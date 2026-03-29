"""AIRA module: api/market_gpt.py"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from agents.market_gpt import conversation_store
from agents.market_gpt.agent import MarketGPTAgent
from core.supabase_client import get_supabase
from models.agent_task import AgentTask
from models.conversation import AskRequest, MarketGPTResponse, ScenarioRequest

router = APIRouter()
logger = logging.getLogger(__name__)

_summary_cache: dict[str, Any] = {
    "expires_at": None,
    "payload": None,
}


def _get_market_gpt_agent(request: Request) -> MarketGPTAgent:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator and "market_gpt" in orchestrator.agents:
        agent = orchestrator.agents["market_gpt"]
        if isinstance(agent, MarketGPTAgent):
            return agent
    return MarketGPTAgent()


@router.post("/ask", response_model=MarketGPTResponse)
async def ask_market_gpt(payload: AskRequest, request: Request) -> dict[str, Any]:
    agent = _get_market_gpt_agent(request)
    task = AgentTask(
        agent_name="market_gpt",
        user_id=payload.user_id,
        input_data={
            "action": "ask",
            "user_id": payload.user_id,
            "question": payload.question,
            "session_id": payload.session_id,
            "symbol": payload.symbol,
            "include_portfolio_context": payload.include_portfolio_context,
        },
    )

    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "MarketGPT ask failed")

    return result.output_data


@router.post("/scenario", response_model=MarketGPTResponse)
async def run_scenario(payload: ScenarioRequest, request: Request) -> dict[str, Any]:
    allowed = {"sector_drop", "market_crash", "interest_rate", "custom"}
    if payload.scenario_type not in allowed:
        raise HTTPException(status_code=400, detail=f"scenario_type must be one of {sorted(allowed)}")

    agent = _get_market_gpt_agent(request)
    task = AgentTask(
        agent_name="market_gpt",
        user_id=payload.user_id,
        input_data={
            "action": "scenario",
            "user_id": payload.user_id,
            "scenario_type": payload.scenario_type,
            "scenario_params": payload.scenario_params,
        },
    )

    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Scenario analysis failed")
    return result.output_data


@router.get("/summary", response_model=MarketGPTResponse)
async def get_daily_market_summary(request: Request) -> dict[str, Any]:
    expires_at = _summary_cache.get("expires_at")
    if isinstance(expires_at, datetime) and expires_at > datetime.now(timezone.utc):
        payload = _summary_cache.get("payload")
        if payload:
            return payload

    agent = _get_market_gpt_agent(request)
    task = AgentTask(
        agent_name="market_gpt",
        user_id="system",
        input_data={
            "action": "summarize",
            "user_id": "system",
        },
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Summary generation failed")

    _summary_cache["payload"] = result.output_data
    _summary_cache["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=30)
    return result.output_data


@router.get("/analyze/{symbol}", response_model=MarketGPTResponse)
async def analyze_stock(symbol: str, request: Request, user_id: str | None = Query(default=None)) -> dict[str, Any]:
    agent = _get_market_gpt_agent(request)
    task = AgentTask(
        agent_name="market_gpt",
        user_id=user_id or "system",
        input_data={
            "action": "analyze_stock",
            "user_id": user_id or "system",
            "symbol": symbol,
        },
    )

    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Stock analysis failed")
    return result.output_data


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str) -> dict[str, Any]:
    supabase_client = get_supabase()
    history = await conversation_store.get_history(session_id=session_id, supabase_client=supabase_client)
    return {
        "session_id": session_id,
        "messages": history,
        "count": len(history),
    }


@router.delete("/session/{session_id}")
async def clear_session_history(session_id: str) -> dict[str, Any]:
    supabase_client = get_supabase()
    await conversation_store.clear_session(session_id=session_id, supabase_client=supabase_client)
    return {
        "session_id": session_id,
        "status": "cleared",
    }
