from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from api.deps import get_current_user_id
from schemas import (
    ProfileCreate,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdate,
)
from supabase_client import Client, get_supabase
from services import profile_service

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])


@router.get("", response_model=ProfileListResponse)
def list_profiles(
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> ProfileListResponse:
    rows = profile_service.list_profiles(supabase, user_id)
    return ProfileListResponse(
        profiles=[ProfileResponse.model_validate(r) for r in rows],
    )


@router.post("", response_model=ProfileResponse)
def create_profile(
    body: ProfileCreate,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> ProfileResponse:
    try:
        row = profile_service.create_profile(
            supabase,
            user_id,
            display_name=body.display_name,
            avatar_url=body.avatar_url,
            accent_color=body.accent_color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ProfileResponse.model_validate(row)


@router.patch("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: UUID,
    body: ProfileUpdate,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> ProfileResponse:
    raw = body.model_dump(exclude_unset=True)
    if "display_name" in raw and raw["display_name"] is not None:
        raw["display_name"] = raw["display_name"].strip()
        if not raw["display_name"]:
            raise HTTPException(status_code=400, detail="display_name cannot be empty.")
    if not raw:
        row = profile_service.get_profile(supabase, user_id, str(profile_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Profile not found")
        return ProfileResponse.model_validate(row)
    row = profile_service.update_profile(supabase, user_id, str(profile_id), raw)
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileResponse.model_validate(row)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: UUID,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    try:
        ok = profile_service.delete_profile(supabase, user_id, str(profile_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Profile not found")
    return Response(status_code=204)
