"""Auth request/response models."""

from typing import Optional

from pydantic import BaseModel, Field

from schemas.user import UserResponse


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
    """Session JWT and profile so the client can log in without an extra ``/users/me`` call."""

    access_token: str = Field(
        ...,
        description="Signed JWT (Bearer). This is not the server SESSION_SECRET.",
    )
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Token lifetime in seconds (30 days).",
    )
    user: Optional[UserResponse] = Field(
        default=None,
        description="Current user profile; set on register and login.",
    )
