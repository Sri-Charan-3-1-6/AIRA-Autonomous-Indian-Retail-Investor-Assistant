"""AIRA module: api/signals.py"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from agents.signal_hunter.agent import SignalHunterAgent
from agents.signal_hunter.fii_dii_tracker import analyze_fii_dii_trend, fetch_fii_dii_data, get_sector_fii_activity
from core.supabase_client import get_supabase
from models.agent_task import AgentTask

router = APIRouter()


def _parse_created_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _get_signal_agent(request: Request) -> SignalHunterAgent:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator and "signal_hunter" in orchestrator.agents:
        agent = orchestrator.agents["signal_hunter"]
        if isinstance(agent, SignalHunterAgent):
            return agent
    return SignalHunterAgent()


async def _fetch_cached_scan_summary() -> dict[str, Any] | None:
    def _op() -> dict[str, Any] | None:
        client = get_supabase()
        latest_resp = (
            client.table("market_signals")
            .select("id, opportunity_score, created_at")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not latest_resp.data:
            return None

        latest_row = latest_resp.data[0]
        latest_time = _parse_created_at(latest_row.get("created_at"))
        if latest_time is None:
            return None

        now = datetime.now(timezone.utc)
        if now - latest_time > timedelta(minutes=30):
            return None

        window_start = (latest_time - timedelta(minutes=30)).isoformat()
        range_resp = (
            client.table("market_signals")
            .select("id, opportunity_score, created_at")
            .gte("created_at", window_start)
            .order("created_at", desc=True)
            .execute()
        )
        rows = range_resp.data or []
        high_priority = sum(1 for row in rows if float(row.get("opportunity_score") or 0.0) > 80)

        return {
            "total_signals_found": len(rows),
            "high_priority_count": high_priority,
            "scan_time": latest_time.isoformat(),
            "cached": True,
        }

    return await asyncio.to_thread(_op)


@router.get("/scan")
async def scan_market(request: Request, force: bool = Query(False)) -> dict[str, Any]:
    if not force:
        cached = await _fetch_cached_scan_summary()
        if cached is not None:
            return cached

    agent = _get_signal_agent(request)
    task = AgentTask(
        agent_name="signal_hunter",
        user_id="system",
        input_data={"action": "scan", "user_id": "system"},
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Signal scan failed")

    output = dict(result.output_data)
    output["cached"] = False
    return output


@router.get("/top")
async def top_signals(
    limit: int = Query(default=10, ge=1, le=100),
    min_score: float = Query(default=40.0, ge=0.0, le=100.0),
    category: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    def _op() -> list[dict[str, Any]]:
        client = get_supabase()
        try:
            # Keep one row per symbol in the query, picking the highest score per symbol.
            response = (
                client.table("market_signals")
                .select("distinct on (symbol) *")
                .gte("opportunity_score", min_score)
                .order("symbol")
                .order("opportunity_score", desc=True)
                .limit(max(limit * 5, 25))
                .execute()
            )
            rows = response.data or []
        except Exception:
            response = (
                client.table("market_signals")
                .select("*")
                .gte("opportunity_score", min_score)
                .order("opportunity_score", desc=True)
                .limit(max(limit * 20, 100))
                .execute()
            )
            rows = response.data or []

        category_upper = category.upper() if category else None
        parsed: list[dict[str, Any]] = []
        best_by_symbol: dict[str, dict[str, Any]] = {}
        for row in rows:
            payload = row.get("data") or {}
            signal_category = str(payload.get("category") or "NEUTRAL").upper()
            if category_upper and signal_category != category_upper:
                continue

            item = {
                "id": row.get("id"),
                "symbol": row.get("symbol"),
                "company": payload.get("company") or row.get("symbol"),
                "signal_type": row.get("signal_type"),
                "opportunity_score": row.get("opportunity_score"),
                "category": signal_category,
                "explanation": payload.get("explanation") or "",
                "data": payload.get("payload") or {},
                "created_at": row.get("created_at"),
            }
            symbol = str(item.get("symbol") or "").upper()
            if not symbol:
                continue
            current = best_by_symbol.get(symbol)
            if current is None or float(item.get("opportunity_score") or 0.0) > float(current.get("opportunity_score") or 0.0):
                best_by_symbol[symbol] = item

        parsed = list(best_by_symbol.values())

        parsed.sort(key=lambda x: float(x.get("opportunity_score") or 0.0), reverse=True)
        return parsed[:limit]

    return await asyncio.to_thread(_op)


@router.get("/{user_id}/personalized")
async def personalized_signals(request: Request, user_id: str, limit: int = Query(default=10, ge=1, le=50)) -> dict[str, Any]:
    agent = _get_signal_agent(request)
    task = AgentTask(
        agent_name="signal_hunter",
        user_id=user_id,
        input_data={"action": "get_signals", "user_id": user_id, "limit": limit},
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Failed to fetch personalized signals")
    return result.output_data


@router.get("/symbol/{symbol}")
async def score_symbol(request: Request, symbol: str) -> dict[str, Any]:
    agent = _get_signal_agent(request)
    task = AgentTask(
        agent_name="signal_hunter",
        user_id="system",
        input_data={"action": "score_symbol", "symbol": symbol, "user_id": "system"},
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Failed to score symbol")
    return result.output_data


@router.get("/fii-dii")
async def fii_dii_analysis(days: int = Query(default=7, ge=1, le=30)) -> dict[str, Any]:
    latest, trend = await asyncio.gather(fetch_fii_dii_data(), analyze_fii_dii_trend(days))
    return {
        "latest": latest,
        "trend": trend,
        "sector_activity": get_sector_fii_activity(),
    }
