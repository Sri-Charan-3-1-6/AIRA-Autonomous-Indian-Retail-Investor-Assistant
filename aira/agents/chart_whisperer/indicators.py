"""AIRA module: agents/chart_whisperer/indicators.py"""

import logging
from typing import Any

import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import ADXIndicator, EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator

logger = logging.getLogger(__name__)


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    frame = df.copy()
    frame.columns = [str(c).lower() for c in frame.columns]

    for col in ["open", "high", "low", "close", "volume"]:
        if col not in frame.columns:
            frame[col] = 0.0

    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    volume = frame["volume"]

    frame["rsi_14"] = RSIIndicator(close=close, window=14).rsi()

    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    frame["macd_line"] = macd.macd()
    frame["macd_signal"] = macd.macd_signal()
    frame["macd_hist"] = macd.macd_diff()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    frame["bb_upper"] = bb.bollinger_hband()
    frame["bb_middle"] = bb.bollinger_mavg()
    frame["bb_lower"] = bb.bollinger_lband()
    frame["bb_bandwidth"] = (frame["bb_upper"] - frame["bb_lower"]) / frame["bb_middle"].replace(0, pd.NA)

    frame["sma_20"] = SMAIndicator(close=close, window=20).sma_indicator()
    frame["sma_50"] = SMAIndicator(close=close, window=50).sma_indicator()
    frame["sma_200"] = SMAIndicator(close=close, window=200).sma_indicator()

    frame["ema_9"] = EMAIndicator(close=close, window=9).ema_indicator()
    frame["ema_21"] = EMAIndicator(close=close, window=21).ema_indicator()

    frame["atr_14"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    frame["obv"] = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    frame["stoch_k"] = stoch.stoch()
    frame["stoch_d"] = stoch.stoch_signal()

    frame["adx_14"] = ADXIndicator(high=high, low=low, close=close, window=14).adx()

    return frame


def interpret_indicators(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "rsi_signal": {"state": "NEUTRAL", "value": 50.0},
            "macd_signal": "NEUTRAL",
            "bb_signal": {"state": "NORMAL", "bandwidth": 0.0},
            "trend": "SIDEWAYS",
            "momentum": "WEAK",
            "overall_signal": "NEUTRAL",
            "confidence": 0.3,
            "summary": "Insufficient data for technical interpretation.",
        }

    row = df.iloc[-1]

    rsi = float(row.get("rsi_14", 50.0) or 50.0)
    if rsi >= 70:
        rsi_state = "OVERBOUGHT"
    elif rsi <= 30:
        rsi_state = "OVERSOLD"
    else:
        rsi_state = "NEUTRAL"

    macd_line = float(row.get("macd_line", 0.0) or 0.0)
    macd_signal_line = float(row.get("macd_signal", 0.0) or 0.0)
    macd_hist = float(row.get("macd_hist", 0.0) or 0.0)
    prev_hist = float(df.iloc[-2].get("macd_hist", 0.0) or 0.0) if len(df) > 1 else 0.0

    if macd_line > macd_signal_line and prev_hist <= 0 < macd_hist:
        macd_state = "BULLISH_CROSSOVER"
    elif macd_line < macd_signal_line and prev_hist >= 0 > macd_hist:
        macd_state = "BEARISH_CROSSOVER"
    elif macd_line > macd_signal_line:
        macd_state = "BULLISH"
    else:
        macd_state = "BEARISH"

    close = float(row.get("close", 0.0) or 0.0)
    bb_upper = float(row.get("bb_upper", close) or close)
    bb_lower = float(row.get("bb_lower", close) or close)
    bb_bandwidth = float(row.get("bb_bandwidth", 0.0) or 0.0)

    if close >= bb_upper * 0.998:
        bb_state = "UPPER_BAND_TOUCH"
    elif close <= bb_lower * 1.002:
        bb_state = "LOWER_BAND_TOUCH"
    elif bb_bandwidth < 0.06:
        bb_state = "SQUEEZE"
    else:
        bb_state = "NORMAL"

    sma20 = float(row.get("sma_20", close) or close)
    sma50 = float(row.get("sma_50", close) or close)
    sma200 = float(row.get("sma_200", close) or close)

    if close > sma20 > sma50 > sma200:
        trend_state = "STRONG_UPTREND"
    elif close > sma20 > sma50:
        trend_state = "UPTREND"
    elif close < sma20 < sma50 < sma200:
        trend_state = "STRONG_DOWNTREND"
    elif close < sma20 < sma50:
        trend_state = "DOWNTREND"
    else:
        trend_state = "SIDEWAYS"

    adx = float(row.get("adx_14", 0.0) or 0.0)
    stoch_k = float(row.get("stoch_k", 50.0) or 50.0)
    if adx >= 30 and (rsi > 60 or rsi < 40):
        momentum_state = "STRONG"
    elif adx >= 20 and (stoch_k > 55 or stoch_k < 45):
        momentum_state = "MODERATE"
    else:
        momentum_state = "WEAK"

    score = 0
    if rsi_state == "OVERSOLD":
        score += 2
    elif rsi_state == "OVERBOUGHT":
        score -= 2

    if "BULLISH" in macd_state:
        score += 2
    elif "BEARISH" in macd_state:
        score -= 2

    if trend_state in {"STRONG_UPTREND", "UPTREND"}:
        score += 2
    elif trend_state in {"STRONG_DOWNTREND", "DOWNTREND"}:
        score -= 2

    if bb_state == "LOWER_BAND_TOUCH":
        score += 1
    elif bb_state == "UPPER_BAND_TOUCH":
        score -= 1

    if momentum_state == "STRONG":
        score += 1 if score >= 0 else -1

    if score >= 4:
        overall = "STRONG_BUY"
    elif score >= 2:
        overall = "BUY"
    elif score <= -4:
        overall = "STRONG_SELL"
    elif score <= -2:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    confidence = min(1.0, max(0.0, 0.45 + abs(score) * 0.1 + (0.1 if adx >= 25 else 0.0)))

    summary = (
        f"RSI is {rsi:.1f} ({rsi_state}), MACD is {macd_state.lower().replace('_', ' ')}, "
        f"and trend is {trend_state.lower().replace('_', ' ')}, giving an overall {overall.lower().replace('_', ' ')} outlook."
    )

    return {
        "rsi_signal": {"state": rsi_state, "value": rsi},
        "macd_signal": macd_state,
        "bb_signal": {"state": bb_state, "bandwidth": bb_bandwidth},
        "trend": trend_state,
        "momentum": momentum_state,
        "overall_signal": overall,
        "confidence": float(round(confidence, 4)),
        "summary": summary,
    }
