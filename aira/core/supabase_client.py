"""AIRA module: core/supabase_client.py"""

from typing import Optional

from supabase import Client, create_client

from core.config import get_settings

_supabase_client: Optional[Client] = None


def init_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _supabase_client


def get_supabase() -> Client:
    if _supabase_client is None:
        return init_supabase()
    return _supabase_client
