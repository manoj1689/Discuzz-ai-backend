"""
Notification service for CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


class NotificationService:
    """Service for notification-related operations."""
    
    async def get_by_id(
        self,
        db: AsyncSession,
        notification_id: UUID
    ) -> Optional[Notification]:
        """Get notification by ID."""
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """Get unread notification count."""
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        return result.scalar() or 0
    
    async def create(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        actor_id: Optional[UUID] = None,
        post_id: Optional[UUID] = None,
        comment_id: Optional[UUID] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            actor_id=actor_id,
            post_id=post_id,
            comment_id=comment_id
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification
    
    async def mark_as_read(
        self,
        db: AsyncSession,
        notification: Notification
    ) -> Notification:
        """Mark notification as read."""
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)
        return notification
    
    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> None:
        """Mark all notifications as read for a user."""
        await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
            .values(is_read=True)
        )
        await db.commit()
    
    async def delete(
        self,
        db: AsyncSession,
        notification: Notification
    ) -> None:
        """Delete a notification."""
        await db.delete(notification)
        await db.commit()


notification_service = NotificationService()
