"""
User database model.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text, Integer, ForeignKey, Table, Column, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, column_property, declared_attr

from app.db.base import Base


# Many-to-many relationship table for followers
followers_table = Table(
    "followers",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("followed_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-many for user interests
user_interests_table = Table(
    "user_interests",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("interest_id", Integer, ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True),
)


class Interest(Base):
    """User interest/topic model."""
    
    __tablename__ = "interests"
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50))
    
    users: Mapped[List["User"]] = relationship(
        secondary=user_interests_table,
        back_populates="interests"
    )


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Profile
    name: Mapped[str] = mapped_column(String(100))
    handle: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    location: Mapped[Optional[str]] = mapped_column(String(100))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Settings
    language: Mapped[str] = mapped_column(String(10), default="en")
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Email verification
    verification_code: Mapped[Optional[str]] = mapped_column(String(6))
    verification_code_expires: Mapped[Optional[datetime]] = mapped_column()
    
    # Relationships
    posts: Mapped[List["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    comments: Mapped[List["Comment"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Notification.user_id"
    )
    
    # Followers/Following
    followers: Mapped[List["User"]] = relationship(
        "User",
        secondary=followers_table,
        primaryjoin=lambda: User.id == followers_table.c.followed_id,
        secondaryjoin=lambda: User.id == followers_table.c.follower_id,
        back_populates="following",
        foreign_keys=[followers_table.c.followed_id, followers_table.c.follower_id],
        lazy="raise"
    )
    following: Mapped[List["User"]] = relationship(
        "User",
        secondary=followers_table,
        primaryjoin=lambda: User.id == followers_table.c.follower_id,
        secondaryjoin=lambda: User.id == followers_table.c.followed_id,
        back_populates="followers",
        foreign_keys=[followers_table.c.followed_id, followers_table.c.follower_id],
        lazy="raise"
    )
    
    @declared_attr
    def followers_count(cls) -> Mapped[int]:
        return column_property(
            select(func.count(followers_table.c.follower_id))
            .where(followers_table.c.followed_id == cls.id)
            .correlate_except(followers_table)
            .scalar_subquery()
        )
    
    @declared_attr
    def following_count(cls) -> Mapped[int]:
        return column_property(
            select(func.count(followers_table.c.followed_id))
            .where(followers_table.c.follower_id == cls.id)
            .correlate_except(followers_table)
            .scalar_subquery()
        )
    
    # Interests
    interests: Mapped[List["Interest"]] = relationship(
        secondary=user_interests_table,
        back_populates="users",
        lazy="raise"
    )


# Import at end to avoid circular imports
if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.comment import Comment
    from app.models.notification import Notification
