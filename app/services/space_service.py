"""
Space service for CRUD operations.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.space import Space
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceUpdate


class SpaceService:
    """Service for space-related operations."""
    
    async def get_by_id(
        self,
        db: AsyncSession,
        space_id: UUID
    ) -> Optional[Space]:
        """Get space by ID."""
        result = await db.execute(
            select(Space)
            .options(selectinload(Space.creator))
            .where(Space.id == space_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_slug(
        self,
        db: AsyncSession,
        slug: str
    ) -> Optional[Space]:
        """Get space by slug."""
        result = await db.execute(
            select(Space)
            .options(selectinload(Space.creator))
            .where(Space.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        is_featured: Optional[bool] = None
    ) -> List[Space]:
        """Get multiple spaces with pagination."""
        query = (
            select(Space)
            .options(selectinload(Space.creator))
            .order_by(desc(Space.member_count))
            .offset(skip)
            .limit(limit)
        )
        
        if is_featured is not None:
            query = query.where(Space.is_featured == is_featured)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def create(
        self,
        db: AsyncSession,
        space_in: SpaceCreate,
        creator_id: UUID
    ) -> Space:
        """Create a new space."""
        space = Space(
            name=space_in.name,
            slug=space_in.slug,
            description=space_in.description,
            icon=space_in.icon,
            creator_id=creator_id
        )
        db.add(space)
        await db.commit()
        await db.refresh(space)
        return space
    
    async def update(
        self,
        db: AsyncSession,
        space: Space,
        space_in: SpaceUpdate
    ) -> Space:
        """Update a space."""
        update_data = space_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(space, field, value)
        
        await db.commit()
        await db.refresh(space)
        return space
    
    async def delete(self, db: AsyncSession, space: Space) -> None:
        """Delete a space."""
        await db.delete(space)
        await db.commit()
    
    async def join_space(
        self,
        db: AsyncSession,
        space: Space,
        user: User
    ) -> None:
        """Join a space."""
        if user not in space.members:
            space.members.append(user)
            space.member_count += 1
            await db.commit()
    
    async def leave_space(
        self,
        db: AsyncSession,
        space: Space,
        user: User
    ) -> None:
        """Leave a space."""
        if user in space.members:
            space.members.remove(user)
            space.member_count -= 1
            await db.commit()


space_service = SpaceService()
