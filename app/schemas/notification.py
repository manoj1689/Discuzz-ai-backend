"""
Pydantic schemas for Notification API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.schemas.user import UserPublic
from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: int
    type: NotificationType
    user: UserPublic
    post_preview: Optional[str] = None
    timestamp: datetime
    read: bool = False
    
    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
