"""
Pydantic schemas for AI API endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel

from app.schemas.post import ContextProfile, InterviewMessage


class InterviewRequest(BaseModel):
    """Request to generate interview questions."""
    draft: str


class InterviewResponse(BaseModel):
    """Response with generated interview questions."""
    questions: List[str]


class ContextProfileRequest(BaseModel):
    """Request to generate context profile."""
    draft: str
    interview_history: List[InterviewMessage]


class ContextProfileResponse(BaseModel):
    """Response with generated context profile."""
    profile: ContextProfile


class DelegateRequest(BaseModel):
    """Request to AI delegate for a response."""
    original_post: str
    profile: ContextProfile
    user_query: str
    chat_history: List[InterviewMessage] = []


class DelegateResponse(BaseModel):
    """Response from AI delegate."""
    response: str
