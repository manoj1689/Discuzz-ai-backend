"""
User API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUser, CurrentUserOptional
from app.core.exceptions import NotFoundError, ConflictError
from app.models.user import User, Interest, followers_table
from app.schemas.user import UserResponse, UserPublic, UserUpdate, UserStats, UserInterests


router = APIRouter(prefix="/users", tags=["Users"])


def _user_to_response(user: User) -> UserResponse:
    """Serialize a user model with interests and stats."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        handle=user.handle,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=user.location,
        website=user.website,
        language=user.language,
        interests=[interest.name for interest in user.interests],
        stats=UserStats(
            followers=user.followers_count,
            following=user.following_count
        ),
        is_verified=user.is_verified,
        created_at=user.created_at
    )


@router.get("/{handle}", response_model=UserPublic)
async def get_user_by_handle(
    handle: str,
    db: DbSession,
    current_user: CurrentUserOptional
):
    """
    Get a user's public profile by handle.
    """
    # Normalize handle
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.followers), selectinload(User.following))
        .where(User.handle == handle.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User")
    
    return UserPublic(
        id=user.id,
        name=user.name,
        handle=user.handle,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=user.location,
        website=user.website,
        stats=UserStats(
            followers=user.followers_count,
            following=user.following_count
        ),
        is_verified=user.is_verified
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Update current user's profile.
    """
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    await db.flush()
    result = await db.execute(
        select(User)
        .options(selectinload(User.interests))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none() or current_user
    
    return _user_to_response(user)


@router.post("/{handle}/follow", status_code=status.HTTP_200_OK)
async def follow_user(
    handle: str,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Follow a user.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.followers))
        .where(User.handle == handle.lower())
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise NotFoundError("User")
    
    if target_user.id == current_user.id:
        raise ConflictError("Cannot follow yourself")
    
    # Check if already following
    if current_user in target_user.followers:
        raise ConflictError("Already following this user")
    
    target_user.followers.append(current_user)
    
    # TODO: Create notification
    
    return {"message": f"Now following {handle}"}


@router.delete("/{handle}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    handle: str,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Unfollow a user.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.followers))
        .where(User.handle == handle.lower())
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise NotFoundError("User")
    
    if current_user not in target_user.followers:
        raise ConflictError("Not following this user")
    
    target_user.followers.remove(current_user)
    
    return {"message": f"Unfollowed {handle}"}


@router.get("/{handle}/followers", response_model=List[UserPublic])
async def get_user_followers(
    handle: str,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Get a user's followers.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.followers))
        .where(User.handle == handle.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User")
    
    # Paginate followers
    offset = (page - 1) * per_page
    followers = user.followers[offset:offset + per_page]
    
    return [
        UserPublic(
            id=f.id,
            name=f.name,
            handle=f.handle,
            avatar_url=f.avatar_url,
            bio=f.bio,
            stats=UserStats(followers=f.followers_count, following=f.following_count),
            is_verified=f.is_verified
        )
        for f in followers
    ]


@router.get("/{handle}/following", response_model=List[UserPublic])
async def get_user_following(
    handle: str,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """
    Get users that a user is following.
    """
    if not handle.startswith("@"):
        handle = f"@{handle}"
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.following))
        .where(User.handle == handle.lower())
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise NotFoundError("User")
    
    offset = (page - 1) * per_page
    following = user.following[offset:offset + per_page]
    
    return [
        UserPublic(
            id=f.id,
            name=f.name,
            handle=f.handle,
            avatar_url=f.avatar_url,
            bio=f.bio,
            stats=UserStats(followers=f.followers_count, following=f.following_count),
            is_verified=f.is_verified
        )
        for f in following
    ]


@router.put("/me/interests", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user_interests(
    data: UserInterests,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Update current user's interests and languages.
    """
    await db.refresh(current_user, attribute_names=["interests"])
    # Clear existing interests
    current_user.interests = []
    
    # Add new interests
    for topic in data.topics:
        result = await db.execute(select(Interest).where(Interest.name == topic))
        interest = result.scalar_one_or_none()
        
        if not interest:
            interest = Interest(name=topic, category="topic")
            db.add(interest)
        
        current_user.interests.append(interest)
    
    # Store languages (simplified - could be separate table)
    if data.languages:
        current_user.language = data.languages[0]  # Primary language
    
    await db.flush()
    result = await db.execute(
        select(User)
        .options(selectinload(User.interests))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none() or current_user
    
    return _user_to_response(user)
