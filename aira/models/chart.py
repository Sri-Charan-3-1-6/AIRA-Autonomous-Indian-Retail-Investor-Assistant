"""AIRA module: models/chart.py"""

from typing import Any

from pydantic import BaseModel, Field


class TechnicalIndicators(BaseModel):
    rsi_14: float | None = Field(default=None, description="Relative Strength Index (14)")
    macd_line: float | None = Field(default=None, description="MACD line")
    macd_signal: float | None = Field(default=None, description="MACD signal line")
    macd_hist: float | None = Field(default=None, description="MACD histogram")
    bb_upper: float | None = Field(default=None, description="Bollinger upper band")
    bb_middle: float | None = Field(default=None, description="Bollinger middle band")
    bb_lower: float | None = Field(default=None, description="Bollinger lower band")
    sma_20: float | None = Field(default=None, description="Simple moving average 20")
    sma_50: float | None = Field(default=None, description="Simple moving average 50")
    sma_200: float | None = Field(default=None, description="Simple moving average 200")
    ema_9: float | None = Field(default=None, description="Exponential moving average 9")
    ema_21: float | None = Field(default=None, description="Exponential moving average 21")
    atr_14: float | None = Field(default=None, description="Average True Range 14")
    obv: float | None = Field(default=None, description="On Balance Volume")
    stoch_k: float | None = Field(default=None, description="Stochastic K")
    stoch_d: float | None = Field(default=None, description="Stochastic D")
    adx_14: float | None = Field(default=None, description="Average Directional Index 14")


class PatternDetection(BaseModel):
    pattern_name: str = Field(..., description="Detected pattern name")
    detected_at_date: str = Field(..., description="Detection date")
    pattern_type: str = Field(..., description="BULLISH, BEARISH, or NEUTRAL")
    description: str = Field(..., description="Pattern explanation")
    reliability: str = Field(..., description="HIGH, MEDIUM, or LOW")


class BacktestResult(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    pattern_name: str = Field(..., description="Pattern name")
    total_occurrences: int = Field(..., description="Total historical occurrences")
    success_rate: float = Field(..., description="Backtest success rate percentage")
    avg_return_5d: float = Field(..., description="Average 5-day return")
    avg_return_10d: float = Field(..., description="Average 10-day return")
    avg_return_20d: float = Field(..., description="Average 20-day return")
    max_gain: float = Field(..., description="Maximum observed gain")
    max_loss: float = Field(..., description="Maximum observed loss")
    historical_instances: list[dict[str, Any]] = Field(default_factory=list, description="Per-instance return outcomes")
    backtest_summary: str = Field(..., description="Human-readable backtest summary")


class ChartAnalysis(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    period: str = Field(..., description="Analysis period")
    indicators: TechnicalIndicators = Field(..., description="Technical indicator snapshot")
    patterns: list[PatternDetection] = Field(default_factory=list, description="Detected chart patterns")
    backtest_results: list[BacktestResult] = Field(default_factory=list, description="Backtesting results")
    chart_image_base64: str | None = Field(default=None, description="Base64 encoded chart image")
    overall_signal: str = Field(..., description="Overall trading signal")
    confidence: float = Field(..., description="Signal confidence score between 0 and 1")
