from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services import profile_service
from services.auth_service import decode_session_token
from supabase.client import Client, get_supabase

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header (Bearer token required).",
        )
    try:
        payload = decode_session_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session.",
        ) from None
    user_id = payload.get("sub")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(status_code=401, detail="Invalid session payload.")
    return user_id


def get_current_profile_id(
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
    x_profile_id: str = Header(
        ...,
        alias="X-Profile-Id",
        description=(
            "Active learner profile UUID; must belong to the authenticated user. "
            "Required for sentence APIs."
        ),
    ),
) -> str:
    pid = x_profile_id.strip()
    if not pid:
        raise HTTPException(
            status_code=400,
            detail="X-Profile-Id cannot be empty.",
        )
    row = profile_service.get_profile(supabase, user_id, pid)
    if row is None:
        raise HTTPException(
            status_code=403,
            detail="Profile not found or does not belong to this account.",
        )
    return pid
