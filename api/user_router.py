from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from supabase import Client

from db.supabase_client import get_supabase
from services import user_service

router = APIRouter(prefix="/v1/users", tags=["users"])


class UserCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(
        default=None, max_length=200, description="Optional display name."
    )


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(
        default=None, max_length=200, description="Set to empty string to clear."
    )


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"extra": "ignore"}


def _to_response(row: dict) -> UserResponse:
    return UserResponse.model_validate(row)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, supabase: Client = Depends(get_supabase)) -> UserResponse:
    try:
        row = user_service.create_user(supabase, body.email, body.display_name)
    except ValueError as exc:
        if str(exc) == "Email already registered":
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _to_response(row)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID, supabase: Client = Depends(get_supabase)
) -> UserResponse:
    row = user_service.get_user_by_id(supabase, str(user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(row)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID, body: UserUpdate, supabase: Client = Depends(get_supabase)
) -> UserResponse:
    row = user_service.update_user(supabase, str(user_id), body.display_name)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(row)
