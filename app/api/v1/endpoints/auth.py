"""
Authentication API endpoints.
"""

import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
from app.schemas.user import UserResponse, UserStats
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    GoogleLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    VerificationRequest,
    ResendVerificationRequest
)
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests


router = APIRouter(prefix="/auth", tags=["Authentication"])


HANDLE_PREFIX = "@"
HANDLE_MAX_LENGTH = 50  # matches User.handle column size
_google_request = google_requests.Request()


def _clean_handle_seed(seed: str) -> str:
    """
    Normalize a handle seed by lowercasing, stripping invalid chars,
    and enforcing minimum/maximum length (without the @ prefix).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", seed or "").strip("_").lower()
    if not cleaned:
        cleaned = "user"
    if len(cleaned) < 3:
        cleaned = cleaned.ljust(3, "0")
    return cleaned[: HANDLE_MAX_LENGTH - len(HANDLE_PREFIX)]


def _load_project_id_from_credentials() -> Optional[str]:
    """Extract project_id from GOOGLE_APPLICATION_CREDENTIALS_JSON if provided."""
    if not settings.google_application_credentials_json:
        return None
    try:
        cred = json.loads(settings.google_application_credentials_json)
        return cred.get("project_id")
    except json.JSONDecodeError:
        raise ValidationError("Invalid GOOGLE_APPLICATION_CREDENTIALS_JSON")


def _verify_google_token(id_token: str) -> dict[str, Any]:
    """
    Verify an incoming Google/Firebase ID token.
    Prefer Firebase verification when service account JSON is available,
    fall back to Google OAuth client ID validation.
    """
    firebase_project_id = settings.firebase_project_id or _load_project_id_from_credentials()
    last_error: Exception | None = None

    if firebase_project_id:
        try:
            return google_id_token.verify_firebase_token(
                id_token,
                _google_request,
                audience=firebase_project_id
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if settings.google_client_id:
        try:
            return google_id_token.verify_oauth2_token(
                id_token,
                _google_request,
                settings.google_client_id
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if last_error:
        raise AuthenticationError("Invalid Google token")
    raise ValidationError("Google Sign-In is not configured")


async def _generate_handle(
    db: AsyncSession,
    seed: str,
    allow_suffix: bool = True
) -> str:
    """
    Build a unique handle. If allow_suffix is False, raise ConflictError
    when the normalized handle is already taken.
    """
    base = _clean_handle_seed(seed)
    suffix = 0
    while True:
        suffix_str = str(suffix) if suffix else ""
        max_base_len = (HANDLE_MAX_LENGTH - len(HANDLE_PREFIX)) - len(suffix_str)
        candidate_body = f"{base[:max_base_len]}{suffix_str}"
        candidate = f"{HANDLE_PREFIX}{candidate_body}"

        result = await db.execute(select(User).where(User.handle == candidate))
        if not result.scalar_one_or_none():
            return candidate

        if not allow_suffix:
            raise ConflictError("Handle already taken")

        suffix += 1


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: DbSession
):
    """
    Register a new user account.
    """
    # Validate password strength
    is_valid, error_msg = validate_password_strength(data.password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    email = data.email.lower()

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ConflictError("Email already registered")

    # Prepare name and handle
    fallback_seed = email.split("@")[0]
    name = data.name or fallback_seed
    handle_seed = data.handle or data.name or fallback_seed
    handle = await _generate_handle(
        db=db,
        seed=handle_seed,
        allow_suffix=not bool(data.handle)
    )
    
    # Generate verification code
    verification_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    
    # Create user
    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        name=name,
        handle=handle,
        verification_code=verification_code,
        verification_code_expires=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    # TODO: Send verification email

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: DbSession
):
    """
    Login with email and password.
    """
    email = data.email.lower()
    result = await db.execute(select(User).where(User.email == email))
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


@router.post("/google", response_model=TokenResponse)
async def login_with_google(
    data: GoogleLoginRequest,
    db: DbSession
):
    """
    Sign in/up using a Google ID token.
    """
    google_payload = _verify_google_token(data.id_token)

    email = google_payload.get("email")
    if not email:
        raise AuthenticationError("Google account is missing email")

    email = email.lower()
    name = google_payload.get("name") or email.split("@")[0]
    picture = google_payload.get("picture")

    # Lookup user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        handle_seed = google_payload.get("given_name") or name or email.split("@")[0]
        handle = await _generate_handle(db, handle_seed, allow_suffix=True)

        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(16)),
            name=name,
            handle=handle,
            avatar_url=picture,
            is_verified=True,
            verification_code=None,
            verification_code_expires=None
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    else:
        updated = False
        if not user.is_verified:
            user.is_verified = True
            updated = True
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            updated = True
        if updated:
            await db.flush()

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
    current_user: CurrentUser,
    db: DbSession
):
    """
    Get current authenticated user info.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.interests))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none() or current_user

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        handle=user.handle,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=user.location,
        website=user.website,
        language=user.language,
        interests=[interest.name for interest in user.interests],
        stats=UserStats(
            followers=user.followers_count,
            following=user.following_count
        ),
        is_verified=user.is_verified,
        created_at=user.created_at
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
