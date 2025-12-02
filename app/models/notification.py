"""
Notification database model.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


class NotificationType(str, enum.Enum):
    LIKE = "like"
    REPLY = "reply"
    FOLLOW = "follow"
    MENTION = "mention"
    SPACE_INVITE = "space_invite"
    AI_CONTEXT = "ai_context"


class Notification(Base):
    """Notification model."""
    
    __tablename__ = "notifications"
    
    # Recipient
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped["User"] = relationship(
        back_populates="notifications",
        foreign_keys="Notification.user_id"
    )
    
    # Type
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        index=True
    )
    
    # Actor (user who triggered the notification)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor: Mapped[Optional["User"]] = relationship(foreign_keys=[actor_id])
    
    # Related content
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    space_id: Mapped[Optional[int]] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"))
    
    # Preview text
    preview_text: Mapped[Optional[str]] = mapped_column(String(280))
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


if TYPE_CHECKING:
    from app.models.user import User
