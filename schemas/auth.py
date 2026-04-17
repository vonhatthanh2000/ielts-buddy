"""Auth request/response models."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Username or email (email matched case-insensitively).",
    )
    password: str = Field(..., min_length=1, max_length=500)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=200)
    email: EmailStr = Field(..., max_length=320)
    password: str = Field(..., min_length=1, max_length=500)
    name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional display name; defaults to username if omitted.",
    )


class LoginResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="Signed JWT; send as Authorization: Bearer <token>.",
    )
