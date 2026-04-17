"""User domain models (API, services, persistence)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Row from public.users (password_hash is never returned — stripped via extra ignore)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Primary key (uuid as string).")
    username: Optional[str] = Field(None, description="Login handle (unique).")
    email: Optional[str] = Field(None, description="Account email (unique, lowercase).")
    name: Optional[str] = Field(None, description="Display name (optional if not stored).")
    created_at: Optional[str] = Field(
        None, description="ISO-8601 timestamp from Postgres, if present."
    )
