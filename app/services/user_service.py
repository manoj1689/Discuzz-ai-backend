"""
User service for CRUD operations.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    """Service for user-related operations."""
    
    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def create(self, db: AsyncSession, user_in: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=user_in.email,
            username=user_in.username,
            display_name=user_in.display_name or user_in.username,
            password_hash=get_password_hash(user_in.password),
            bio=user_in.bio
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def update(
        self,
        db: AsyncSession,
        user: User,
        user_in: UserUpdate
    ) -> User:
        """Update user."""
        update_data = user_in.model_dump(exclude_unset=True)
        
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        return user
    
    async def authenticate(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user by email and password."""
        user = await self.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    
    async def follow_user(
        self,
        db: AsyncSession,
        follower: User,
        following: User
    ) -> None:
        """Follow a user."""
        await db.refresh(follower, attribute_names=["following"])
        if following not in follower.following:
            follower.following.append(following)
            await db.commit()
    
    async def unfollow_user(
        self,
        db: AsyncSession,
        follower: User,
        following: User
    ) -> None:
        """Unfollow a user."""
        await db.refresh(follower, attribute_names=["following"])
        if following in follower.following:
            follower.following.remove(following)
            await db.commit()


user_service = UserService()
