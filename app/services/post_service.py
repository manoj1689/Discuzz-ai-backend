"""
Post service for CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate, ContextProfile


class PostService:
    """Service for post-related operations."""
    
    async def get_by_id(
        self,
        db: AsyncSession,
        post_id: UUID
    ) -> Optional[Post]:
        """Get post by ID with author."""
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.id == post_id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        space_id: Optional[UUID] = None
    ) -> List[Post]:
        """Get multiple posts with pagination."""
        query = (
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.is_published == True)
            .order_by(desc(Post.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        if space_id:
            query = query.where(Post.space_id == space_id)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_author(
        self,
        db: AsyncSession,
        author_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[Post]:
        """Get posts by author."""
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.author_id == author_id)
            .order_by(desc(Post.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        db: AsyncSession,
        post_in: PostCreate,
        author_id: UUID
    ) -> Post:
        """Create a new post."""
        # Convert context profile to dict if provided
        context_profile_dict = None
        if post_in.context_profile:
            context_profile_dict = post_in.context_profile.model_dump()
        
        post = Post(
            content=post_in.content,
            author_id=author_id,
            space_id=post_in.space_id,
            context_profile=context_profile_dict,
            delegate_enabled=post_in.delegate_enabled,
            is_published=post_in.is_published
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)
        
        # Load author relationship
        await db.refresh(post, ["author"])
        return post
    
    async def update(
        self,
        db: AsyncSession,
        post: Post,
        post_in: PostUpdate
    ) -> Post:
        """Update a post."""
        update_data = post_in.model_dump(exclude_unset=True)
        
        if "context_profile" in update_data and update_data["context_profile"]:
            update_data["context_profile"] = update_data["context_profile"].model_dump()
        
        for field, value in update_data.items():
            setattr(post, field, value)
        
        await db.commit()
        await db.refresh(post)
        return post
    
    async def delete(self, db: AsyncSession, post: Post) -> None:
        """Delete a post."""
        await db.delete(post)
        await db.commit()
    
    async def like_post(
        self,
        db: AsyncSession,
        post: Post,
        user: User
    ) -> None:
        """Like a post."""
        if user not in post.liked_by:
            post.liked_by.append(user)
            post.likes_count += 1
            await db.commit()
    
    async def unlike_post(
        self,
        db: AsyncSession,
        post: Post,
        user: User
    ) -> None:
        """Unlike a post."""
        if user in post.liked_by:
            post.liked_by.remove(user)
            post.likes_count -= 1
            await db.commit()
    
    async def repost(
        self,
        db: AsyncSession,
        post: Post,
        user: User
    ) -> None:
        """Repost a post."""
        if user not in post.reposted_by:
            post.reposted_by.append(user)
            post.reposts_count += 1
            await db.commit()
    
    async def increment_views(
        self,
        db: AsyncSession,
        post: Post
    ) -> None:
        """Increment post views."""
        post.views_count += 1
        await db.commit()
    
    async def search(
        self,
        db: AsyncSession,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Post]:
        """Search posts by content."""
        result = await db.execute(
            select(Post)
            .options(selectinload(Post.author))
            .where(
                Post.is_published == True,
                Post.content.ilike(f"%{query}%")
            )
            .order_by(desc(Post.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


post_service = PostService()
