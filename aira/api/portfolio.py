"""AIRA module: api/portfolio.py"""

import asyncio
import base64
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from core.supabase_client import get_supabase
from models.agent_task import AgentTask

router = APIRouter()


def _extract_file_type(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".xlsx"):
        return "excel"
    if lower.endswith(".csv"):
        return "csv"
    raise ValueError("Unsupported file type. Only pdf, xlsx, and csv are allowed.")


@router.post("/upload")
async def upload_portfolio_statement(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(...),
) -> dict[str, Any]:
    try:
        file_type = _extract_file_type(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")

    encoded = base64.b64encode(file_bytes).decode("utf-8")

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator is not initialized")
    agent = orchestrator.agents.get("portfolio_doctor")
    if agent is None:
        raise HTTPException(status_code=503, detail="Portfolio Doctor agent is not registered")

    task = AgentTask(
        agent_name="portfolio_doctor",
        user_id=user_id,
        input_data={
            "file_bytes_base64": encoded,
            "file_type": file_type,
            "user_id": user_id,
        },
    )

    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Portfolio analysis failed")

    return result.output_data


@router.get("/{user_id}/analysis")
async def get_latest_analysis(user_id: str) -> dict[str, Any]:
    def _op() -> dict[str, Any] | None:
        client = get_supabase()
        resp = (
            client.table("portfolios")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return resp.data[0]

    row = await asyncio.to_thread(_op)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No portfolio analysis found for user_id '{user_id}'")

    return row


@router.get("/{user_id}/history")
async def get_analysis_history(user_id: str) -> list[dict[str, Any]]:
    def _op() -> list[dict[str, Any]]:
        client = get_supabase()
        resp = (
            client.table("portfolios")
            .select("id, created_at, xirr, raw_data")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []

    rows = await asyncio.to_thread(_op)

    history: list[dict[str, Any]] = []
    for row in rows:
        raw_data = row.get("raw_data") or {}
        overall_score = raw_data.get("overall_score")
        if overall_score is None and isinstance(raw_data.get("rebalancing_plan"), dict):
            overall_score = raw_data["rebalancing_plan"].get("overall_score")

        history.append(
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "xirr": row.get("xirr"),
                "overall_score": overall_score,
            }
        )

    return history
