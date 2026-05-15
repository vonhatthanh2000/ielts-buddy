"""App Supabase client (not the PyPI ``supabase`` package — see ``supabase/migrations/``)."""

from supabase_client.client import Client, get_supabase

__all__ = ["Client", "get_supabase"]
