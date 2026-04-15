from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import decode_session_token

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
