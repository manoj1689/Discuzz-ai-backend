"""
Pydantic schemas for Space API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic
from app.models.space import ParticipantRole


class SpaceParticipantResponse(BaseModel):
    """Space participant response."""
    user: UserPublic
    role: ParticipantRole
    is_muted: bool = True
    is_speaking: bool = False
    hand_raised: bool = False
    
    model_config = {"from_attributes": True}


class SpaceCreate(BaseModel):
    """Schema for creating a space."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_length=5)


class SpaceResponse(BaseModel):
    """Schema for space response."""
    id: int
    title: str
    description: Optional[str] = None
    tags: List[str] = []
    host: UserPublic
    participants: List[SpaceParticipantResponse] = []
    is_active: bool = True
    started_at: Optional[datetime] = None
    listener_count: int = 0
    
    model_config = {"from_attributes": True}


class SpaceMessageCreate(BaseModel):
    """Schema for creating a space message."""
    content: str = Field(..., min_length=1, max_length=500)


class SpaceMessageResponse(BaseModel):
    """Schema for space message response."""
    id: int
    user: UserPublic
    content: str
    timestamp: datetime
    
    model_config = {"from_attributes": True}
