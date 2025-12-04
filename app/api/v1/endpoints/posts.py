"""
Post API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUser, CurrentUserOptional
from app.core.exceptions import NotFoundError, AuthorizationError
from app.models.post import Post
from app.models.user import User, followers_table
from app.schemas.post import (
    PostCreate,
    PostWithInterview,
    PostUpdate,
    PostResponse,
    PostListResponse,
    ContextProfile
)


router = APIRouter(prefix="/posts", tags=["Posts"])


def post_to_response(post: Post, current_user_id: Optional[int] = None) -> PostResponse:
    """Convert Post model to response schema."""
    is_liked = False
    if current_user_id:
        is_liked = any(u.id == current_user_id for u in post.liked_by)
    
    context_profile = ContextProfile(
        intent=post.context_profile.get("intent", ""),
        tone=post.context_profile.get("tone", ""),
        assumptions=post.context_profile.get("assumptions", ""),
        audience=post.context_profile.get("audience", ""),
        coreArgument=post.context_profile.get("coreArgument", post.context_profile.get("core_argument", ""))
    )
    
    return PostResponse(
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
    )


@router.get("", response_model=PostListResponse)
async def get_posts(
    db: DbSession,
    current_user: CurrentUserOptional,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    feed: str = Query("foryou", pattern="^(foryou|following)$")
):
    """
    Get posts feed.
    - foryou: All posts (algorithmic in future)
    - following: Posts from users the current user follows
    """
    offset = (page - 1) * per_page
    
    filters = [Post.is_deleted == False, Post.is_published == True]
    
    query = (
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.liked_by))
        .where(*filters)
        .order_by(desc(Post.created_at))
    )
    
    if feed == "following" and current_user:
        following_ids_result = await db.scalars(
            select(followers_table.c.followed_id).where(
                followers_table.c.follower_id == current_user.id
            )
        )
        following_ids = following_ids_result.all()
        if not following_ids:
            return PostListResponse(
                items=[],
                total=0,
                page=page,
                per_page=per_page,
                has_next=False
            )
        filters.append(Post.author_id.in_(following_ids))
        query = query.where(Post.author_id.in_(following_ids))
    
    # Get total count
    count_query = select(func.count(Post.id)).where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    result = await db.execute(query.offset(offset).limit(per_page))
    posts = result.scalars().all()
    
    current_user_id = current_user.id if current_user else None
    
    return PostListResponse(
        items=[post_to_response(p, current_user_id) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + len(posts) < total
    )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: DbSession,
    current_user: CurrentUserOptional
):
    """
    Get a single post by ID.
    """
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.liked_by))
        .where(Post.id == post_id, Post.is_deleted == False)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise NotFoundError("Post")
    
    current_user_id = current_user.id if current_user else None
    return post_to_response(post, current_user_id)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    data: PostWithInterview,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Create a new post with context profile.
    """
    post = Post(
        content=data.content,
        image_url=data.image_url,
        author_id=current_user.id,
        context_profile={
            "intent": data.context_profile.intent,
            "tone": data.context_profile.tone,
            "assumptions": data.context_profile.assumptions,
            "audience": data.context_profile.audience,
            "coreArgument": data.context_profile.core_argument
        },
        interview_history=[m.model_dump() for m in data.interview_history]
    )
    
    db.add(post)
    await db.flush()
    await db.refresh(post)
    
    # Load relationships
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.liked_by))
        .where(Post.id == post.id)
    )
    post = result.scalar_one()
    
    return post_to_response(post, current_user.id)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Delete a post (soft delete).
    """
    result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted == False)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise NotFoundError("Post")
    
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise AuthorizationError("Not authorized to delete this post")
    
    post.is_deleted = True


@router.post("/{post_id}/like", status_code=status.HTTP_200_OK)
async def like_post(
    post_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Like a post.
    """
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.liked_by))
        .where(Post.id == post_id, Post.is_deleted == False)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise NotFoundError("Post")
    
    if current_user in post.liked_by:
        return {"message": "Already liked", "likes": post.likes_count}
    
    post.liked_by.append(current_user)
    post.likes_count += 1
    
    # TODO: Create notification
    
    return {"message": "Post liked", "likes": post.likes_count}


@router.delete("/{post_id}/like", status_code=status.HTTP_200_OK)
async def unlike_post(
    post_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Unlike a post.
    """
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.liked_by))
        .where(Post.id == post_id, Post.is_deleted == False)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise NotFoundError("Post")
    
    if current_user not in post.liked_by:
        return {"message": "Not liked", "likes": post.likes_count}
    
    post.liked_by.remove(current_user)
    post.likes_count -= 1
    
    return {"message": "Post unliked", "likes": post.likes_count}


@router.get("/user/{handle}", response_model=PostListResponse)
async def get_user_posts(
    handle: str,
    db: DbSession,
    current_user: CurrentUserOptional,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Get posts by a specific user.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    # Get user
    user_result = await db.execute(select(User).where(User.handle == handle.lower()))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User")
    
    offset = (page - 1) * per_page
    
    query = (
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.liked_by))
        .where(Post.author_id == user.id, Post.is_deleted == False)
        .order_by(desc(Post.created_at))
    )
    
    count_query = select(func.count(Post.id)).where(
        Post.author_id == user.id, Post.is_deleted == False
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    result = await db.execute(query.offset(offset).limit(per_page))
    posts = result.scalars().all()
    
    current_user_id = current_user.id if current_user else None
    
    return PostListResponse(
        items=[post_to_response(p, current_user_id) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
        has_next=offset + len(posts) < total
    )
