"""Singleton Supabase client for API and services."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """
    Singleton Supabase client for the API layer (Depends) and services.

    Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env (service role for
    server-side writes; use the anon key only if your RLS policies allow it).
    SUPABASE_KEY is accepted as an alias for the service role key.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set in the environment."
        )
    return create_client(url, key)
