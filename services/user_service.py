from typing import Optional

from supabase import Client


def get_user_by_id(supabase: Client, user_id: str) -> Optional[dict]:
    res = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not res.data:
        return None
    return res.data[0]


def get_user_by_username(supabase: Client, username: str) -> Optional[dict]:
    """Lookup by normalized username (store usernames lowercase in Supabase)."""
    key = username.strip().lower()
    if not key:
        return None
    res = supabase.table("users").select("*").eq("username", key).limit(1).execute()
    if not res.data:
        return None
    return res.data[0]


def create_user(
    supabase: Client,
    *,
    username: str,
    password_hash: str,
    name: Optional[str],
) -> dict:
    """Insert a new user row. ``username`` must be normalized (lowercase) before calling."""
    display = (name.strip() if name else None) or username
    row = {
        "username": username,
        "password_hash": password_hash,
        "name": display,
    }
    res = supabase.table("users").insert(row).select("id", "username", "name", "created_at").execute()
    if not res.data:
        raise RuntimeError("Failed to create user")
    return res.data[0]
