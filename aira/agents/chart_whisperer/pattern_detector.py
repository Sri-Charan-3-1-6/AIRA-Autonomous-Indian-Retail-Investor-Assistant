"""AIRA module: agents/chart_whisperer/pattern_detector.py"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _date_at(df: pd.DataFrame, idx: int) -> str:
    if idx < 0 or idx >= len(df):
        return ""
    value = df.index[idx]
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _build_pattern(df: pd.DataFrame, idx: int, name: str, ptype: str, description: str, reliability: str) -> dict[str, Any]:
    return {
        "pattern_name": name,
        "detected_at_index": int(idx),
        "detected_at_date": _date_at(df, idx),
        "pattern_type": ptype,
        "description": description,
        "reliability": reliability,
    }


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = [str(c).lower() for c in frame.columns]
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in frame.columns:
            frame[col] = 0.0
    return frame


def detect_doji(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    for i in range(len(frame)):
        op = float(frame.iloc[i]["open"])
        cl = float(frame.iloc[i]["close"])
        hi = float(frame.iloc[i]["high"])
        lo = float(frame.iloc[i]["low"])
        candle_range = hi - lo

        # Skip invalid/flat candles where body-to-range comparison is undefined.
        if candle_range <= 0:
            continue

        body_size = abs(op - cl)
        if body_size < (candle_range * 0.0005):
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Doji",
                    "NEUTRAL",
                    "Open and close are almost equal, indicating indecision.",
                    "MEDIUM",
                )
            )
    return patterns


def detect_hammer(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    for i in range(1, len(frame)):
        row = frame.iloc[i]
        body = abs(float(row["close"]) - float(row["open"]))
        lower = min(float(row["open"]), float(row["close"])) - float(row["low"])
        upper = float(row["high"]) - max(float(row["open"]), float(row["close"]))
        prev_close = float(frame.iloc[max(0, i - 3):i]["close"].mean())
        in_downtrend = float(row["close"]) < prev_close
        if body > 0 and lower >= 2 * body and upper <= body * 0.35:
            reliability = "HIGH" if in_downtrend else "MEDIUM"
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Hammer",
                    "BULLISH",
                    "Small body near top with long lower shadow suggests potential reversal.",
                    reliability,
                )
            )
    return patterns


def detect_shooting_star(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    for i in range(1, len(frame)):
        row = frame.iloc[i]
        body = abs(float(row["close"]) - float(row["open"]))
        lower = min(float(row["open"]), float(row["close"])) - float(row["low"])
        upper = float(row["high"]) - max(float(row["open"]), float(row["close"]))
        prev_close = float(frame.iloc[max(0, i - 3):i]["close"].mean())
        in_uptrend = float(row["close"]) > prev_close
        if body > 0 and upper >= 2 * body and lower <= body * 0.35:
            reliability = "HIGH" if in_uptrend else "MEDIUM"
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Shooting Star",
                    "BEARISH",
                    "Small body near bottom with long upper wick indicates rejection at highs.",
                    reliability,
                )
            )
    return patterns


def detect_engulfing(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    for i in range(1, len(frame)):
        prev = frame.iloc[i - 1]
        curr = frame.iloc[i]
        prev_red = float(prev["close"]) < float(prev["open"])
        prev_green = float(prev["close"]) > float(prev["open"])
        curr_green = float(curr["close"]) > float(curr["open"])
        curr_red = float(curr["close"]) < float(curr["open"])

        prev_low_body = min(float(prev["open"]), float(prev["close"]))
        prev_high_body = max(float(prev["open"]), float(prev["close"]))
        curr_low_body = min(float(curr["open"]), float(curr["close"]))
        curr_high_body = max(float(curr["open"]), float(curr["close"]))

        if prev_red and curr_green and curr_low_body <= prev_low_body and curr_high_body >= prev_high_body:
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Bullish Engulfing",
                    "BULLISH",
                    "Current bullish body fully engulfs prior bearish body.",
                    "HIGH",
                )
            )
        elif prev_green and curr_red and curr_low_body <= prev_low_body and curr_high_body >= prev_high_body:
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Bearish Engulfing",
                    "BEARISH",
                    "Current bearish body fully engulfs prior bullish body.",
                    "HIGH",
                )
            )
    return patterns


def detect_morning_star(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    for i in range(2, len(frame)):
        a = frame.iloc[i - 2]
        b = frame.iloc[i - 1]
        c = frame.iloc[i]

        a_body = abs(float(a["close"]) - float(a["open"]))
        b_body = abs(float(b["close"]) - float(b["open"]))
        c_body = abs(float(c["close"]) - float(c["open"]))

        cond1 = float(a["close"]) < float(a["open"]) and a_body > b_body * 1.3
        cond2 = b_body <= a_body * 0.5
        cond3 = float(c["close"]) > float(c["open"]) and c_body >= b_body * 1.5
        cond4 = float(c["close"]) >= ((float(a["open"]) + float(a["close"])) / 2)

        if cond1 and cond2 and cond3 and cond4:
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Morning Star",
                    "BULLISH",
                    "Three-candle bullish reversal pattern after decline.",
                    "HIGH",
                )
            )
    return patterns


def detect_support_resistance(df: pd.DataFrame) -> dict[str, list[float]]:
    frame = _prepare(df).tail(60)
    lows = frame["low"].values
    highs = frame["high"].values

    supports_raw: list[float] = []
    resistances_raw: list[float] = []

    for i in range(2, len(frame) - 2):
        if lows[i] <= lows[i - 1] and lows[i] <= lows[i + 1] and lows[i] <= lows[i - 2] and lows[i] <= lows[i + 2]:
            supports_raw.append(float(lows[i]))
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i + 1] and highs[i] >= highs[i - 2] and highs[i] >= highs[i + 2]:
            resistances_raw.append(float(highs[i]))

    def _cluster(levels: list[float], tolerance: float = 0.015) -> list[float]:
        if not levels:
            return []
        levels_sorted = sorted(levels)
        clustered = [levels_sorted[0]]
        counts = [1]

        for value in levels_sorted[1:]:
            if abs(value - clustered[-1]) / max(clustered[-1], 1e-9) <= tolerance:
                clustered[-1] = (clustered[-1] * counts[-1] + value) / (counts[-1] + 1)
                counts[-1] += 1
            else:
                clustered.append(value)
                counts.append(1)

        filtered = [round(level, 2) for level, count in zip(clustered, counts) if count >= 2]
        return filtered[:5]

    return {
        "support_levels": _cluster(supports_raw),
        "resistance_levels": _cluster(resistances_raw),
    }


def detect_double_top(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    highs = frame["high"].values

    peaks = [i for i in range(2, len(frame) - 2) if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]]
    for i in range(len(peaks) - 1):
        p1 = peaks[i]
        p2 = peaks[i + 1]
        if p2 - p1 < 5:
            continue
        h1 = highs[p1]
        h2 = highs[p2]
        if abs(h1 - h2) / max(h1, h2, 1e-9) <= 0.02:
            patterns.append(
                _build_pattern(
                    frame,
                    p2,
                    "Double Top",
                    "BEARISH",
                    "Two similar peaks indicate potential trend reversal downward.",
                    "MEDIUM",
                )
            )
    return patterns


def detect_double_bottom(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    lows = frame["low"].values

    troughs = [i for i in range(2, len(frame) - 2) if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]]
    for i in range(len(troughs) - 1):
        t1 = troughs[i]
        t2 = troughs[i + 1]
        if t2 - t1 < 5:
            continue
        l1 = lows[t1]
        l2 = lows[t2]
        if abs(l1 - l2) / max(l1, l2, 1e-9) <= 0.02:
            patterns.append(
                _build_pattern(
                    frame,
                    t2,
                    "Double Bottom",
                    "BULLISH",
                    "Two similar troughs suggest buying support and potential upside reversal.",
                    "MEDIUM",
                )
            )
    return patterns


def detect_bull_flag(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    patterns: list[dict[str, Any]] = []
    if len(frame) < 20:
        return patterns

    for i in range(15, len(frame)):
        impulse_start = i - 15
        impulse_end = i - 6
        flag_start = i - 5
        flag_end = i

        impulse = frame.iloc[impulse_start:impulse_end + 1]
        flag = frame.iloc[flag_start:flag_end + 1]
        if impulse.empty or flag.empty:
            continue

        impulse_return = (float(impulse["close"].iloc[-1]) - float(impulse["close"].iloc[0])) / max(
            float(impulse["close"].iloc[0]), 1e-9
        )
        flag_return = (float(flag["close"].iloc[-1]) - float(flag["close"].iloc[0])) / max(
            float(flag["close"].iloc[0]), 1e-9
        )

        if impulse_return > 0.08 and -0.05 <= flag_return <= 0.01:
            patterns.append(
                _build_pattern(
                    frame,
                    i,
                    "Bull Flag",
                    "BULLISH",
                    "Sharp rise followed by mild downward consolidation indicates continuation setup.",
                    "MEDIUM",
                )
            )
    return patterns


def detect_breakout(df: pd.DataFrame) -> list[dict[str, Any]]:
    frame = _prepare(df)
    levels = detect_support_resistance(frame)
    resistances = levels.get("resistance_levels", [])
    patterns: list[dict[str, Any]] = []
    if frame.empty or not resistances:
        return patterns

    latest = frame.iloc[-1]
    close = float(latest["close"])
    volume = float(latest["volume"])
    avg_volume = float(frame["volume"].tail(20).mean()) if len(frame) >= 20 else float(frame["volume"].mean())

    nearest_resistance = max([r for r in resistances if r <= close * 1.2], default=max(resistances))
    if close > nearest_resistance * 1.005 and volume > avg_volume * 1.4:
        patterns.append(
            _build_pattern(
                frame,
                len(frame) - 1,
                "Breakout",
                "BULLISH",
                "Price closed above resistance with above-average volume.",
                "HIGH",
            )
        )
    return patterns


def detect_all_patterns(df: pd.DataFrame) -> dict[str, Any]:
    frame = _prepare(df)

    doji = detect_doji(frame)
    hammer = detect_hammer(frame)
    shooting_star = detect_shooting_star(frame)
    engulfing = detect_engulfing(frame)
    morning_star = detect_morning_star(frame)
    levels = detect_support_resistance(frame)
    double_top = detect_double_top(frame)
    double_bottom = detect_double_bottom(frame)
    bull_flag = detect_bull_flag(frame)
    breakout = detect_breakout(frame)

    all_patterns = doji + hammer + shooting_star + engulfing + morning_star + double_top + double_bottom + bull_flag + breakout

    reliability_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    most_significant = None
    if all_patterns:
        most_significant = sorted(
            all_patterns,
            key=lambda p: (reliability_rank.get(str(p.get("reliability", "LOW")), 0), p.get("detected_at_index", 0)),
            reverse=True,
        )[0]

    return {
        "patterns": all_patterns,
        "support_levels": levels.get("support_levels", []),
        "resistance_levels": levels.get("resistance_levels", []),
        "most_significant_pattern": most_significant,
        "pattern_count": len(all_patterns),
    }
