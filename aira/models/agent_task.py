"""AIRA module: models/agent_task.py"""

from datetime import datetime
from typing import Any, Dict, Optional, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = Field(..., description="Target agent name")
    user_id: str = Field(..., description="User UUID")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input payload")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output payload")
    status: str = Field(default="pending", description="pending, running, completed, failed")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": "3d1eb49d-2af0-431f-86af-1415adf739f2",
                "agent_name": "signal_hunter",
                "user_id": "b6f9c653-39a1-4c0f-b7a2-1213ab4f4a6e",
                "input_data": {"watchlist": ["TCS", "INFY"]},
                "output_data": {},
                "status": "pending",
                "confidence_score": 0.0,
                "created_at": "2026-03-26T06:30:00Z",
                "completed_at": None,
                "error_message": None,
            }
        }
    }


class MorningPipelineRequest(BaseModel):
    user_id: str = Field(..., description="User ID for morning orchestration run")


class MorningReport(BaseModel):
    pipeline_run_at: str
    signals_found: int
    breakouts_found: int
    video_frames: int
    market_summary: str
    top_opportunities: list[dict[str, Any]]
    execution_time_seconds: float


class PortfolioIntelligence(BaseModel):
    portfolio_health: dict[str, Any]
    personalized_signals: list[dict[str, Any]]
    ai_insights: str
    recommended_actions: list[str]
    execution_time_seconds: Optional[float] = None


class CompleteStockAnalysis(BaseModel):
    symbol: str
    technical_analysis: dict[str, Any]
    ai_analysis: str
    combined_signal: Literal["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]
    confidence: float
    execution_time_seconds: Optional[float] = None


class SystemStatusResponse(BaseModel):
    checked_at: str
    agents: list[dict[str, Any]]
    supabase: dict[str, Any]
    last_morning_pipeline_run_at: Optional[str]
    total_signals: int
    total_conversations: int
    system_status: str
    execution_time_seconds: float
