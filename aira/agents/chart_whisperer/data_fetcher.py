"""AIRA module: agents/chart_whisperer/data_fetcher.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_ALLOWED_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
_ALLOWED_INTERVALS = {"1d", "1wk", "1mo"}


def get_nse_symbol(company_name: str) -> str:
    mapping = {
        "hdfc bank": "HDFCBANK",
        "reliance industries": "RELIANCE",
        "infosys": "INFY",
        "tcs": "TCS",
        "icici bank": "ICICIBANK",
        "axis bank": "AXISBANK",
        "kotak mahindra bank": "KOTAKBANK",
        "state bank of india": "SBIN",
        "bajaj finance": "BAJFINANCE",
        "hindustan unilever": "HINDUNILVR",
        "wipro": "WIPRO",
        "hcl technologies": "HCLTECH",
        "maruti suzuki": "MARUTI",
        "titan": "TITAN",
        "asian paints": "ASIANPAINT",
        "ultratech cement": "ULTRACEMCO",
        "nestle india": "NESTLEIND",
        "power grid": "POWERGRID",
        "ntpc": "NTPC",
        "ongc": "ONGC",
        "tata motors": "TATAMOTORS",
        "tata steel": "TATASTEEL",
        "jsw steel": "JSWSTEEL",
        "sun pharma": "SUNPHARMA",
        "dr reddys": "DRREDDY",
        "cipla": "CIPLA",
        "divis lab": "DIVISLAB",
        "bharti airtel": "BHARTIARTL",
        "adani enterprises": "ADANIENT",
        "itc": "ITC",
    }

    name = (company_name or "").strip().lower()
    for key, symbol in mapping.items():
        if key in name:
            return symbol

    fallback = (company_name or "").strip().upper().replace(" ", "")
    if not fallback:
        return "UNKNOWN.NS"
    if fallback.endswith(".NS"):
        return fallback
    return f"{fallback}.NS"


def _normalize_symbol(symbol: str) -> str:
    clean = (symbol or "").strip().upper()
    if not clean:
        return "UNKNOWN.NS"
    if clean.endswith(".NS"):
        return clean
    return f"{clean}.NS"


def _sample_stock_data(symbol: str, period: str, interval: str) -> dict[str, Any]:
    logger.warning("Using sample OHLCV data for %s", symbol)
    freq_map = {"1d": "B", "1wk": "W-FRI", "1mo": "MS"}
    periods = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252, "2y": 504, "5y": 1260}

    rows = max(40, periods.get(period, 132))
    idx = pd.date_range(end=pd.Timestamp.utcnow(), periods=rows, freq=freq_map.get(interval, "B"))
    base_price = 1000.0 + (abs(hash(symbol)) % 700)

    data_rows: list[dict[str, Any]] = []
    prev_close = base_price
    for i, date in enumerate(idx):
        drift = (i / max(rows, 1)) * 0.2
        swing = ((i % 12) - 6) * 0.45
        open_p = max(1.0, prev_close + swing * 0.7)
        close_p = max(1.0, open_p + swing + drift)
        high_p = max(open_p, close_p) + 4.5
        low_p = min(open_p, close_p) - 4.2
        volume = float(1_200_000 + (i % 25) * 40_000)
        returns_pct = ((close_p - prev_close) / prev_close) * 100 if prev_close else 0.0

        data_rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": float(round(open_p, 2)),
                "high": float(round(high_p, 2)),
                "low": float(round(max(0.1, low_p), 2)),
                "close": float(round(close_p, 2)),
                "volume": volume,
                "returns_pct": float(round(returns_pct, 4)),
            }
        )
        prev_close = close_p

    closes = [r["close"] for r in data_rows]
    volumes = [r["volume"] for r in data_rows]
    first_close = closes[0]
    last_close = closes[-1]
    total_return_pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0

    return {
        "symbol": symbol.replace(".NS", ""),
        "company_name": f"{symbol.replace('.NS', '')} Sample Ltd",
        "data": data_rows,
        "summary": {
            "current_price": float(round(last_close, 2)),
            "change_pct": float(round(data_rows[-1]["returns_pct"], 4)),
            "week_52_high": float(round(max(closes), 2)),
            "week_52_low": float(round(min(closes), 2)),
            "avg_volume": float(round(sum(volumes) / len(volumes), 2)),
            "total_return_pct": float(round(total_return_pct, 4)),
        },
        "source": "sample_data",
    }


async def fetch_stock_data(symbol: str, period: str = "6mo", interval: str = "1d") -> dict[str, Any]:
    try:
        requested_period = period if period in _ALLOWED_PERIODS else "6mo"
        requested_interval = interval if interval in _ALLOWED_INTERVALS else "1d"
        nse_symbol = _normalize_symbol(symbol)

        logger.info(
            "Fetching stock data symbol=%s period=%s interval=%s",
            nse_symbol,
            requested_period,
            requested_interval,
        )

        def _fetch() -> dict[str, Any]:
            ticker = yf.Ticker(nse_symbol)
            hist = ticker.history(period=requested_period, interval=requested_interval, auto_adjust=False)
            info = ticker.info if isinstance(getattr(ticker, "info", {}), dict) else {}

            if hist is None or hist.empty:
                raise ValueError("Empty history from yfinance")

            hist = hist.rename(columns=str.lower)
            for col in ["open", "high", "low", "close", "volume"]:
                if col not in hist.columns:
                    hist[col] = 0.0

            hist = hist[["open", "high", "low", "close", "volume"]].copy()
            hist = hist.dropna(subset=["close"])
            hist["returns_pct"] = hist["close"].pct_change().fillna(0.0) * 100

            data_rows: list[dict[str, Any]] = []
            for dt, row in hist.iterrows():
                date_value = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
                data_rows.append(
                    {
                        "date": date_value,
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                        "returns_pct": float(row["returns_pct"]),
                    }
                )

            closes = hist["close"]
            volumes = hist["volume"]
            first_close = float(closes.iloc[0])
            last_close = float(closes.iloc[-1])
            total_return_pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0

            summary = {
                "current_price": float(last_close),
                "change_pct": float(hist["returns_pct"].iloc[-1]),
                "week_52_high": float(closes.max()),
                "week_52_low": float(closes.min()),
                "avg_volume": float(volumes.mean()),
                "total_return_pct": float(total_return_pct),
            }

            company_name = (
                info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or nse_symbol.replace(".NS", "")
            )

            return {
                "symbol": nse_symbol.replace(".NS", ""),
                "company_name": company_name,
                "data": data_rows,
                "summary": summary,
                "source": "live",
            }

        return await asyncio.to_thread(_fetch)
    except Exception as exc:
        logger.warning("Failed to fetch live stock data for %s: %s", symbol, exc)
        return _sample_stock_data(_normalize_symbol(symbol), period, interval)


async def fetch_multiple_stocks(symbols: list[str], period: str = "6mo") -> dict[str, dict[str, Any]]:
    logger.info("Fetching multiple stocks count=%s period=%s", len(symbols), period)
    tasks = [fetch_stock_data(symbol, period=period, interval="1d") for symbol in symbols]
    results = await asyncio.gather(*tasks)

    output: dict[str, dict[str, Any]] = {}
    for symbol, result in zip(symbols, results):
        output[str(symbol).upper()] = result
    return output
