"""
Comment database model.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Comment(Base):
    """Comment/Reply model."""
    
    __tablename__ = "comments"
    
    # Content
    content: Mapped[str] = mapped_column(Text)
    
    # Author relationship
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    author: Mapped["User"] = relationship(back_populates="comments")
    
    # Post relationship
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    post: Mapped["Post"] = relationship(back_populates="comments")
    
    # Reply to another comment (threading)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
        index=True
    )
    replies: Mapped[List["Comment"]] = relationship(
        "Comment",
        backref="parent",
        remote_side="Comment.id"
    )
    
    # AI delegate response flag
    is_ai_response: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.post import Post
