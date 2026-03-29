"""AIRA module: models/conversation.py"""

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime | None = Field(default=None, description="Message timestamp")


class Conversation(BaseModel):
    session_id: str = Field(..., description="Conversation session ID")
    user_id: str = Field(..., description="User ID")
    messages: list[ConversationMessage] = Field(default_factory=list, description="Conversation messages")
    created_at: datetime | None = Field(default=None, description="Conversation creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Conversation update timestamp")


class AskRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    question: str = Field(..., description="Question for MarketGPT")
    session_id: str | None = Field(default=None, description="Optional conversation session ID")
    symbol: str | None = Field(default=None, description="Optional NSE symbol")
    include_portfolio_context: bool = Field(default=True, description="Whether to include portfolio context")


class ScenarioRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    scenario_type: str = Field(..., description="sector_drop, market_crash, interest_rate, or custom")
    scenario_params: dict = Field(default_factory=dict, description="Scenario parameters")


class MarketGPTResponse(BaseModel):
    session_id: str | None = Field(default=None, description="Conversation session ID")
    answer: str = Field(..., description="Formatted response")
    sources: list[str] = Field(default_factory=list, description="Sources used for response")
    disclaimer: str = Field(..., description="Mandatory financial disclaimer")
    query_type: str = Field(..., description="conversational, analysis, scenario, recommendation")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Response confidence")
