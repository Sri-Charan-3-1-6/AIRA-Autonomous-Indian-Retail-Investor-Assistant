"""AIRA module: models/portfolio.py"""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class Portfolio(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="Portfolio UUID")
    user_id: str = Field(..., description="Owner user UUID")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw portfolio payload")
    xirr: float = Field(default=0.0, description="Computed XIRR")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dc5a31ff-2a25-45ce-9ffd-1bde5da4be27",
                "user_id": "b6f9c653-39a1-4c0f-b7a2-1213ab4f4a6e",
                "raw_data": {"holdings": [{"symbol": "TCS", "quantity": 10}]},
                "xirr": 12.4,
                "created_at": "2026-03-26T06:30:00Z",
            }
        }
    }


class PortfolioHistoryItem(BaseModel):
    id: str = Field(..., description="Portfolio row id")
    created_at: datetime = Field(..., description="Analysis timestamp")
    xirr: float = Field(..., description="Portfolio XIRR")
    overall_score: int | None = Field(default=None, description="AI health score")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dc5a31ff-2a25-45ce-9ffd-1bde5da4be27",
                "created_at": "2026-03-27T09:40:00Z",
                "xirr": 0.146,
                "overall_score": 78,
            }
        }
    }


class PortfolioUploadResponse(BaseModel):
    overall_score: int = Field(..., ge=0, le=100)
    xirr_results: Dict[str, Any] = Field(default_factory=dict)
    overlap_analysis: Dict[str, Any] = Field(default_factory=dict)
    expense_analysis: Dict[str, Any] = Field(default_factory=dict)
    benchmark_analysis: Dict[str, Any] = Field(default_factory=dict)
    tax_analysis: Dict[str, Any] = Field(default_factory=dict)
    rebalancing_plan: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "overall_score": 74,
                "xirr_results": {"overall_xirr": 0.139},
                "overlap_analysis": {"diversification_score": 62.4},
                "expense_analysis": {"annual_expense_cost": 8420.12},
                "benchmark_analysis": {"alpha": -0.008},
                "tax_analysis": {"estimated_tax": 14250.0},
                "rebalancing_plan": {"summary": "Portfolio is stable but concentrated."},
            }
        }
    }
