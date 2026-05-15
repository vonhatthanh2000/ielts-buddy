from typing import Any, Optional

from supabase_client import Client

MAX_PROFILES_PER_USER = 10


def list_profiles(supabase: Client, user_id: str) -> list[dict]:
    res = (
        supabase.table("profiles")
        .select("id, user_id, display_name, avatar_url, accent_color, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return list(res.data or [])


def get_profile(supabase: Client, user_id: str, profile_id: str) -> Optional[dict]:
    res = (
        supabase.table("profiles")
        .select("id, user_id, display_name, avatar_url, accent_color, created_at")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]


def _count_profiles(supabase: Client, user_id: str) -> int:
    res = (
        supabase.table("profiles")
        .select("id", count="exact", head=True)
        .eq("user_id", user_id)
        .execute()
    )
    if res.count is not None:
        return int(res.count)
    return 0


def create_profile(
    supabase: Client,
    user_id: str,
    *,
    display_name: str,
    avatar_url: Optional[str],
    accent_color: Optional[str],
) -> dict:
    if _count_profiles(supabase, user_id) >= MAX_PROFILES_PER_USER:
        raise ValueError(f"Maximum {MAX_PROFILES_PER_USER} profiles per account.")
    name = display_name.strip()
    if not name:
        raise ValueError("display_name cannot be empty.")
    row: dict[str, Any] = {
        "user_id": user_id,
        "display_name": name,
        "avatar_url": avatar_url,
        "accent_color": accent_color,
    }
    res = supabase.table("profiles").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to create profile")
    return res.data[0]


def update_profile(
    supabase: Client,
    user_id: str,
    profile_id: str,
    updates: dict[str, Any],
) -> Optional[dict]:
    if not updates:
        return get_profile(supabase, user_id, profile_id)
    res = (
        supabase.table("profiles")
        .update(updates)
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]


def delete_profile(supabase: Client, user_id: str, profile_id: str) -> bool:
    if get_profile(supabase, user_id, profile_id) is None:
        return False
    if _count_profiles(supabase, user_id) <= 1:
        raise ValueError("Cannot delete the last profile.")
    supabase.table("profiles").delete().eq("id", profile_id).eq("user_id", user_id).execute()
    return True
