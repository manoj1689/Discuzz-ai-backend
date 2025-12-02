"""
Post and ContextProfile database models.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Many-to-many for post likes
post_likes_table = __import__('sqlalchemy', fromlist=['Table', 'Column']).Table(
    "post_likes",
    Base.metadata,
    __import__('sqlalchemy', fromlist=['Column']).Column(
        "user_id", 
        Integer, 
        __import__('sqlalchemy', fromlist=['ForeignKey']).ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    ),
    __import__('sqlalchemy', fromlist=['Column']).Column(
        "post_id", 
        Integer, 
        __import__('sqlalchemy', fromlist=['ForeignKey']).ForeignKey("posts.id", ondelete="CASCADE"), 
        primary_key=True
    ),
)


class Post(Base):
    """Post/Discussion model with AI-generated context profile."""
    
    __tablename__ = "posts"
    
    # Content
    content: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Author relationship
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author: Mapped["User"] = relationship(back_populates="posts")
    
    # Context Profile (AI-generated)
    context_profile: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="AI-generated context profile with intent, tone, assumptions, audience, coreArgument"
    )
    
    # Stats (denormalized for performance)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="post", 
        cascade="all, delete-orphan"
    )
    liked_by: Mapped[List["User"]] = relationship(
        secondary=post_likes_table,
        backref="liked_posts"
    )
    
    # Interview data (stored for AI delegate)
    interview_history: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=None,
        comment="Interview Q&A used to generate context profile"
    )


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.comment import Comment
