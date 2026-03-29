"""AIRA module: agents/chart_whisperer/chart_generator.py"""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd

matplotlib.use("Agg")

logger = logging.getLogger(__name__)


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = [str(c).lower() for c in frame.columns]

    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.set_index("date")

    if not isinstance(frame.index, pd.DatetimeIndex):
        frame.index = pd.to_datetime(frame.index, errors="coerce")

    frame = frame.sort_index()
    frame = frame.dropna(subset=["open", "high", "low", "close"], how="any")

    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    for src, dst in rename_map.items():
        if src in frame.columns:
            frame[dst] = frame[src]

    if "Volume" not in frame.columns:
        frame["Volume"] = 0.0

    return frame


def _to_base64(fig: plt.Figure) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=140, facecolor=fig.get_facecolor())
    buffer.seek(0)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    plt.close(fig)
    return encoded


def generate_candlestick_chart(df: pd.DataFrame, symbol: str, patterns: list[dict[str, Any]], indicators: dict[str, Any]) -> str:
    try:
        frame = _prepare(df)
        if frame.empty:
            raise ValueError("No data available for candlestick chart")

        addplots = []
        for ma_col, color in [("sma_20", "#ffcc00"), ("sma_50", "#00d4ff"), ("sma_200", "#ff6b6b")]:
            if ma_col in frame.columns:
                addplots.append(mpf.make_addplot(frame[ma_col], panel=0, color=color, width=1.0))

        if "rsi_14" in frame.columns:
            addplots.append(mpf.make_addplot(frame["rsi_14"], panel=1, color="#c792ea", ylabel="RSI"))
        if "macd_line" in frame.columns:
            addplots.append(mpf.make_addplot(frame["macd_line"], panel=2, color="#4dd0e1", ylabel="MACD"))
        if "macd_signal" in frame.columns:
            addplots.append(mpf.make_addplot(frame["macd_signal"], panel=2, color="#ffab40"))
        if "macd_hist" in frame.columns:
            addplots.append(
                mpf.make_addplot(
                    frame["macd_hist"],
                    panel=2,
                    type="bar",
                    color=np.where(frame["macd_hist"] >= 0, "#66bb6a", "#ef5350"),
                    alpha=0.6,
                )
            )

        bull_marks = pd.Series(np.nan, index=frame.index)
        bear_marks = pd.Series(np.nan, index=frame.index)

        for p in patterns or []:
            idx = int(p.get("detected_at_index", -1))
            if idx < 0 or idx >= len(frame):
                continue
            ptype = str(p.get("pattern_type", "NEUTRAL")).upper()
            ts = frame.index[idx]
            if ptype == "BULLISH":
                bull_marks.loc[ts] = frame.iloc[idx]["Low"] * 0.985
            elif ptype == "BEARISH":
                bear_marks.loc[ts] = frame.iloc[idx]["High"] * 1.015

        if bull_marks.notna().any():
            addplots.append(mpf.make_addplot(bull_marks, panel=0, type="scatter", marker="^", markersize=70, color="#00e676"))
        if bear_marks.notna().any():
            addplots.append(mpf.make_addplot(bear_marks, panel=0, type="scatter", marker="v", markersize=70, color="#ff5252"))

        support_levels = indicators.get("support_levels", []) if isinstance(indicators, dict) else []
        resistance_levels = indicators.get("resistance_levels", []) if isinstance(indicators, dict) else []
        hlines = []
        hline_colors = []
        for value in support_levels:
            hlines.append(float(value))
            hline_colors.append("#00c853")
        for value in resistance_levels:
            hlines.append(float(value))
            hline_colors.append("#ff1744")

        last_close = float(frame["Close"].iloc[-1])
        prev_close = float(frame["Close"].iloc[-2]) if len(frame) > 1 else last_close
        change_pct = ((last_close - prev_close) / prev_close * 100.0) if prev_close else 0.0

        fig, axes = mpf.plot(
            frame,
            type="candle",
            style="nightclouds",
            volume=True,
            addplot=addplots if addplots else None,
            panel_ratios=(7, 2, 2),
            figratio=(18, 10),
            figscale=1.2,
            returnfig=True,
            hlines=dict(hlines=hlines, colors=hline_colors, linestyle="--", alpha=0.5) if hlines else None,
        )

        title = f"{symbol.upper()} | Price {last_close:.2f} | Change {change_pct:+.2f}%"
        fig.suptitle(title, color="white", fontsize=12)

        max_labels = 12
        labels_added = 0
        for p in patterns or []:
            if labels_added >= max_labels:
                break
            idx = int(p.get("detected_at_index", -1))
            if idx < 0 or idx >= len(frame):
                continue
            y = frame.iloc[idx]["High"] * 1.02
            axes[0].annotate(
                str(p.get("pattern_name", "Pattern")),
                xy=(frame.index[idx], y),
                xytext=(0, 8),
                textcoords="offset points",
                color="#e0e0e0",
                fontsize=7,
                ha="center",
            )
            labels_added += 1

        return _to_base64(fig)
    except Exception as exc:
        logger.warning("Candlestick chart generation failed for %s: %s", symbol, exc)
        fig = plt.figure(figsize=(10, 4), facecolor="#0e1117")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#0e1117")
        ax.plot([], [])
        ax.set_title(f"{symbol.upper()} chart unavailable", color="white")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")
        return _to_base64(fig)


