"""Auth request/response models."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1, max_length=500)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    password: str = Field(..., min_length=1, max_length=500)
    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional display name; defaults to username if omitted.",
    )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Token lifetime in seconds (30 days).",
    )
