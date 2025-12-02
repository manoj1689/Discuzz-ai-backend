"""
Space (audio room) database models.
"""

from typing import TYPE_CHECKING, List, Optional
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


class ParticipantRole(str, enum.Enum):
    HOST = "host"
    CO_HOST = "co_host"
    SPEAKER = "speaker"
    LISTENER = "listener"


class Space(Base):
    """Audio Space/Room model."""
    
    __tablename__ = "spaces"
    
    # Basic info
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String(50)), default=list)
    
    # Host
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    host: Mapped["User"] = relationship(foreign_keys=[host_id])
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Settings
    is_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    participants: Mapped[List["SpaceParticipant"]] = relationship(
        back_populates="space",
        cascade="all, delete-orphan"
    )
    messages: Mapped[List["SpaceMessage"]] = relationship(
        back_populates="space",
        cascade="all, delete-orphan"
    )


class SpaceParticipant(Base):
    """Space participant with role."""
    
    __tablename__ = "space_participants"
    
    # Space relationship
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    space: Mapped["Space"] = relationship(back_populates="participants")
    
    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped["User"] = relationship()
    
    # Status
    role: Mapped[ParticipantRole] = mapped_column(Enum(ParticipantRole), default=ParticipantRole.LISTENER)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=True)
    is_speaking: Mapped[bool] = mapped_column(Boolean, default=False)
    hand_raised: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SpaceMessage(Base):
    """Chat message in a space."""
    
    __tablename__ = "space_messages"
    
    # Space relationship
    space_id: Mapped[int] = mapped_column(ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    space: Mapped["Space"] = relationship(back_populates="messages")
    
    # Author
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped["User"] = relationship()
    
    # Content
    content: Mapped[str] = mapped_column(Text)


if TYPE_CHECKING:
    from app.models.user import User
