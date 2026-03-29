"""AIRA module: agents/video_studio/script_generator.py"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "-"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_tone(value: str) -> str:
    tone = (value or "NEUTRAL").strip().upper()
    if tone not in {"BULLISH", "BEARISH", "NEUTRAL"}:
        return "NEUTRAL"
    return tone


def _fallback_market_script(market_data: dict[str, Any]) -> dict[str, Any]:
    nifty = _safe_float(market_data.get("nifty_change_pct"), 0.0)
    fii_net = _safe_float(market_data.get("fii_net"), 0.0)
    dii_net = _safe_float(market_data.get("dii_net"), 0.0)
    top_signals = market_data.get("top_signals") or []
    picks = ", ".join([str(s.get("symbol") or "N/A") for s in top_signals[:3]]) or "select frontline names"

    if nifty > 0.3:
        tone = "BULLISH"
    elif nifty < -0.3:
        tone = "BEARISH"
    else:
        tone = "NEUTRAL"

    return {
        "intro": "Namaste and welcome to your AIRA market wrap. Today's tone is balanced with selective opportunities.",
        "market_overview": (
            f"Nifty moved {nifty:+.2f}% in the latest session. "
            f"FII net flow stood at {fii_net:+.0f} crore while DII net flow was {dii_net:+.0f} crore. "
            "Institutional positioning suggests stock-specific action rather than a broad one-way market."
        ),
        "top_opportunities": (
            f"Our top monitored opportunities today include {picks}. "
            "These names are showing relatively stronger setup quality and follow-through potential. "
            "Use staggered entries and keep position sizing disciplined."
        ),
        "sector_watch": (
            "Banking and IT are currently driving headline momentum while defensives remain mixed. "
            "Watch crude, global yields, and currency moves for next-session sector rotation cues."
        ),
        "closing": "For retail investors, stick to your plan, avoid overtrading, and prioritize risk management.",
        "duration_seconds": 75,
        "tone": tone,
    }


def _fallback_stock_script(symbol: str, analysis: dict[str, Any]) -> dict[str, Any]:
    summary = analysis.get("summary") or {}
    current_price = _safe_float(summary.get("current_price"), 0.0)
    signal = str(analysis.get("overall_signal") or "NEUTRAL")
    confidence = _safe_float(analysis.get("confidence"), 0.0)

    return {
        "intro": f"Here is your quick AIRA view on {symbol}.",
        "market_overview": (
            f"{symbol} is currently around {current_price:.2f}. "
            f"The technical signal is {signal}. "
            "Momentum and structure indicate selective participation."
        ),
        "top_opportunities": (
            f"The setup confidence is {confidence:.2f} on our scale. "
            "Focus on price behavior near key support and resistance levels. "
            "Prefer disciplined entries rather than chasing sharp candles."
        ),
        "sector_watch": "Track sector peers and index direction because relative strength often drives near-term moves.",
        "closing": "Retail investors should prioritize risk limits and avoid oversized positions in single names.",
        "duration_seconds": 38,
        "tone": "NEUTRAL",
        "stock_name": str(analysis.get("company_name") or symbol),
        "current_price": current_price,
        "signal": signal,
    }


def _coerce_script(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    return {
        "intro": str(payload.get("intro") or fallback["intro"]),
        "market_overview": str(payload.get("market_overview") or fallback["market_overview"]),
        "top_opportunities": str(payload.get("top_opportunities") or fallback["top_opportunities"]),
        "sector_watch": str(payload.get("sector_watch") or fallback["sector_watch"]),
        "closing": str(payload.get("closing") or fallback["closing"]),
        "duration_seconds": int(_safe_float(payload.get("duration_seconds"), fallback["duration_seconds"])),
        "tone": _normalize_tone(str(payload.get("tone") or fallback["tone"])),
        **{k: v for k, v in payload.items() if k not in {"intro", "market_overview", "top_opportunities", "sector_watch", "closing", "duration_seconds", "tone"}},
    }


async def generate_market_script(market_data: dict[str, Any], groq_client, use_groq: bool = True) -> dict[str, Any]:
    fallback = _fallback_market_script(market_data)
    schema = {
        "type": "object",
        "required": [
            "intro",
            "market_overview",
            "top_opportunities",
            "sector_watch",
            "closing",
            "duration_seconds",
            "tone",
        ],
        "properties": {
            "intro": {"type": "string"},
            "market_overview": {"type": "string"},
            "top_opportunities": {"type": "string"},
            "sector_watch": {"type": "string"},
            "closing": {"type": "string"},
            "duration_seconds": {"type": "number"},
            "tone": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
        },
    }

    prompt = (
        "Create a 60 to 90 second broadcast-style Indian market summary for retail investors. "
        "Return ONLY JSON with exact keys: intro, market_overview, top_opportunities, sector_watch, closing, duration_seconds, tone. "
        "Use exactly these sections and sentence counts: INTRO 2 sentences, MARKET_OVERVIEW 3 sentences, "
        "TOP_OPPORTUNITIES 3 sentences covering top 2 to 3 signals with opportunity scores, "
        "SECTOR_WATCH 2 sentences, CLOSING 1 sentence actionable takeaway. "
        "Tone must be one of BULLISH, BEARISH, NEUTRAL.\n\n"
        f"Market Data: {json.dumps(market_data, ensure_ascii=True)}"
    )

    if not use_groq:
        fallback["generated_at"] = datetime.utcnow().isoformat()
        return fallback

    try:
        logger.info("Generating market video script via Groq")
        generated = await groq_client.generate_json(prompt, schema)
        script = _coerce_script(generated, fallback)
        script["generated_at"] = datetime.utcnow().isoformat()
        return script
    except Exception as exc:
        logger.exception("Groq market script generation failed error=%s", exc)
        fallback["generated_at"] = datetime.utcnow().isoformat()
        return fallback


async def generate_stock_script(symbol: str, analysis: dict[str, Any], groq_client, use_groq: bool = True) -> dict[str, Any]:
    fallback = _fallback_stock_script(symbol, analysis)
    schema = {
        "type": "object",
        "required": [
            "intro",
            "market_overview",
            "top_opportunities",
            "sector_watch",
            "closing",
            "duration_seconds",
            "tone",
            "stock_name",
            "current_price",
            "signal",
        ],
        "properties": {
            "intro": {"type": "string"},
            "market_overview": {"type": "string"},
            "top_opportunities": {"type": "string"},
            "sector_watch": {"type": "string"},
            "closing": {"type": "string"},
            "duration_seconds": {"type": "number"},
            "tone": {"type": "string", "enum": ["BULLISH", "BEARISH", "NEUTRAL"]},
            "stock_name": {"type": "string"},
            "current_price": {"type": "number"},
            "signal": {"type": "string"},
        },
    }

    prompt = (
        f"Create a 30 to 45 second broadcast-style script for stock {symbol} for Indian retail investors. "
        "Return ONLY JSON with exact keys: intro, market_overview, top_opportunities, sector_watch, closing, "
        "duration_seconds, tone, stock_name, current_price, signal. "
        "Section sentence counts: INTRO 2, MARKET_OVERVIEW 3, TOP_OPPORTUNITIES 3, SECTOR_WATCH 2, CLOSING 1.\n\n"
        f"Stock Analysis Data: {json.dumps(analysis, ensure_ascii=True)}"
    )

    if not use_groq:
        fallback["generated_at"] = datetime.utcnow().isoformat()
        return fallback

    try:
        logger.info("Generating stock video script via Groq symbol=%s", symbol)
        generated = await groq_client.generate_json(prompt, schema)
        script = _coerce_script(generated, fallback)
        script["stock_name"] = str(generated.get("stock_name") or fallback["stock_name"])
        script["current_price"] = _safe_float(generated.get("current_price"), fallback["current_price"])
        script["signal"] = str(generated.get("signal") or fallback["signal"])
        script["generated_at"] = datetime.utcnow().isoformat()
        return script
    except Exception as exc:
        logger.exception("Groq stock script generation failed symbol=%s error=%s", symbol, exc)
        fallback["generated_at"] = datetime.utcnow().isoformat()
        return fallback
