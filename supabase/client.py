"""
Supabase Python client singleton.

The repo folder is named ``supabase`` (same as the PyPI package). We clear any
already-loaded local ``supabase`` entries from ``sys.modules``, prepend the
venv ``site-packages`` to ``sys.path``, then import the installed SDK.
"""

import os
import site
import sys
from functools import lru_cache

from dotenv import load_dotenv

_site_packages = site.getsitepackages()[0]

# Drop local ``supabase`` stubs so the real package can load.
for _name in list(sys.modules):
    if _name == "supabase" or _name.startswith("supabase."):
        if _name != "supabase.client":
            del sys.modules[_name]

_inserted = False
if not sys.path or sys.path[0] != _site_packages:
    sys.path.insert(0, _site_packages)
    _inserted = True
try:
    from supabase._sync.client import Client, create_client  # type: ignore[import-not-found]
finally:
    if _inserted and sys.path and sys.path[0] == _site_packages:
        sys.path.pop(0)

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
