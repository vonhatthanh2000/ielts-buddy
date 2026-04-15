"""User domain models (API, services, persistence)."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Row from public.users (adjust fields to match your Supabase table)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Primary key (uuid as string).")
    name: str = Field(..., description="User's name.")
    created_at: Optional[str] = Field(
        None, description="ISO-8601 timestamp from Postgres, if present."
    )
