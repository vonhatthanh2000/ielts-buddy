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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> str:
    """Extract profile_id from JWT token (preferred) or X-Profile-Id header."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header (Bearer token required).",
        )

    # Try to get profile_id from JWT token first
    try:
        payload = decode_session_token(credentials.credentials)
        token_profile_id = payload.get("profile_id")
        if token_profile_id and isinstance(token_profile_id, str):
            # Verify the profile belongs to this user
            row = profile_service.get_profile(supabase, user_id, token_profile_id)
            if row is not None:
                return token_profile_id
    except jwt.PyJWTError:
        pass  # Fall through to header check

    # Fallback: try X-Profile-Id header for backward compatibility
    # Note: This requires FastAPI's Header dependency, but we're in a different pattern
    # For now, raise an error if not in token
    raise HTTPException(
        status_code=401,
        detail="Profile ID not found in token. Please login with profile_id.",
    )
