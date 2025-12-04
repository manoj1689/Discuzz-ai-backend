"""
Pydantic schemas for Authentication API.
"""

from pydantic import AliasChoices, BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(validation_alias=AliasChoices("email", "username"))
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RegisterRequest(BaseModel):
    """Registration request schema."""
    email: EmailStr = Field(validation_alias=AliasChoices("email", "username"))
    password: str = Field(..., min_length=8)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    handle: str | None = Field(default=None, min_length=3, max_length=50)


class GoogleLoginRequest(BaseModel):
    """Google OAuth login request."""
    id_token: str = Field(..., min_length=10)


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class VerificationRequest(BaseModel):
    """Email verification request."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    """Resend verification code request."""
    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)
