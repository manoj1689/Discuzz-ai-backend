"""
Comment service for CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    """Service for comment-related operations."""
    
    async def get_by_id(
        self,
        db: AsyncSession,
        comment_id: UUID
    ) -> Optional[Comment]:
        """Get comment by ID."""
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.id == comment_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_post(
        self,
        db: AsyncSession,
        post_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Comment]:
        """Get comments for a post."""
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(
                Comment.post_id == post_id,
                Comment.parent_id == None  # Only top-level comments
            )
            .order_by(desc(Comment.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_replies(
        self,
        db: AsyncSession,
        parent_id: UUID
    ) -> List[Comment]:
        """Get replies to a comment."""
        result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.parent_id == parent_id)
            .order_by(Comment.created_at)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        db: AsyncSession,
        comment_in: CommentCreate,
        author_id: UUID
    ) -> Comment:
        """Create a new comment."""
        comment = Comment(
            content=comment_in.content,
            post_id=comment_in.post_id,
            author_id=author_id,
            parent_id=comment_in.parent_id,
            is_delegate_response=comment_in.is_delegate_response
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        await db.refresh(comment, ["author"])
        return comment
    
    async def update(
        self,
        db: AsyncSession,
        comment: Comment,
        comment_in: CommentUpdate
    ) -> Comment:
        """Update a comment."""
        update_data = comment_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(comment, field, value)
        
        await db.commit()
        await db.refresh(comment)
        return comment
    
    async def delete(self, db: AsyncSession, comment: Comment) -> None:
        """Delete a comment."""
        await db.delete(comment)
        await db.commit()
    
    async def like_comment(
        self,
        db: AsyncSession,
        comment: Comment,
        user: User
    ) -> None:
        """Like a comment."""
        if user not in comment.liked_by:
            comment.liked_by.append(user)
            comment.likes_count += 1
            await db.commit()
    
    async def unlike_comment(
        self,
        db: AsyncSession,
        comment: Comment,
        user: User
    ) -> None:
        """Unlike a comment."""
        if user in comment.liked_by:
            comment.liked_by.remove(user)
            comment.likes_count -= 1
            await db.commit()


comment_service = CommentService()
