from fastapi import APIRouter, Depends, HTTPException

from schemas import LoginRequest, LoginResponse, RegisterRequest
from supabase.client import Client, get_supabase
from services import auth_service, user_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _duplicate_username(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(x in msg for x in ("duplicate", "unique", "23505", "already exists"))


@router.post("/register", response_model=LoginResponse)
def register(body: RegisterRequest, supabase: Client = Depends(get_supabase)) -> LoginResponse:
    key = body.username.strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="Invalid username")
    if user_service.get_user_by_username(supabase, key):
        raise HTTPException(status_code=409, detail="Username already taken")
    pw_hash = auth_service.hash_password(body.password)
    try:
        created = user_service.create_user(
            supabase,
            username=key,
            password_hash=pw_hash,
            name=body.name,
        )
    except Exception as exc:
        if _duplicate_username(exc):
            raise HTTPException(status_code=409, detail="Username already taken") from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    user_id = str(created["id"])
    token, expires_in = auth_service.create_session_token(user_id, key)
    return LoginResponse(access_token=token, expires_in=expires_in)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, supabase: Client = Depends(get_supabase)) -> LoginResponse:
    row = user_service.get_user_by_username(supabase, body.username)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    stored = row.get("password_hash") or ""
    if not auth_service.verify_password(body.password, stored):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user_id = str(row["id"])
    username = str(row.get("username") or body.username.strip().lower())
    token, expires_in = auth_service.create_session_token(user_id, username)
    return LoginResponse(access_token=token, expires_in=expires_in)
