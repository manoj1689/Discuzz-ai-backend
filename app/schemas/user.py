"""
Pydantic schemas for User API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserStats(BaseModel):
    """User statistics."""
    followers: int = 0
    following: int = 0


class UserBase(BaseModel):
    """Base user schema."""
    name: str = Field(..., min_length=1, max_length=100)
    handle: str = Field(..., min_length=3, max_length=50)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    
    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        if not v.startswith("@"):
            v = f"@{v}"
        if not re.match(r"^@[a-zA-Z0-9_]{2,49}$", v):
            raise ValueError("Handle must contain only letters, numbers, and underscores")
        return v.lower()


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=100)
    handle: str = Field(..., min_length=3, max_length=50)
    
    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        if not v.startswith("@"):
            v = f"@{v}"
        if not re.match(r"^@[a-zA-Z0-9_]{2,49}$", v):
            raise ValueError("Handle must contain only letters, numbers, and underscores")
        return v.lower()


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = None
    language: Optional[str] = Field(None, max_length=10)
    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    notifications_enabled: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: EmailStr
    name: str
    handle: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    language: Optional[str] = None
    interests: List[str] = []
    stats: UserStats
    is_verified: bool = False
    created_at: datetime
    
    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Public user profile (without email)."""
    id: int
    name: str
    handle: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    stats: UserStats
    is_verified: bool = False
    
    model_config = {"from_attributes": True}


class UserInterests(BaseModel):
    """User interests update."""
    languages: List[str] = []
    topics: List[str] = []
