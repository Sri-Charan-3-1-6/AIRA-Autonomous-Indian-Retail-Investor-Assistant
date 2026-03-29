"""AIRA module: api/orchestrator_routes.py"""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from models.agent_task import (
    AgentTask,
    CompleteStockAnalysis,
    MorningPipelineRequest,
    MorningReport,
    PortfolioIntelligence,
    SystemStatusResponse,
)
from orchestrator.orchestrator import Orchestrator

router = APIRouter()
_morning_pipeline_lock = asyncio.Lock()


class OrchestrateRunRequest(BaseModel):
    agent_name: str = Field(..., description="Registered agent name")
    user_id: str = Field(..., description="User UUID")
    input_data: dict = Field(default_factory=dict, description="Task input payload")

    model_config = {
        "json_schema_extra": {
            "example": {
                "agent_name": "signal_hunter",
                "user_id": "b6f9c653-39a1-4c0f-b7a2-1213ab4f4a6e",
                "input_data": {"watchlist": ["TCS", "INFY"]},
            }
        }
    }


def get_orchestrator(request: Request) -> Orchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator is not initialized")
    return orchestrator


@router.post("/run", response_model=AgentTask)
async def run_orchestration(payload: OrchestrateRunRequest, request: Request) -> AgentTask:
    orchestrator = get_orchestrator(request)

    if payload.agent_name not in orchestrator.agents:
        raise HTTPException(status_code=404, detail=f"Agent '{payload.agent_name}' not found")

    try:
        task = AgentTask(
            agent_name=payload.agent_name,
            user_id=payload.user_id,
            input_data=payload.input_data,
        )
        return await orchestrator.dispatch(payload.agent_name, task)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestrator run failed: {exc}") from exc


@router.post("/morning-pipeline", response_model=MorningReport)
async def run_morning_pipeline(payload: MorningPipelineRequest, request: Request) -> MorningReport:
    orchestrator = get_orchestrator(request)
    if _morning_pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="Morning pipeline is already running")

    try:
        async with _morning_pipeline_lock:
            report = await orchestrator.run_morning_pipeline(payload.user_id)
            return MorningReport(**report)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Morning pipeline failed: {exc}") from exc


@router.get("/portfolio-intelligence/{user_id}", response_model=PortfolioIntelligence)
async def get_portfolio_intelligence(user_id: str, request: Request) -> PortfolioIntelligence:
    orchestrator = get_orchestrator(request)
    try:
        result = await orchestrator.get_portfolio_intelligence(user_id)
        return PortfolioIntelligence(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Portfolio intelligence failed: {exc}") from exc


@router.get("/analyze/{symbol}", response_model=CompleteStockAnalysis)
async def analyze_stock_complete(symbol: str, request: Request, user_id: str = "system") -> CompleteStockAnalysis:
    orchestrator = get_orchestrator(request)
    try:
        result = await orchestrator.analyze_stock_complete(symbol=symbol, user_id=user_id)
        return CompleteStockAnalysis(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Complete stock analysis failed: {exc}") from exc


@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status(request: Request) -> SystemStatusResponse:
    orchestrator = get_orchestrator(request)
    try:
        result = await orchestrator.get_system_status()
        return SystemStatusResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"System status failed: {exc}") from exc


@router.get("/pipeline-history")
async def get_pipeline_history(request: Request) -> dict:
    orchestrator = get_orchestrator(request)
    try:
        reports = await orchestrator.get_pipeline_history(limit=7)
        return {"count": len(reports), "reports": reports}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline history fetch failed: {exc}") from exc
