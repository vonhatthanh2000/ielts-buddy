from typing import Optional

from supabase import Client


def get_user_by_id(supabase: Client, user_id: str) -> Optional[dict]:
    res = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not res.data:
        return None
    return res.data[0]
