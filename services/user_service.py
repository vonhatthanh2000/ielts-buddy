from typing import Optional

from supabase import Client

# Expects a public.users table, for example:
#   id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
#   email text UNIQUE NOT NULL,
#   display_name text,
#   created_at timestamptz NOT NULL DEFAULT now()


def create_user(supabase: Client, email: str, display_name: Optional[str]) -> dict:
    row = {
        "email": email.strip().lower(),
        "display_name": display_name.strip() if display_name else None,
    }
    try:
        res = supabase.table("users").insert(row).select("*").execute()
    except Exception as e:
        err = str(e).lower()
        if any(x in err for x in ("duplicate", "unique", "23505")):
            raise ValueError("Email already registered") from e
        raise
    if not res.data:
        raise RuntimeError("Failed to create user")
    return res.data[0]


def get_user_by_id(supabase: Client, user_id: str) -> Optional[dict]:
    res = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not res.data:
        return None
    return res.data[0]


def update_user(
    supabase: Client, user_id: str, display_name: Optional[str]
) -> Optional[dict]:
    patch: dict = {}
    if display_name is not None:
        patch["display_name"] = display_name.strip() or None
    if not patch:
        return get_user_by_id(supabase, user_id)
    res = supabase.table("users").update(patch).eq("id", user_id).select("*").execute()
    if not res.data:
        return None
    return res.data[0]
