"""AIRA module: models/signal.py"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketSignal(BaseModel):
    id: str | None = Field(default=None, description="Signal UUID")
    symbol: str = Field(..., description="NSE stock symbol")
    company: str = Field(..., description="Company name")
    signal_type: str = Field(..., description="Signal source/type such as composite or bulk_deal")
    opportunity_score: float = Field(..., description="Opportunity score from 0 to 100")
    category: str = Field(..., description="Signal category like STRONG_BUY, BUY, WATCH, NEUTRAL, AVOID")
    explanation: str = Field(..., description="Human-readable scoring explanation")
    data: dict[str, Any] = Field(default_factory=dict, description="Raw signal payload and supporting analysis")
    created_at: datetime | None = Field(default=None, description="Signal creation timestamp")


class SignalAlert(BaseModel):
    signal_id: str = Field(..., description="Related market signal UUID")
    user_id: str = Field(..., description="Target user UUID")
    is_read: bool = Field(default=False, description="Whether the alert has been read by the user")
    created_at: datetime | None = Field(default=None, description="Alert creation timestamp")


class FIIDIIData(BaseModel):
    date: str = Field(..., description="Trade date for the data snapshot")
    fii_buy: float = Field(..., description="FII buy value")
    fii_sell: float = Field(..., description="FII sell value")
    fii_net: float = Field(..., description="Net FII flow")
    dii_buy: float = Field(..., description="DII buy value")
    dii_sell: float = Field(..., description="DII sell value")
    dii_net: float = Field(..., description="Net DII flow")
    total_net: float = Field(..., description="Combined net flow of FII and DII")
