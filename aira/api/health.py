"""AIRA module: api/health.py"""

import asyncio

from fastapi import APIRouter, Request

from core.config import get_settings
from core.supabase_client import get_supabase
from orchestrator.orchestrator import Orchestrator

router = APIRouter()


def get_orchestrator(request: Request) -> Orchestrator:
    return getattr(request.app.state, "orchestrator", None)


async def _check_supabase() -> dict:
    def _op() -> None:
        client = get_supabase()
        client.table("users").select("id").limit(1).execute()

    try:
        await asyncio.to_thread(_op)
        return {"status": "healthy"}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


@router.get("/health")
async def health(request: Request) -> dict:
    settings = get_settings()
    orchestrator = get_orchestrator(request)

    supabase_status = await _check_supabase()
    if orchestrator is None:
        return {
            "app": {
                "name": "AIRA",
                "version": settings.APP_VERSION,
                "environment": settings.APP_ENV,
            },
            "supabase": supabase_status,
            "agents": [],
            "system_status": "unhealthy",
            "error": "orchestrator_not_initialized",
        }

    agent_statuses = await orchestrator.get_all_agent_health()

    agents_ok = all(agent.get("status") == "healthy" for agent in agent_statuses)
    overall_status = "healthy" if supabase_status.get("status") == "healthy" and agents_ok else "unhealthy"

    return {
        "app": {
            "name": "AIRA",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        },
        "supabase": supabase_status,
        "agents": agent_statuses,
        "system_status": overall_status,
    }
