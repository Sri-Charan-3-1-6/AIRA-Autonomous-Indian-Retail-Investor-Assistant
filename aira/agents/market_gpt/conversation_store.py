"""AIRA module: agents/market_gpt/conversation_store.py"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_ALLOWED_ROLES = {"user", "assistant"}
_FALLBACK_SESSIONS: dict[str, dict[str, Any]] = {}


async def create_session(user_id: str, supabase_client) -> str:
    session_id = str(uuid4())

    def _op() -> None:
        supabase_client.table("conversations").insert(
            {
                "user_id": user_id,
                "session_id": session_id,
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

    try:
        await asyncio.to_thread(_op)
        logger.info("Created conversation session session_id=%s user_id=%s", session_id, user_id)
    except Exception as exc:
        logger.warning(
            "Supabase conversation table unavailable, using in-memory fallback session_id=%s error=%s",
            session_id,
            exc,
        )
        _FALLBACK_SESSIONS[session_id] = {
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    return session_id


async def get_history(session_id: str, supabase_client) -> list[dict[str, str]]:
    def _op() -> list[dict[str, str]]:
        response = (
            supabase_client.table("conversations")
            .select("messages")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return []

        messages = response.data[0].get("messages") or []
        history: list[dict[str, str]] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "").strip().lower()
            content = str(message.get("content") or "").strip()
            if role in _ALLOWED_ROLES and content:
                history.append({"role": role, "content": content})
        return history

    try:
        return await asyncio.to_thread(_op)
    except Exception as exc:
        logger.warning("Failed Supabase history fetch, using fallback session_id=%s error=%s", session_id, exc)
        fallback = _FALLBACK_SESSIONS.get(session_id)
        if not fallback:
            return []
        history: list[dict[str, str]] = []
        for message in fallback.get("messages", []):
            role = str(message.get("role") or "").strip().lower()
            content = str(message.get("content") or "").strip()
            if role in _ALLOWED_ROLES and content:
                history.append({"role": role, "content": content})
        return history


async def add_message(session_id: str, role: str, content: str, supabase_client) -> None:
    role_clean = str(role).strip().lower()
    if role_clean not in _ALLOWED_ROLES:
        raise ValueError("role must be either user or assistant")

    content_clean = str(content).strip()
    if not content_clean:
        raise ValueError("content cannot be empty")

    def _op() -> None:
        response = (
            supabase_client.table("conversations")
            .select("messages")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise ValueError(f"session_id '{session_id}' not found")

        existing_messages = response.data[0].get("messages") or []
        existing_messages.append(
            {
                "role": role_clean,
                "content": content_clean,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        supabase_client.table("conversations").update(
            {
                "messages": existing_messages,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("session_id", session_id).execute()

    try:
        await asyncio.to_thread(_op)
    except Exception as exc:
        logger.warning("Failed Supabase add_message, using fallback session_id=%s error=%s", session_id, exc)
        if session_id not in _FALLBACK_SESSIONS:
            _FALLBACK_SESSIONS[session_id] = {
                "user_id": "unknown",
                "messages": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        _FALLBACK_SESSIONS[session_id]["messages"].append(
            {
                "role": role_clean,
                "content": content_clean,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        _FALLBACK_SESSIONS[session_id]["updated_at"] = datetime.now(timezone.utc).isoformat()


async def get_recent_history(session_id: str, max_messages: int = 10, supabase_client=None) -> list[dict[str, str]]:
    if supabase_client is None:
        raise ValueError("supabase_client is required")

    history = await get_history(session_id=session_id, supabase_client=supabase_client)
    if max_messages <= 0:
        return []
    return history[-max_messages:]


async def clear_session(session_id: str, supabase_client) -> None:
    def _op() -> None:
        supabase_client.table("conversations").delete().eq("session_id", session_id).execute()

    try:
        await asyncio.to_thread(_op)
    except Exception as exc:
        logger.warning("Failed Supabase clear_session, using fallback session_id=%s error=%s", session_id, exc)
    _FALLBACK_SESSIONS.pop(session_id, None)
    logger.info("Cleared conversation session session_id=%s", session_id)
