"""AIRA module: db/crud.py"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from core.supabase_client import get_supabase
from models.agent_task import AgentTask
from models.user import User, UserCreate


async def create_user(payload: UserCreate) -> User:
    def _op() -> Dict[str, Any]:
        client = get_supabase()
        response = (
            client.table("users")
            .insert(
                {
                    "email": payload.email,
                    "name": payload.name,
                    "risk_profile": payload.risk_profile,
                }
            )
            .execute()
        )
        if not response.data:
            raise ValueError("Failed to create user")
        return response.data[0]

    row = await asyncio.to_thread(_op)
    return User(**row)


async def get_user(user_id: str) -> Optional[User]:
    def _op() -> Optional[Dict[str, Any]]:
        client = get_supabase()
        response = client.table("users").select("*").eq("id", user_id).limit(1).execute()
        if not response.data:
            return None
        return response.data[0]

    row = await asyncio.to_thread(_op)
    if row is None:
        return None
    return User(**row)


async def log_audit(task: AgentTask) -> None:
    def _op() -> None:
        client = get_supabase()
        client.table("audit_logs").insert(
            {
                "task_id": task.task_id,
                "agent_name": task.agent_name,
                "user_id": task.user_id,
                "input_data": task.input_data,
                "output_data": task.output_data,
                "status": task.status,
                "confidence_score": task.confidence_score,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message,
            }
        ).execute()

    await asyncio.to_thread(_op)


def get_audit_logs(
    supabase_client,
    user_id: str | None = None,
    limit: int | None = None,
    agent_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    query = supabase_client.table("audit_logs").select("*")

    if user_id is not None:
        query = query.eq("user_id", user_id)
    if agent_name is not None:
        query = query.eq("agent_name", agent_name)
    if start_date is not None:
        query = query.gte("created_at", start_date)
    if end_date is not None:
        query = query.lte("created_at", end_date)

    query = query.order("created_at", desc=True)
    if limit is not None:
        query = query.limit(limit)

    response = query.execute()
    return response.data or []


def get_audit_stats(supabase_client) -> dict[str, Any]:
    base_response = supabase_client.table("audit_logs").select("agent_name,confidence_score,status").execute()
    rows = base_response.data or []

    total_decisions = len(rows)
    decisions_by_agent: dict[str, int] = {}
    confidence_totals_by_agent: dict[str, float] = {}
    confidence_counts_by_agent: dict[str, int] = {}
    total_failed = 0
    total_completed = 0

    for row in rows:
        agent = str(row.get("agent_name") or "unknown")
        decisions_by_agent[agent] = decisions_by_agent.get(agent, 0) + 1

        confidence = row.get("confidence_score")
        try:
            confidence_value = float(confidence)
            confidence_totals_by_agent[agent] = confidence_totals_by_agent.get(agent, 0.0) + confidence_value
            confidence_counts_by_agent[agent] = confidence_counts_by_agent.get(agent, 0) + 1
        except (TypeError, ValueError):
            pass

        status = str(row.get("status") or "").lower()
        if status == "completed":
            total_completed += 1
        elif status == "failed":
            total_failed += 1

    avg_confidence_by_agent: dict[str, float] = {}
    for agent, total_conf in confidence_totals_by_agent.items():
        count = confidence_counts_by_agent.get(agent, 0)
        avg_confidence_by_agent[agent] = (total_conf / count) if count else 0.0

    success_rate = (total_completed / total_decisions) if total_decisions else 0.0

    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    last_24h_response = (
        supabase_client.table("audit_logs")
        .select("id")
        .gte("created_at", since_24h)
        .execute()
    )
    last_24h_count = len(last_24h_response.data or [])

    return {
        "total_decisions": total_decisions,
        "decisions_by_agent": decisions_by_agent,
        "avg_confidence_by_agent": avg_confidence_by_agent,
        "success_rate": success_rate,
        "total_failed": total_failed,
        "last_24h_count": last_24h_count,
    }


def get_agent_decision_trail(supabase_client, task_id: str) -> dict[str, Any] | None:
    response = (
        supabase_client.table("audit_logs")
        .select("*")
        .eq("task_id", task_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    return rows[0]
