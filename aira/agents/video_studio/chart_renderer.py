"""AIRA module: agents/video_studio/chart_renderer.py"""

import base64
import io
import logging
import textwrap
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import patches
import numpy as np

logger = logging.getLogger(__name__)

BG_PRIMARY = "#1a1a2e"
BG_SECONDARY = "#16213e"
TXT = "#ffffff"
POS = "#00ff88"
NEG = "#ff4444"


def _fig_to_base64(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=100, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("ascii")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "-"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def render_market_overview_frame(data: dict[str, Any]) -> str:
    nifty_change = _safe_float(data.get("nifty_change_pct"), 0.0)
    fii_net = _safe_float(data.get("fii_net"), 0.0)
    dii_net = _safe_float(data.get("dii_net"), 0.0)
    sentiment = str(data.get("sentiment") or ("BULLISH" if nifty_change > 0 else "BEARISH" if nifty_change < 0 else "NEUTRAL"))

    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG_PRIMARY)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], width_ratios=[1.5, 1.0])

    ax_title = fig.add_subplot(gs[0, 0])
    ax_title.set_facecolor(BG_PRIMARY)
    ax_title.axis("off")
    ax_title.text(0.01, 0.82, "AIRA MARKET DASHBOARD", fontsize=28, fontweight="bold", color=TXT)
    ax_title.text(0.01, 0.52, "NIFTY 50", fontsize=16, color=TXT)
    ax_title.text(0.01, 0.16, f"{nifty_change:+.2f}%", fontsize=58, fontweight="bold", color=POS if nifty_change >= 0 else NEG)

    ax_sent = fig.add_subplot(gs[0, 1])
    ax_sent.set_facecolor(BG_SECONDARY)
    ax_sent.axis("off")
    color = POS if sentiment == "BULLISH" else NEG if sentiment == "BEARISH" else TXT
    ax_sent.text(0.5, 0.62, "SENTIMENT", ha="center", va="center", color=TXT, fontsize=15)
    ax_sent.text(0.5, 0.38, sentiment, ha="center", va="center", color=color, fontsize=26, fontweight="bold")

    ax_bar = fig.add_subplot(gs[1, :])
    ax_bar.set_facecolor(BG_PRIMARY)
    vals = [fii_net, dii_net]
    labels = ["FII NET FLOW", "DII NET FLOW"]
    colors = [POS if fii_net >= 0 else NEG, POS if dii_net >= 0 else NEG]
    bars = ax_bar.bar(labels, vals, color=colors, width=0.55)
    ax_bar.axhline(0, color="#888888", linewidth=1.2)
    ax_bar.tick_params(axis="x", colors=TXT, labelsize=12)
    ax_bar.tick_params(axis="y", colors=TXT, labelsize=11)
    ax_bar.set_title("Institutional Flows (Crore)", color=TXT, fontsize=16, pad=12)
    for spine in ax_bar.spines.values():
        spine.set_color("#404060")
    for bar, value in zip(bars, vals):
        y = bar.get_height()
        va = "bottom" if y >= 0 else "top"
        ax_bar.text(bar.get_x() + bar.get_width() / 2, y, f"{value:+.0f}", ha="center", va=va, color=TXT, fontsize=11)

    fig.subplots_adjust(left=0.03, right=0.98, top=0.96, bottom=0.07, hspace=0.32)
    return _fig_to_base64(fig)


