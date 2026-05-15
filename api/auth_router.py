from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user_id
from schemas import LoginRequest, LoginResponse, RegisterRequest, SwitchProfileRequest
from supabase_client import Client, get_supabase
from services import auth_service, profile_service, user_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _duplicate_username(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(x in msg for x in ("duplicate", "unique", "23505", "already exists"))


@router.post("/register", response_model=LoginResponse)
def register(body: RegisterRequest, supabase: Client = Depends(get_supabase)) -> LoginResponse:
    key = body.username.strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="Invalid username")
    email_key = body.email.strip().lower()
    if not email_key:
        raise HTTPException(status_code=400, detail="Invalid email")
    if user_service.get_user_by_username(supabase, key):
        raise HTTPException(status_code=409, detail="Username already taken")
    if user_service.get_user_by_email(supabase, email_key):
        raise HTTPException(status_code=409, detail="Email already registered")
    pw_hash = auth_service.hash_password(body.password)
    try:
        created = user_service.create_user(
            supabase,
            username=key,
            email=email_key,
            password_hash=pw_hash,
            name=body.name,
        )
    except Exception as exc:
        if _duplicate_username(exc):
            raise HTTPException(
                status_code=409,
                detail="Username or email already taken",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    user_id = str(created["id"])
    # Registration doesn't include profile_id (profile created separately)
    token, _ = auth_service.create_session_token(user_id, key)
    return LoginResponse(access_token=token)


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, supabase: Client = Depends(get_supabase)) -> LoginResponse:
    row = user_service.get_user_by_username_or_email(supabase, body.username)
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    stored = row.get("password_hash") or ""
    if not auth_service.verify_password(body.password, stored):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user_id = str(row["id"])
    username = str(row.get("username") or body.username.strip().lower())
    # No profile_id on initial login - use /switch-profile after selecting
    token, _ = auth_service.create_session_token(user_id, username)
    return LoginResponse(access_token=token)


@router.post("/switch-profile", response_model=LoginResponse)
def switch_profile(
    body: SwitchProfileRequest,
    supabase: Client = Depends(get_supabase),
    user_id: str = Depends(get_current_user_id),
) -> LoginResponse:
    """
    Switch to a profile and get a new token with profile_id embedded.

    Call this after login once the user has selected their profile.
    """
    profile_id = body.profile_id.strip()
    if not profile_id:
        raise HTTPException(status_code=400, detail="Profile ID cannot be empty.")

    # Verify profile exists and belongs to this user
    row = profile_service.get_profile(supabase, user_id, profile_id)
    if row is None:
        raise HTTPException(
            status_code=403,
            detail="Profile not found or does not belong to this account.",
        )

    # Get username for token
    user = user_service.get_user_by_id(supabase, user_id)
    username = str(user.get("username") or "") if user else ""

    # Create new token with profile_id
    token, _ = auth_service.create_session_token(user_id, username, profile_id)
    return LoginResponse(access_token=token)
