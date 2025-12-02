"""
Search API endpoints.
"""

from typing import List

from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUserOptional
from app.models.user import User
from app.models.post import Post
from app.schemas.user import UserPublic, UserStats
from app.schemas.post import PostResponse, ContextProfile


router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/users", response_model=List[UserPublic])
async def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    db: DbSession = None,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Search for users by name or handle.
    """
    search_term = f"%{q.lower()}%"
    
    query = (
        select(User)
        .where(
            or_(
                User.name.ilike(search_term),
                User.handle.ilike(search_term)
            ),
            User.is_active == True
        )
        .limit(limit)
    )
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        UserPublic(
            id=u.id,
            name=u.name,
            handle=u.handle,
            avatar_url=u.avatar_url,
            bio=u.bio,
            stats=UserStats(
                followers=u.followers_count,
                following=u.following_count
            ),
            is_verified=u.is_verified
        )
        for u in users
    ]


@router.get("/posts", response_model=List[PostResponse])
async def search_posts(
    q: str = Query(..., min_length=1, max_length=100),
    db: DbSession = None,
    current_user: CurrentUserOptional = None,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Search for posts by content.
    """
    search_term = f"%{q.lower()}%"
    
    query = (
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.liked_by))
        .where(
            Post.content.ilike(search_term),
            Post.is_deleted == False,
            Post.is_published == True
        )
        .limit(limit)
    )
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    current_user_id = current_user.id if current_user else None
    
    responses = []
    for post in posts:
        is_liked = any(u.id == current_user_id for u in post.liked_by) if current_user_id else False
        
        context_profile = ContextProfile(
            intent=post.context_profile.get("intent", ""),
            tone=post.context_profile.get("tone", ""),
            assumptions=post.context_profile.get("assumptions", ""),
            audience=post.context_profile.get("audience", ""),
            coreArgument=post.context_profile.get("coreArgument", post.context_profile.get("core_argument", ""))
        )
        
        responses.append(PostResponse(
            id=post.id,
            content=post.content,
            image_url=post.image_url,
            author_name=post.author.name,
            author_handle=post.author.handle,
            avatar_url=post.author.avatar_url,
            context_profile=context_profile,
            likes=post.likes_count,
            reply_count=post.reply_count,
            is_liked=is_liked,
            timestamp=post.created_at
        ))
    
    return responses
