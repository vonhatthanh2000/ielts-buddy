from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from api.deps import get_current_user_id
from schemas import UserResponse
from db.supabase_client import get_supabase
from services import user_service

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> UserResponse:
    row = user_service.get_user_by_id(supabase, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(row)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, supabase: Client = Depends(get_supabase)) -> UserResponse:
    row = user_service.get_user_by_id(supabase, str(user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(row)
