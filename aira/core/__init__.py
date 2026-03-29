"""AIRA module: core/__init__.py"""

from .config import get_settings
from .supabase_client import get_supabase, init_supabase
from .gemini_client import get_gemini_client, init_gemini_client

__all__ = [
    "get_settings",
    "get_supabase",
    "init_supabase",
    "get_gemini_client",
    "init_gemini_client",
]