def generate_indicator_chart(df: pd.DataFrame, symbol: str) -> str:
    try:
        frame = _prepare(df)
        if frame.empty:
            raise ValueError("No data available for indicator chart")

        addplots = []
        for col, color in [("bb_upper", "#f48fb1"), ("bb_middle", "#90caf9"), ("bb_lower", "#f48fb1")]:
            if col in frame.columns:
                addplots.append(mpf.make_addplot(frame[col], panel=0, color=color, width=1.0))

        fig, _ = mpf.plot(
            frame,
            type="line",
            style="nightclouds",
            volume=True,
            addplot=addplots if addplots else None,
            figratio=(16, 8),
            returnfig=True,
        )
        fig.suptitle(f"{symbol.upper()} Bollinger + Volume", color="white")
        return _to_base64(fig)
    except Exception as exc:
        logger.warning("Indicator chart generation failed for %s: %s", symbol, exc)
        fig = plt.figure(figsize=(8, 4))
        fig.text(0.1, 0.5, "Indicator chart unavailable", color="black")
        return _to_base64(fig)


def generate_pattern_highlight_chart(df: pd.DataFrame, symbol: str, pattern_name: str, instance_index: int) -> str:
    try:
        frame = _prepare(df)
        if frame.empty:
            raise ValueError("No data available for pattern highlight chart")

        idx = max(0, int(instance_index))
        if idx >= len(frame):
            idx = len(frame) - 1

        start = max(0, idx - 10)
        end = min(len(frame), idx + 11)
        window = frame.iloc[start:end].copy()
        local_idx = idx - start

        mark = pd.Series(np.nan, index=window.index)
        if 0 <= local_idx < len(window):
            mark.iloc[local_idx] = float(window.iloc[local_idx]["High"]) * 1.02

        addplots = [mpf.make_addplot(mark, panel=0, type="scatter", marker="*", markersize=120, color="#ffd54f")]
        fig, axes = mpf.plot(
            window,
            type="candle",
            style="nightclouds",
            volume=True,
            addplot=addplots,
            returnfig=True,
            figratio=(14, 8),
        )

        if 0 <= local_idx < len(window):
            axes[0].annotate(
                pattern_name,
                xy=(window.index[local_idx], float(window.iloc[local_idx]["High"]) * 1.02),
                xytext=(0, 10),
                textcoords="offset points",
                color="#ffd54f",
                fontsize=9,
                ha="center",
            )

        fig.suptitle(f"{symbol.upper()} {pattern_name} Highlight", color="white")
        return _to_base64(fig)
    except Exception as exc:
        logger.warning("Pattern highlight chart generation failed for %s: %s", symbol, exc)
        fig = plt.figure(figsize=(8, 4))
        fig.text(0.1, 0.5, "Pattern highlight unavailable", color="black")
        return _to_base64(fig)
