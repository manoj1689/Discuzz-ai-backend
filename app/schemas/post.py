"""
Pydantic schemas for Post API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class ContextProfile(BaseModel):
    """AI-generated context profile."""
    intent: str
    tone: str
    assumptions: str
    audience: str
    core_argument: str = Field(alias="coreArgument")
    
    model_config = {"populate_by_name": True}


class InterviewMessage(BaseModel):
    """Interview message for context generation."""
    id: str
    role: str  # 'user' or 'model'
    content: str
    timestamp: int


class PostCreate(BaseModel):
    """Schema for creating a post."""
    content: str = Field(..., min_length=1, max_length=5000)
    image_url: Optional[str] = None


class PostWithInterview(BaseModel):
    """Schema for creating a post with interview data."""
    content: str = Field(..., min_length=1, max_length=5000)
    image_url: Optional[str] = None
    interview_history: List[InterviewMessage]
    context_profile: ContextProfile


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    content: str
    image_url: Optional[str] = None
    author_name: str
    author_handle: str
    avatar_url: Optional[str] = None
    context_profile: ContextProfile
    likes: int
    reply_count: int
    is_liked: bool = False
    timestamp: datetime
    
    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    """Paginated post list response."""
    items: List[PostResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
