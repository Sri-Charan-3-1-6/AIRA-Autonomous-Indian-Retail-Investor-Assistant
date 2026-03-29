"""AIRA module: models/audit.py"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    id: str | None = None
    task_id: str
    agent_name: str
    user_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    status: str
    confidence_score: float = 0.0
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None


class AuditStats(BaseModel):
    total_decisions: int = 0
    decisions_by_agent: dict[str, int] = Field(default_factory=dict)
    avg_confidence_by_agent: dict[str, float] = Field(default_factory=dict)
    success_rate: float = 0.0
    total_failed: int = 0
    last_24h_count: int = 0


class ComplianceReport(BaseModel):
    total_ai_decisions: int = 0
    confidence_above_0_7_percentage: float = 0.0
    data_driven_not_direct_advice: bool = True
    marketgpt_disclaimer_present_in_all: bool = True
    marketgpt_total_responses: int = 0
    marketgpt_responses_with_disclaimer: int = 0
    generated_at: datetime
