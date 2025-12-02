"""
Comment API endpoints.
"""

from typing import List

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUser, CurrentUserOptional
from app.core.exceptions import NotFoundError, AuthorizationError
from app.models.post import Post
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse, CommentListResponse
from app.schemas.user import UserPublic, UserStats


router = APIRouter(prefix="/posts/{post_id}/comments", tags=["Comments"])


def comment_to_response(comment: Comment) -> CommentResponse:
    """Convert Comment model to response schema."""
    return CommentResponse(
        id=comment.id,
        author=UserPublic(
            id=comment.author.id,
            name=comment.author.name,
            handle=comment.author.handle,
            avatar_url=comment.author.avatar_url,
            bio=comment.author.bio,
            stats=UserStats(
                followers=comment.author.followers_count,
                following=comment.author.following_count
            ),
            is_verified=comment.author.is_verified
        ),
        content=comment.content,
        timestamp=comment.created_at,
        is_ai_response=comment.is_ai_response,
        reply_to_id=comment.parent_id
    )


@router.get("", response_model=CommentListResponse)
async def get_post_comments(
    post_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """
    Get comments for a post.
    """
    # Verify post exists
    post_result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted == False)
    )
    if not post_result.scalar_one_or_none():
        raise NotFoundError("Post")
    
    offset = (page - 1) * per_page
    
    query = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.post_id == post_id, Comment.is_deleted == False)
        .order_by(Comment.created_at)
    )
    
    count_query = select(func.count(Comment.id)).where(
        Comment.post_id == post_id, Comment.is_deleted == False
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    result = await db.execute(query.offset(offset).limit(per_page))
    comments = result.scalars().all()
    
    return CommentListResponse(
        items=[comment_to_response(c) for c in comments],
        total=total
    )


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    data: CommentCreate,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Create a new comment on a post.
    """
    # Verify post exists
    post_result = await db.execute(
        select(Post).where(Post.id == post_id, Post.is_deleted == False)
    )
    post = post_result.scalar_one_or_none()
    
    if not post:
        raise NotFoundError("Post")
    
    # Verify parent comment if replying
    if data.reply_to_id:
        parent_result = await db.execute(
            select(Comment).where(
                Comment.id == data.reply_to_id,
                Comment.post_id == post_id,
                Comment.is_deleted == False
            )
        )
        if not parent_result.scalar_one_or_none():
            raise NotFoundError("Parent comment")
    
    comment = Comment(
        content=data.content,
        author_id=current_user.id,
        post_id=post_id,
        parent_id=data.reply_to_id
    )
    
    db.add(comment)
    
    # Update post reply count
    post.reply_count += 1
    
    await db.flush()
    await db.refresh(comment)
    
    # Load author relationship
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment.id)
    )
    comment = result.scalar_one()
    
    # TODO: Create notification
    
    return comment_to_response(comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Delete a comment (soft delete).
    """
    result = await db.execute(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.post_id == post_id,
            Comment.is_deleted == False
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise NotFoundError("Comment")
    
    if comment.author_id != current_user.id and not current_user.is_superuser:
        raise AuthorizationError("Not authorized to delete this comment")
    
    comment.is_deleted = True
    
    # Update post reply count
    post_result = await db.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one()
    if post.reply_count > 0:
        post.reply_count -= 1