def render_signal_frame(signal: dict[str, Any]) -> str:
    symbol = str(signal.get("symbol") or "N/A")
    score = max(0.0, min(100.0, _safe_float(signal.get("opportunity_score"), 0.0)))
    category = str(signal.get("category") or ("STRONG BUY" if score >= 85 else "BUY" if score >= 70 else "WATCH"))
    explanation = str(signal.get("explanation") or "Signal explanation unavailable.")
    technical = signal.get("technical_indicators") or signal.get("data", {}).get("technical_indicators") or {}

    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG_PRIMARY)

    ax_main = fig.add_axes([0, 0, 1, 1])
    ax_main.set_facecolor(BG_PRIMARY)
    ax_main.axis("off")
    ax_main.text(0.5, 0.88, symbol, ha="center", va="center", fontsize=52, color=TXT, fontweight="bold")
    ax_main.text(0.5, 0.8, category, ha="center", va="center", fontsize=22, color=POS if category in {"STRONG BUY", "BUY"} else TXT)

    ax_gauge = fig.add_axes([0.08, 0.36, 0.28, 0.32])
    ax_gauge.set_facecolor(BG_PRIMARY)
    ax_gauge.axis("off")
    ring_bg = patches.Wedge((0.5, 0.5), 0.45, 0, 360, width=0.12, color="#303050")
    ring_fg = patches.Wedge((0.5, 0.5), 0.45, 90, 90 - (360 * score / 100.0), width=0.12, color=POS if score >= 70 else NEG)
    ax_gauge.add_patch(ring_bg)
    ax_gauge.add_patch(ring_fg)
    ax_gauge.text(0.5, 0.52, f"{score:.0f}", ha="center", va="center", fontsize=30, color=TXT, fontweight="bold")
    ax_gauge.text(0.5, 0.28, "SCORE", ha="center", va="center", fontsize=12, color=TXT)

    ax_text = fig.add_axes([0.4, 0.36, 0.54, 0.36])
    ax_text.set_facecolor(BG_SECONDARY)
    ax_text.axis("off")
    wrapped = "\n".join(textwrap.wrap(explanation, width=58))
    ax_text.text(0.03, 0.92, "WHY THIS SIGNAL", color=TXT, fontsize=15, fontweight="bold", va="top")
    ax_text.text(0.03, 0.82, wrapped, color=TXT, fontsize=13, va="top")

    ax_ind = fig.add_axes([0.08, 0.08, 0.86, 0.2])
    ax_ind.set_facecolor(BG_PRIMARY)
    ax_ind.axis("off")
    ax_ind.text(0.01, 0.88, "TECHNICAL SNAPSHOT", color=TXT, fontsize=14, fontweight="bold")
    if isinstance(technical, dict) and technical:
        pairs = list(technical.items())[:5]
        for idx, (k, v) in enumerate(pairs):
            value_text = f"{v:.2f}" if isinstance(v, (int, float)) else str(v)
            ax_ind.text(0.01 + idx * 0.19, 0.45, f"{str(k).upper()}: {value_text}", color=TXT, fontsize=11)
    else:
        ax_ind.text(0.01, 0.45, "Indicators not available for this signal.", color=TXT, fontsize=11)

    return _fig_to_base64(fig)


def render_sector_frame(sector_data: dict[str, Any]) -> str:
    sectors = sector_data.get("sectors") if isinstance(sector_data, dict) else None
    if not isinstance(sectors, dict) or not sectors:
        sectors = {
            "BANKING": 1.1,
            "IT": 0.6,
            "AUTO": 0.3,
            "PHARMA": -0.4,
            "METALS": -0.7,
        }

    labels = [str(k).upper() for k in sectors.keys()]
    values = [_safe_float(v) for v in sectors.values()]
    colors = [POS if v >= 0 else NEG for v in values]

    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100, facecolor=BG_PRIMARY)
    ax.set_facecolor(BG_PRIMARY)
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color=TXT, fontsize=12)
    ax.tick_params(axis="x", colors=TXT)
    ax.axvline(0, color="#888888", linewidth=1.2)
    ax.set_title("Sector Performance Snapshot (%)", color=TXT, fontsize=22, pad=14)
    for spine in ax.spines.values():
        spine.set_color("#404060")
    for bar, value in zip(bars, values):
        x = bar.get_width()
        offset = 0.05 if x >= 0 else -0.05
        align = "left" if x >= 0 else "right"
        ax.text(x + offset, bar.get_y() + bar.get_height() / 2, f"{value:+.2f}%", va="center", ha=align, color=TXT, fontsize=11)

    fig.subplots_adjust(left=0.15, right=0.96, top=0.9, bottom=0.1)
    return _fig_to_base64(fig)


