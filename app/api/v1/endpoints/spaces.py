"""
Space API endpoints.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, CurrentUser, CurrentUserOptional
from app.core.exceptions import NotFoundError, AuthorizationError, ConflictError
from app.models.space import Space, SpaceParticipant, SpaceMessage, ParticipantRole
from app.schemas.space import (
    SpaceCreate,
    SpaceResponse,
    SpaceParticipantResponse,
    SpaceMessageCreate,
    SpaceMessageResponse
)
from app.schemas.user import UserPublic, UserStats


router = APIRouter(prefix="/spaces", tags=["Spaces"])


def participant_to_response(p: SpaceParticipant) -> SpaceParticipantResponse:
    """Convert participant to response."""
    return SpaceParticipantResponse(
        user=UserPublic(
            id=p.user.id,
            name=p.user.name,
            handle=p.user.handle,
            avatar_url=p.user.avatar_url,
            bio=p.user.bio,
            stats=UserStats(
                followers=p.user.followers_count,
                following=p.user.following_count
            ),
            is_verified=p.user.is_verified
        ),
        role=p.role,
        is_muted=p.is_muted,
        is_speaking=p.is_speaking,
        hand_raised=p.hand_raised
    )


def space_to_response(space: Space) -> SpaceResponse:
    """Convert space to response."""
    listener_count = sum(1 for p in space.participants if p.role == ParticipantRole.LISTENER)
    
    return SpaceResponse(
        id=space.id,
        title=space.title,
        description=space.description,
        tags=space.tags,
        host=UserPublic(
            id=space.host.id,
            name=space.host.name,
            handle=space.host.handle,
            avatar_url=space.host.avatar_url,
            bio=space.host.bio,
            stats=UserStats(
                followers=space.host.followers_count,
                following=space.host.following_count
            ),
            is_verified=space.host.is_verified
        ),
        participants=[participant_to_response(p) for p in space.participants],
        is_active=space.is_active,
        started_at=space.started_at,
        listener_count=listener_count
    )


@router.get("", response_model=List[SpaceResponse])
async def get_active_spaces(
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50)
):
    """
    Get active spaces.
    """
    offset = (page - 1) * per_page
    
    query = (
        select(Space)
        .options(
            selectinload(Space.host),
            selectinload(Space.participants).selectinload(SpaceParticipant.user)
        )
        .where(Space.is_active == True)
        .order_by(Space.started_at.desc())
    )
    
    result = await db.execute(query.offset(offset).limit(per_page))
    spaces = result.scalars().all()
    
    return [space_to_response(s) for s in spaces]


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(
    data: SpaceCreate,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Create a new space.
    """
    space = Space(
        title=data.title,
        description=data.description,
        tags=data.tags[:5],  # Limit to 5 tags
        host_id=current_user.id,
        started_at=datetime.now(timezone.utc)
    )
    
    db.add(space)
    await db.flush()
    
    # Add host as participant
    host_participant = SpaceParticipant(
        space_id=space.id,
        user_id=current_user.id,
        role=ParticipantRole.HOST,
        is_muted=False,
        is_speaking=True
    )
    db.add(host_participant)
    
    await db.flush()
    await db.refresh(space)
    
    # Load relationships
    result = await db.execute(
        select(Space)
        .options(
            selectinload(Space.host),
            selectinload(Space.participants).selectinload(SpaceParticipant.user)
        )
        .where(Space.id == space.id)
    )
    space = result.scalar_one()
    
    return space_to_response(space)


@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(
    space_id: int,
    db: DbSession
):
    """
    Get a specific space.
    """
    result = await db.execute(
        select(Space)
        .options(
            selectinload(Space.host),
            selectinload(Space.participants).selectinload(SpaceParticipant.user)
        )
        .where(Space.id == space_id)
    )
    space = result.scalar_one_or_none()
    
    if not space:
        raise NotFoundError("Space")
    
    return space_to_response(space)


