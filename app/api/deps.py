"""
API dependencies for dependency injection.
"""

from typing import Annotated, Optional

from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.session import get_db
from app.models.user import User


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises AuthenticationError if not authenticated.
    """
    if not credentials:
        raise AuthenticationError("Missing authentication token")
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise AuthenticationError("Invalid or expired token")
    
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.interests))
        .where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AuthenticationError("User not found")
    
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    
    return user


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
) -> Optional[User]:
    """
    Dependency to optionally get the current user.
    Returns None if not authenticated.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(db, credentials)
    except AuthenticationError:
        return None


async def get_current_verified_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get a verified user.
    """
    if not current_user.is_verified:
        raise AuthorizationError("Email verification required")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get a superuser.
    """
    if not current_user.is_superuser:
        raise AuthorizationError("Superuser access required")
    return current_user


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
CurrentVerifiedUser = Annotated[User, Depends(get_current_verified_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
