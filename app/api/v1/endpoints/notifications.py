"""
Notification API endpoints.
"""

from typing import List

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUser
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.schemas.user import UserPublic, UserStats


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False)
):
    """
    Get current user's notifications.
    """
    offset = (page - 1) * per_page
    
    query = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    # Get counts
    count_query = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id
    )
    unread_query = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar()
    
    result = await db.execute(query.offset(offset).limit(per_page))
    notifications = result.scalars().all()
    
    items = []
    for n in notifications:
        if n.actor:
            items.append(NotificationResponse(
                id=n.id,
                type=n.type,
                user=UserPublic(
                    id=n.actor.id,
                    name=n.actor.name,
                    handle=n.actor.handle,
                    avatar_url=n.actor.avatar_url,
                    bio=n.actor.bio,
                    stats=UserStats(
                        followers=n.actor.followers_count,
                        following=n.actor.following_count
                    ),
                    is_verified=n.actor.is_verified
                ),
                post_preview=n.preview_text,
                timestamp=n.created_at,
                read=n.is_read
            ))
    
    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count
    )


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_as_read(
    db: DbSession,
    current_user: CurrentUser
):
    """
    Mark all notifications as read.
    """
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )
    
    return {"message": "All notifications marked as read"}


@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_as_read(
    notification_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Mark a specific notification as read.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()
    
    if notification:
        notification.is_read = True
    
    return {"message": "Notification marked as read"}
