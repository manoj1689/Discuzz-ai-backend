"""
AI API endpoints for context profile generation and delegate.
"""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser
from app.services.ai_service import ai_service
from app.schemas.ai import (
    InterviewRequest,
    InterviewResponse,
    ContextProfileRequest,
    ContextProfileResponse,
    DelegateRequest,
    DelegateResponse
)


router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/interview", response_model=InterviewResponse)
async def generate_interview_questions(
    data: InterviewRequest,
    current_user: CurrentUser
):
    """
    Generate interview questions for a draft post.
    """
    questions = await ai_service.generate_interview_questions(data.draft)
    return InterviewResponse(questions=questions)


@router.post("/context-profile", response_model=ContextProfileResponse)
async def generate_context_profile(
    data: ContextProfileRequest,
    current_user: CurrentUser
):
    """
    Generate a context profile from draft and interview history.
    """
    profile = await ai_service.generate_context_profile(
        data.draft,
        data.interview_history
    )
    return ContextProfileResponse(profile=profile)


@router.post("/delegate", response_model=DelegateResponse)
async def get_delegate_response(
    data: DelegateRequest,
    current_user: CurrentUser
):
    """
    Get an AI delegate response to a reader's question.
    """
    response = await ai_service.generate_delegate_response(
        data.original_post,
        data.profile,
        data.user_query,
        data.chat_history
    )
    return DelegateResponse(response=response)