def render_title_frame(title: str, subtitle: str, date: str) -> str:
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)

    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))
    ax.imshow(gradient, aspect="auto", extent=[0, 1, 0, 1], cmap=matplotlib.colors.LinearSegmentedColormap.from_list("aira", [BG_PRIMARY, BG_SECONDARY]))
    ax.axis("off")
    ax.text(0.5, 0.78, "AIRA", ha="center", va="center", fontsize=62, color=TXT, fontweight="bold")
    ax.text(0.5, 0.56, title, ha="center", va="center", fontsize=30, color=TXT, fontweight="bold")
    ax.text(0.5, 0.44, subtitle, ha="center", va="center", fontsize=18, color=TXT)
    ax.text(0.5, 0.2, date or datetime.utcnow().strftime("%d %b %Y"), ha="center", va="center", fontsize=16, color=TXT)

    return _fig_to_base64(fig)


def render_closing_frame(message: str) -> str:
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100, facecolor=BG_PRIMARY)
    ax.set_facecolor(BG_PRIMARY)
    ax.axis("off")
    wrapped = "\n".join(textwrap.wrap(message or "Stay disciplined and invest with a plan.", width=52))
    ax.text(0.5, 0.7, "AIRA TAKEAWAY", ha="center", va="center", fontsize=34, color=TXT, fontweight="bold")
    ax.text(0.5, 0.46, wrapped, ha="center", va="center", fontsize=20, color=TXT)
    ax.text(0.5, 0.18, "aira.ai  |  Data-driven, investor-friendly insights", ha="center", va="center", fontsize=14, color=TXT)
    return _fig_to_base64(fig)


def render_all_frames(script: dict[str, Any], market_data: dict[str, Any]) -> list[dict[str, Any]]:
    logger.info("Rendering full video frame set")
    top_signals = market_data.get("top_signals") or []
    date = str(market_data.get("date") or datetime.utcnow().strftime("%d %b %Y"))
    sector_map = market_data.get("sector_performance") or {
        "BANKING": 0.9,
        "IT": 0.4,
        "PHARMA": -0.3,
        "AUTO": 0.2,
        "METALS": -0.5,
    }

    frames: list[dict[str, Any]] = [
        {
            "frame_type": "title",
            "image_base64": render_title_frame(
                title="Daily Market Wrap",
                subtitle=f"Tone: {str(script.get('tone') or 'NEUTRAL')}",
                date=date,
            ),
            "duration_seconds": 2.5,
            "caption": str(script.get("intro") or "Welcome to AIRA market wrap."),
        },
        {
            "frame_type": "market_overview",
            "image_base64": render_market_overview_frame(
                {
                    "nifty_change_pct": market_data.get("nifty_change_pct", 0.0),
                    "fii_net": market_data.get("fii_net", 0.0),
                    "dii_net": market_data.get("dii_net", 0.0),
                    "sentiment": script.get("tone", "NEUTRAL"),
                }
            ),
            "duration_seconds": 4.0,
            "caption": str(script.get("market_overview") or "Market overview."),
        },
    ]

    for signal in top_signals[:2]:
        frames.append(
            {
                "frame_type": "signal",
                "image_base64": render_signal_frame(signal),
                "duration_seconds": 3.8,
                "caption": str(script.get("top_opportunities") or "Top opportunity."),
            }
        )

    frames.append(
        {
            "frame_type": "sector",
            "image_base64": render_sector_frame({"sectors": sector_map}),
            "duration_seconds": 3.0,
            "caption": str(script.get("sector_watch") or "Sector watch."),
        }
    )

    frames.append(
        {
            "frame_type": "closing",
            "image_base64": render_closing_frame(str(script.get("closing") or "Stay disciplined.")),
            "duration_seconds": 2.8,
            "caption": str(script.get("closing") or "Stay disciplined."),
        }
    )

    return frames
