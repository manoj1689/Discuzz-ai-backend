"""
Pydantic schemas for Comment API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class CommentCreate(BaseModel):
    """Schema for creating a comment."""
    content: str = Field(..., min_length=1, max_length=2000)
    reply_to_id: Optional[int] = None


class CommentResponse(BaseModel):
    """Schema for comment response."""
    id: int
    author: UserPublic
    content: str
    timestamp: datetime
    is_ai_response: bool = False
    reply_to_id: Optional[int] = None
    
    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Paginated comment list response."""
    items: List[CommentResponse]
    total: int