@router.post("/{space_id}/join", response_model=SpaceParticipantResponse)
async def join_space(
    space_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Join a space as a listener.
    """
    result = await db.execute(
        select(Space)
        .options(selectinload(Space.participants))
        .where(Space.id == space_id, Space.is_active == True)
    )
    space = result.scalar_one_or_none()
    
    if not space:
        raise NotFoundError("Space")
    
    # Check if already in space
    for p in space.participants:
        if p.user_id == current_user.id and not p.left_at:
            raise ConflictError("Already in this space")
    
    participant = SpaceParticipant(
        space_id=space_id,
        user_id=current_user.id,
        role=ParticipantRole.LISTENER
    )
    
    db.add(participant)
    await db.flush()
    await db.refresh(participant)
    
    # Load user
    result = await db.execute(
        select(SpaceParticipant)
        .options(selectinload(SpaceParticipant.user))
        .where(SpaceParticipant.id == participant.id)
    )
    participant = result.scalar_one()
    
    return participant_to_response(participant)


@router.post("/{space_id}/leave", status_code=status.HTTP_200_OK)
async def leave_space(
    space_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Leave a space.
    """
    result = await db.execute(
        select(SpaceParticipant).where(
            SpaceParticipant.space_id == space_id,
            SpaceParticipant.user_id == current_user.id,
            SpaceParticipant.left_at == None
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise NotFoundError("Participant")
    
    participant.left_at = datetime.now(timezone.utc)
    
    return {"message": "Left space successfully"}


@router.post("/{space_id}/end", status_code=status.HTTP_200_OK)
async def end_space(
    space_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    End a space (host only).
    """
    result = await db.execute(
        select(Space).where(Space.id == space_id, Space.is_active == True)
    )
    space = result.scalar_one_or_none()
    
    if not space:
        raise NotFoundError("Space")
    
    if space.host_id != current_user.id:
        raise AuthorizationError("Only the host can end the space")
    
    space.is_active = False
    space.ended_at = datetime.now(timezone.utc)
    
    return {"message": "Space ended"}


@router.post("/{space_id}/raise-hand", status_code=status.HTTP_200_OK)
async def raise_hand(
    space_id: int,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Raise/lower hand in a space.
    """
    result = await db.execute(
        select(SpaceParticipant).where(
            SpaceParticipant.space_id == space_id,
            SpaceParticipant.user_id == current_user.id,
            SpaceParticipant.left_at == None
        )
    )
    participant = result.scalar_one_or_none()
    
    if not participant:
        raise NotFoundError("Participant")
    
    participant.hand_raised = not participant.hand_raised
    
    return {"hand_raised": participant.hand_raised}


@router.get("/{space_id}/messages", response_model=List[SpaceMessageResponse])
async def get_space_messages(
    space_id: int,
    db: DbSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """
    Get chat messages in a space.
    """
    offset = (page - 1) * per_page
    
    query = (
        select(SpaceMessage)
        .options(selectinload(SpaceMessage.user))
        .where(SpaceMessage.space_id == space_id)
        .order_by(SpaceMessage.created_at.desc())
    )
    
    result = await db.execute(query.offset(offset).limit(per_page))
    messages = result.scalars().all()
    
    return [
        SpaceMessageResponse(
            id=m.id,
            user=UserPublic(
                id=m.user.id,
                name=m.user.name,
                handle=m.user.handle,
                avatar_url=m.user.avatar_url,
                bio=m.user.bio,
                stats=UserStats(
                    followers=m.user.followers_count,
                    following=m.user.following_count
                ),
                is_verified=m.user.is_verified
            ),
            content=m.content,
            timestamp=m.created_at
        )
        for m in reversed(messages)
    ]


@router.post("/{space_id}/messages", response_model=SpaceMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_space_message(
    space_id: int,
    data: SpaceMessageCreate,
    db: DbSession,
    current_user: CurrentUser
):
    """
    Send a chat message in a space.
    """
    # Verify user is in space
    result = await db.execute(
        select(SpaceParticipant).where(
            SpaceParticipant.space_id == space_id,
            SpaceParticipant.user_id == current_user.id,
            SpaceParticipant.left_at == None
        )
    )
    if not result.scalar_one_or_none():
        raise AuthorizationError("Must be in space to send messages")
    
    message = SpaceMessage(
        space_id=space_id,
        user_id=current_user.id,
        content=data.content
    )
    
    db.add(message)
    await db.flush()
    await db.refresh(message)
    
    return SpaceMessageResponse(
        id=message.id,
        user=UserPublic(
            id=current_user.id,
            name=current_user.name,
            handle=current_user.handle,
            avatar_url=current_user.avatar_url,
            bio=current_user.bio,
            stats=UserStats(
                followers=current_user.followers_count,
                following=current_user.following_count
            ),
            is_verified=current_user.is_verified
        ),
        content=message.content,
        timestamp=message.created_at
    )
