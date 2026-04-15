import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

SESSION_DAYS = 30


def _secret() -> str:
    secret = os.getenv("SESSION_SECRET") or os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "SESSION_SECRET (or JWT_SECRET) must be set for login tokens."
        )
    return secret


def hash_password(plain: str) -> str:
    """Hash a password for storing in ``users.password_hash`` (bcrypt)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_session_token(user_id: str, username: str) -> tuple[str, int]:
    """Return (jwt, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=SESSION_DAYS)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "iat": now,
        "exp": exp,
    }
    token = jwt.encode(payload, _secret(), algorithm="HS256")
    expires_in = int((exp - now).total_seconds())
    return token, expires_in


def decode_session_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=["HS256"])
