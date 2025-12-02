"""
Authentication API endpoints.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, CurrentUser
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ValidationError,
    NotFoundError
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserStats
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    VerificationRequest,
    ResendVerificationRequest
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: DbSession
):
    """
    Register a new user account.
    """
    # Validate password strength
    is_valid, error_msg = validate_password_strength(data.password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")
    
    # Check if handle already exists
    result = await db.execute(select(User).where(User.handle == data.handle))
    if result.scalar_one_or_none():
        raise ConflictError("Handle already taken")
    
    # Generate verification code
    verification_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Create user
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
        handle=data.handle,
        verification_code=verification_code,
        verification_code_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # TODO: Send verification email
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        handle=user.handle,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=user.location,
        website=user.website,
        stats=UserStats(followers=0, following=0),
        is_verified=user.is_verified,
        created_at=user.created_at
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: DbSession
):
    """
    Login with email and password.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: DbSession
):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("Invalid refresh token")
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise AuthenticationError("User not found or disabled")
    
    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_email(
    data: VerificationRequest,
    db: DbSession
):
    """
    Verify email with verification code.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User")
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    if user.verification_code != data.code:
        raise ValidationError("Invalid verification code")
    
    if user.verification_code_expires and user.verification_code_expires < datetime.now(timezone.utc):
        raise ValidationError("Verification code expired")
    
    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    data: ResendVerificationRequest,
    db: DbSession
):
    """
    Resend verification code.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if user exists
        return {"message": "If the email exists, a verification code has been sent"}
    
    if user.is_verified:
        return {"message": "Email already verified"}
    
    # Generate new verification code
    user.verification_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    user.verification_code_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # TODO: Send verification email
    
    return {"message": "If the email exists, a verification code has been sent"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser
):
    """
    Get current authenticated user info.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        handle=current_user.handle,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        location=current_user.location,
        website=current_user.website,
        stats=UserStats(
            followers=current_user.followers_count,
            following=current_user.following_count
        ),
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: CurrentUser
):
    """
    Logout (client should discard tokens).
    For enhanced security, implement token blacklisting with Redis.
    """
    # TODO: Add token to blacklist in Redis
    return {"message": "Logged out successfully"}
