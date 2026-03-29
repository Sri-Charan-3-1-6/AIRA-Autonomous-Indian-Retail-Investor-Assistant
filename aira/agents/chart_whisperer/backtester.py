"""AIRA module: agents/chart_whisperer/backtester.py"""

from __future__ import annotations

from typing import Any

import pandas as pd

from agents.chart_whisperer import pattern_detector


def _returns_at(df: pd.DataFrame, idx: int, days: int) -> float | None:
    target = idx + days
    if target >= len(df):
        return None
    entry = float(df.iloc[idx]["close"])
    exit_price = float(df.iloc[target]["close"])
    if entry == 0:
        return None
    return ((exit_price - entry) / entry) * 100


def _direction_for_pattern(pattern_name: str) -> str:
    name = pattern_name.lower()
    bearish_terms = ["bearish", "double top", "shooting star"]
    bullish_terms = ["bullish", "hammer", "morning star", "double bottom", "breakout", "bull flag"]
    if any(term in name for term in bearish_terms):
        return "BEARISH"
    if any(term in name for term in bullish_terms):
        return "BULLISH"
    return "NEUTRAL"


def _pattern_occurrences(df: pd.DataFrame, pattern_name: str) -> list[dict[str, Any]]:
    name = pattern_name.lower().strip()
    detectors = {
        "doji": pattern_detector.detect_doji,
        "hammer": pattern_detector.detect_hammer,
        "shooting star": pattern_detector.detect_shooting_star,
        "bullish engulfing": pattern_detector.detect_engulfing,
        "bearish engulfing": pattern_detector.detect_engulfing,
        "morning star": pattern_detector.detect_morning_star,
        "double top": pattern_detector.detect_double_top,
        "double bottom": pattern_detector.detect_double_bottom,
        "bull flag": pattern_detector.detect_bull_flag,
        "breakout": pattern_detector.detect_breakout,
    }

    if name in {"bullish engulfing", "bearish engulfing"}:
        rows = [p for p in detectors[name](df) if p.get("pattern_name", "").lower() == name]
        return rows

    detector = detectors.get(name)
    if detector:
        rows = detector(df)
        if name in {"doji", "hammer", "shooting star", "morning star", "double top", "double bottom", "bull flag", "breakout"}:
            return [p for p in rows if p.get("pattern_name", "").lower() == name]
        return rows

    all_patterns = pattern_detector.detect_all_patterns(df).get("patterns", [])
    return [p for p in all_patterns if str(p.get("pattern_name", "")).lower() == name]


def backtest_pattern(symbol: str, pattern_name: str, df: pd.DataFrame) -> dict[str, Any]:
    frame = df.copy()
    frame.columns = [str(c).lower() for c in frame.columns]
    occurrences = _pattern_occurrences(frame, pattern_name)

    historical_instances: list[dict[str, Any]] = []
    returns_5: list[float] = []
    returns_10: list[float] = []
    returns_20: list[float] = []

    predicted_direction = _direction_for_pattern(pattern_name)
    successes = 0
    valid_success_samples = 0

    for occ in occurrences:
        idx = int(occ.get("detected_at_index", -1))
        if idx < 0 or idx >= len(frame):
            continue

        r5 = _returns_at(frame, idx, 5)
        r10 = _returns_at(frame, idx, 10)
        r20 = _returns_at(frame, idx, 20)

        if r5 is not None:
            returns_5.append(r5)
        if r10 is not None:
            returns_10.append(r10)
        if r20 is not None:
            returns_20.append(r20)

        if r10 is not None:
            valid_success_samples += 1
            if predicted_direction == "BULLISH" and r10 > 0:
                successes += 1
            elif predicted_direction == "BEARISH" and r10 < 0:
                successes += 1
            elif predicted_direction == "NEUTRAL" and abs(r10) < 2.0:
                successes += 1

        date_value = occ.get("detected_at_date") or (frame.index[idx].strftime("%Y-%m-%d") if hasattr(frame.index[idx], "strftime") else str(frame.index[idx]))
        historical_instances.append(
            {
                "date": date_value,
                "entry_price": float(frame.iloc[idx]["close"]),
                "return_5d": r5,
                "return_10d": r10,
                "return_20d": r20,
            }
        )

    def _avg(values: list[float]) -> float:
        return float(sum(values) / len(values)) if values else 0.0

    all_realized = returns_5 + returns_10 + returns_20
    max_gain = max(all_realized) if all_realized else 0.0
    max_loss = min(all_realized) if all_realized else 0.0
    success_rate = (successes / valid_success_samples * 100.0) if valid_success_samples else 0.0

    summary = (
        f"{pattern_name} appeared {len(historical_instances)} times in last 2 years for {symbol.upper()}. "
        f"Price moved avg {_avg(returns_10):.2f}% in 10 days with {success_rate:.1f}% success rate."
    )

    return {
        "symbol": symbol.upper(),
        "pattern_name": pattern_name,
        "total_occurrences": len(historical_instances),
        "success_rate": float(round(success_rate, 4)),
        "avg_return_5d": float(round(_avg(returns_5), 4)),
        "avg_return_10d": float(round(_avg(returns_10), 4)),
        "avg_return_20d": float(round(_avg(returns_20), 4)),
        "max_gain": float(round(max_gain, 4)),
        "max_loss": float(round(max_loss, 4)),
        "historical_instances": historical_instances,
        "backtest_summary": summary,
    }


def backtest_multiple_patterns(symbol: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    all_detected = pattern_detector.detect_all_patterns(df).get("patterns", [])
    unique_names = sorted({str(p.get("pattern_name", "")).strip() for p in all_detected if p.get("pattern_name")})

    results: list[dict[str, Any]] = []
    for name in unique_names:
        results.append(backtest_pattern(symbol, name, df))

    results.sort(key=lambda x: float(x.get("success_rate", 0.0)), reverse=True)
    return results
