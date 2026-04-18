"""Profile selection models (per-account learner profiles)."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    display_name: str
    avatar_url: Optional[str] = None
    accent_color: Optional[str] = None
    created_at: Optional[str] = None


class ProfileCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=120)
    avatar_url: Optional[str] = Field(None, max_length=2000)
    accent_color: Optional[str] = Field(
        None,
        max_length=32,
        description="Optional UI color token (e.g. hex) for avatar ring/fallback.",
    )


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=120)
    avatar_url: Optional[str] = Field(None, max_length=2000)
    accent_color: Optional[str] = Field(None, max_length=32)


class ProfileListResponse(BaseModel):
    profiles: List[ProfileResponse]
