"""AIRA module: api/charts.py"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from agents.chart_whisperer.agent import ChartWhispererAgent
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)
router = APIRouter()


def _agent(request: Request) -> ChartWhispererAgent:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator and "chart_whisperer" in orchestrator.agents:
        candidate = orchestrator.agents["chart_whisperer"]
        if isinstance(candidate, ChartWhispererAgent):
            return candidate
    return ChartWhispererAgent()


@router.get("/analyze/{symbol}")
async def analyze_symbol(
    request: Request,
    symbol: str,
    period: str = Query(default="6mo"),
    interval: str = Query(default="1d"),
    include_chart: bool = Query(default=True),
) -> dict[str, Any]:
    task = AgentTask(
        agent_name="chart_whisperer",
        user_id="system",
        input_data={
            "action": "analyze",
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "include_chart": include_chart,
        },
    )
    result = await _agent(request).run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Analysis failed")
    return result.output_data


@router.get("/backtest/{symbol}")
async def backtest_symbol(request: Request, symbol: str) -> dict[str, Any]:
    task = AgentTask(
        agent_name="chart_whisperer",
        user_id="system",
        input_data={"action": "backtest", "symbol": symbol, "period": "2y", "interval": "1d", "include_chart": False},
    )
    result = await _agent(request).run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Backtest failed")
    return result.output_data


@router.get("/compare")
async def compare_symbols(request: Request, symbols: str = Query(..., description="Comma-separated symbols")) -> dict[str, Any]:
    parts = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two symbols for comparison")

    task = AgentTask(
        agent_name="chart_whisperer",
        user_id="system",
        input_data={"action": "compare", "symbols": parts, "period": "6mo", "interval": "1d", "include_chart": False},
    )
    result = await _agent(request).run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Compare failed")
    return result.output_data


@router.get("/breakouts")
async def scan_breakouts(request: Request) -> dict[str, Any]:
    task = AgentTask(
        agent_name="chart_whisperer",
        user_id="system",
        input_data={"action": "scan_breakouts", "period": "6mo", "interval": "1d", "include_chart": False},
    )
    result = await _agent(request).run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Breakout scan failed")
    return result.output_data


@router.get("/pattern/{symbol}/{pattern_name}")
async def pattern_detail(request: Request, symbol: str, pattern_name: str) -> dict[str, Any]:
    task = AgentTask(
        agent_name="chart_whisperer",
        user_id="system",
        input_data={
            "action": "analyze",
            "symbol": symbol,
            "period": "2y",
            "interval": "1d",
            "include_chart": False,
        },
    )
    result = await _agent(request).run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Pattern analysis failed")

    payload = result.output_data
    patterns = [p for p in payload.get("patterns", []) if str(p.get("pattern_name", "")).lower() == pattern_name.lower()]
    backtests = [b for b in payload.get("backtest_results", []) if str(b.get("pattern_name", "")).lower() == pattern_name.lower()]

    return {
        "symbol": symbol.upper(),
        "pattern_name": pattern_name,
        "matches_found": len(patterns),
        "patterns": patterns,
        "backtest": backtests[0] if backtests else None,
        "analysis_summary": payload.get("indicator_interpretation", {}),
    }
