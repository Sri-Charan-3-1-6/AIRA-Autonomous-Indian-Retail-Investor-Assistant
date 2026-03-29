"""AIRA module: agents/signal_hunter/fii_dii_tracker.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
NSE_BASE_URL = "https://www.nseindia.com/"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "-"):
            return default
        text = str(value).replace(",", "").replace("Rs", "").strip()
        return float(text)
    except (TypeError, ValueError):
        return default


def _sample_history() -> list[dict[str, Any]]:
    return [
        {"date": "2026-03-20", "fii_buy": 13250.0, "fii_sell": 11800.0, "fii_net": 1450.0, "dii_buy": 9800.0, "dii_sell": 10120.0, "dii_net": -320.0},
        {"date": "2026-03-21", "fii_buy": 12840.0, "fii_sell": 11990.0, "fii_net": 850.0, "dii_buy": 10010.0, "dii_sell": 9980.0, "dii_net": 30.0},
        {"date": "2026-03-24", "fii_buy": 13720.0, "fii_sell": 12110.0, "fii_net": 1610.0, "dii_buy": 10200.0, "dii_sell": 10490.0, "dii_net": -290.0},
        {"date": "2026-03-25", "fii_buy": 14030.0, "fii_sell": 12360.0, "fii_net": 1670.0, "dii_buy": 10820.0, "dii_sell": 11040.0, "dii_net": -220.0},
        {"date": "2026-03-26", "fii_buy": 14510.0, "fii_sell": 12680.0, "fii_net": 1830.0, "dii_buy": 11240.0, "dii_sell": 11560.0, "dii_net": -320.0},
    ]


async def _fetch_fii_dii_history() -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(headers=REQUEST_HEADERS, timeout=20.0, follow_redirects=True) as client:
            logger.info("Priming NSE session for FII/DII")
            await client.get(NSE_BASE_URL)
            await asyncio.sleep(2)

            logger.info("Fetching FII/DII data from NSE")
            response = await client.get(FII_DII_URL)
            response.raise_for_status()
            await asyncio.sleep(2)

            payload = response.json()
            rows = payload.get("data") if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                rows = []

            parsed: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                fii_buy = _to_float(row.get("buyValueFii") or row.get("fiiBuyValue") or row.get("fiiBuy"))
                fii_sell = _to_float(row.get("sellValueFii") or row.get("fiiSellValue") or row.get("fiiSell"))
                dii_buy = _to_float(row.get("buyValueDii") or row.get("diiBuyValue") or row.get("diiBuy"))
                dii_sell = _to_float(row.get("sellValueDii") or row.get("diiSellValue") or row.get("diiSell"))
                fii_net = _to_float(row.get("netValueFii")) or (fii_buy - fii_sell)
                dii_net = _to_float(row.get("netValueDii")) or (dii_buy - dii_sell)

                parsed.append(
                    {
                        "date": row.get("date") or row.get("tradeDate") or datetime.utcnow().strftime("%Y-%m-%d"),
                        "fii_buy": fii_buy,
                        "fii_sell": fii_sell,
                        "fii_net": fii_net,
                        "dii_buy": dii_buy,
                        "dii_sell": dii_sell,
                        "dii_net": dii_net,
                        "source": "live",
                    }
                )

            if not parsed:
                raise ValueError("Empty FII/DII payload")

            return parsed
    except Exception as exc:
        logger.warning("Failed to fetch live FII/DII data: %s", exc)
        sample = _sample_history()
        for row in sample:
            row["source"] = "sample_data"
        return sample


async def fetch_fii_dii_data() -> dict[str, Any]:
    history = await _fetch_fii_dii_history()
    latest = history[0] if history else {}

    return {
        "date": latest.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "fii_buy": _to_float(latest.get("fii_buy")),
        "fii_sell": _to_float(latest.get("fii_sell")),
        "fii_net": _to_float(latest.get("fii_net")),
        "dii_buy": _to_float(latest.get("dii_buy")),
        "dii_sell": _to_float(latest.get("dii_sell")),
        "dii_net": _to_float(latest.get("dii_net")),
        "total_net": _to_float(latest.get("fii_net")) + _to_float(latest.get("dii_net")),
        "source": latest.get("source", "live"),
    }


async def analyze_fii_dii_trend(days: int) -> dict[str, Any]:
    lookback = max(1, int(days))
    history = await _fetch_fii_dii_history()
    window = history[:lookback]

    if not window:
        window = _sample_history()[:lookback]

    fii_values = [_to_float(item.get("fii_net")) for item in window]
    dii_values = [_to_float(item.get("dii_net")) for item in window]

    total_fii_net_7d = float(sum(fii_values[:7]))
    total_dii_net_7d = float(sum(dii_values[:7]))

    def _trend(total_net: float) -> str:
        if total_net > 250:
            return "BUYING"
        if total_net < -250:
            return "SELLING"
        return "NEUTRAL"

    def _consecutive(values: list[float], positive: bool) -> int:
        count = 0
        for value in values:
            if positive and value > 0:
                count += 1
            elif not positive and value < 0:
                count += 1
            else:
                break
        return count

    fii_trend = _trend(total_fii_net_7d)
    dii_trend = _trend(total_dii_net_7d)
    consecutive_fii_buying_days = _consecutive(fii_values, True)
    consecutive_fii_selling_days = _consecutive(fii_values, False)

    if fii_trend == "BUYING" and dii_trend != "BUYING":
        market_sentiment = "BULLISH"
    elif fii_trend == "SELLING" and dii_trend != "SELLING":
        market_sentiment = "BEARISH"
    else:
        market_sentiment = "MIXED"

    insight = (
        f"FII is {fii_trend.lower()} with {consecutive_fii_buying_days} buying streak days, "
        f"while DII is {dii_trend.lower()}, indicating {market_sentiment.lower()} market bias."
    )

    return {
        "fii_trend": fii_trend,
        "dii_trend": dii_trend,
        "consecutive_fii_buying_days": consecutive_fii_buying_days,
        "consecutive_fii_selling_days": consecutive_fii_selling_days,
        "total_fii_net_7d": total_fii_net_7d,
        "total_dii_net_7d": total_dii_net_7d,
        "market_sentiment": market_sentiment,
        "insight": insight,
    }


def get_sector_fii_activity() -> dict[str, dict[str, Any]]:
    return {
        "IT": {"net_flow": 520.0, "trend": "BUYING"},
        "Banking": {"net_flow": 880.0, "trend": "BUYING"},
        "Pharma": {"net_flow": -120.0, "trend": "SELLING"},
        "Auto": {"net_flow": 240.0, "trend": "BUYING"},
        "FMCG": {"net_flow": -90.0, "trend": "SELLING"},
        "Metals": {"net_flow": -260.0, "trend": "SELLING"},
        "Energy": {"net_flow": 140.0, "trend": "BUYING"},
        "Realty": {"net_flow": -45.0, "trend": "SELLING"},
    }
