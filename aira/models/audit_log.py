"""AIRA module: models/audit_log.py"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="Audit record UUID")
    task_id: str = Field(..., description="Agent task id")
    agent_name: str = Field(..., description="Agent name")
    user_id: str = Field(..., description="User id")
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(..., description="Task status")
    confidence_score: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "3e31f4a2-9808-4294-b672-c14941ce218d",
                "task_id": "3d1eb49d-2af0-431f-86af-1415adf739f2",
                "agent_name": "signal_hunter",
                "user_id": "b6f9c653-39a1-4c0f-b7a2-1213ab4f4a6e",
                "input_data": {"watchlist": ["TCS", "INFY"]},
                "output_data": {"signals": []},
                "status": "completed",
                "confidence_score": 0.72,
                "created_at": "2026-03-26T06:30:00Z",
                "completed_at": "2026-03-26T06:30:03Z",
                "error_message": None,
            }
        }
    }
