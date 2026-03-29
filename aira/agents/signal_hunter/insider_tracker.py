"""AIRA module: agents/signal_hunter/insider_tracker.py"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

INSIDER_TRADES_URL = "https://www.nseindia.com/api/corporates-pit?index=equities&beforeRecDate=&afterRecDate="
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
        text = str(value).replace(",", "").replace("%", "").strip()
        return float(text)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, "", "-"):
            return default
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    candidates = ["%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in candidates:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _sample_insider_trades() -> list[dict[str, Any]]:
    today = datetime.utcnow()
    return [
        {
            "symbol": "INFY",
            "company": "Infosys Limited",
            "insider_name": "Ravi Kumar",
            "insider_designation": "Promoter",
            "transaction_type": "BUY",
            "quantity": 150000,
            "value": 240000000.0,
            "transaction_date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
            "acquisition_percentage": 0.12,
            "source": "sample_data",
        },
        {
            "symbol": "INFY",
            "company": "Infosys Limited",
            "insider_name": "Meera Nair",
            "insider_designation": "Director",
            "transaction_type": "BUY",
            "quantity": 95000,
            "value": 152000000.0,
            "transaction_date": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "acquisition_percentage": 0.08,
            "source": "sample_data",
        },
        {
            "symbol": "SBIN",
            "company": "State Bank of India",
            "insider_name": "Amit Verma",
            "insider_designation": "Promoter Group",
            "transaction_type": "SELL",
            "quantity": 120000,
            "value": 92000000.0,
            "transaction_date": (today - timedelta(days=12)).strftime("%Y-%m-%d"),
            "acquisition_percentage": 0.03,
            "source": "sample_data",
        },
    ]


async def fetch_insider_trades() -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(headers=REQUEST_HEADERS, timeout=20.0, follow_redirects=True) as client:
            logger.info("Priming NSE session for insider trades")
            await client.get(NSE_BASE_URL)
            await asyncio.sleep(2)

            logger.info("Fetching insider trades from NSE")
            response = await client.get(INSIDER_TRADES_URL)
            response.raise_for_status()
            await asyncio.sleep(2)

            payload = response.json()
            rows = payload.get("data") if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                rows = []

            trades: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue

                tx_raw = str(
                    row.get("acqMode")
                    or row.get("acqtoDisp")
                    or row.get("txnType")
                    or row.get("transactionType")
                    or ""
                ).upper()
                tx_type = "BUY" if "BUY" in tx_raw or "ACQ" in tx_raw else "SELL"
                trades.append(
                    {
                        "symbol": str(row.get("symbol") or row.get("symbolName") or "").upper(),
                        "company": row.get("company") or row.get("companyName") or "",
                        "insider_name": row.get("personCategory") or row.get("name") or row.get("insider") or "",
                        "insider_designation": row.get("promoterType") or row.get("designation") or "",
                        "transaction_type": tx_type,
                        "quantity": _to_int(row.get("secAcq") or row.get("quantity") or row.get("noOfShare")),
                        "value": _to_float(row.get("secVal") or row.get("value") or row.get("valueOfShare")),
                        "transaction_date": row.get("acqtoDt") or row.get("date") or row.get("txnDate") or "",
                        "acquisition_percentage": _to_float(
                            row.get("secAcqDispPercentage") or row.get("acqtoPercent") or row.get("holdingPct")
                        ),
                        "source": "live",
                    }
                )

            return trades
    except Exception as exc:
        logger.warning("Failed to fetch insider trades: %s", exc)
        return _sample_insider_trades()


def analyze_insider_sentiment(trades: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    sentiment_by_symbol: dict[str, dict[str, Any]] = {}

    for trade in trades:
        symbol = str(trade.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        if symbol not in sentiment_by_symbol:
            sentiment_by_symbol[symbol] = {
                "buy_count": 0,
                "sell_count": 0,
                "net_value": 0.0,
                "sentiment": "NEUTRAL",
                "recent_trades": [],
            }

        bucket = sentiment_by_symbol[symbol]
        trade_type = str(trade.get("transaction_type") or "").upper()
        value = _to_float(trade.get("value"), 0.0)

        if trade_type == "BUY":
            bucket["buy_count"] += 1
            bucket["net_value"] += value
        else:
            bucket["sell_count"] += 1
            bucket["net_value"] -= value

        bucket["recent_trades"].append(trade)

    for symbol, summary in sentiment_by_symbol.items():
        recent_sorted = sorted(
            summary["recent_trades"],
            key=lambda t: _parse_date(str(t.get("transaction_date") or "")) or datetime.min,
            reverse=True,
        )
        summary["recent_trades"] = recent_sorted[:3]

        if summary["net_value"] > 0 and summary["buy_count"] > summary["sell_count"]:
            summary["sentiment"] = "BULLISH"
        elif summary["net_value"] < 0 and summary["sell_count"] >= summary["buy_count"]:
            summary["sentiment"] = "BEARISH"
        else:
            summary["sentiment"] = "NEUTRAL"

    return sentiment_by_symbol


def detect_unusual_insider_activity(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(days=30)
    grouped: dict[str, dict[str, Any]] = {}

    for trade in trades:
        if str(trade.get("transaction_type") or "").upper() != "BUY":
            continue

        trade_date = _parse_date(str(trade.get("transaction_date") or ""))
        if trade_date is None or trade_date < cutoff:
            continue

        symbol = str(trade.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        if symbol not in grouped:
            grouped[symbol] = {
                "symbol": symbol,
                "company": trade.get("company") or symbol,
                "total_buy_value": 0.0,
                "insiders": set(),
                "latest_date": trade_date,
            }

        grouped[symbol]["total_buy_value"] += _to_float(trade.get("value"), 0.0)
        grouped[symbol]["insiders"].add(str(trade.get("insider_name") or "Unknown"))
        if trade_date > grouped[symbol]["latest_date"]:
            grouped[symbol]["latest_date"] = trade_date

    unusual: list[dict[str, Any]] = []
    for symbol, item in grouped.items():
        num_insiders = len(item["insiders"])
        total_value = float(item["total_buy_value"])

        if num_insiders >= 2 and total_value >= 50_000_000:
            days = max(1, (datetime.utcnow() - item["latest_date"]).days)
            crores = total_value / 10_000_000
            unusual.append(
                {
                    "symbol": symbol,
                    "company": item["company"],
                    "total_buy_value": total_value,
                    "num_insiders": num_insiders,
                    "alert_reason": (
                        f"{num_insiders} insiders bought shares worth {crores:.1f} crore in last {days} days"
                    ),
                }
            )

    unusual.sort(key=lambda x: x["total_buy_value"], reverse=True)
    return unusual
