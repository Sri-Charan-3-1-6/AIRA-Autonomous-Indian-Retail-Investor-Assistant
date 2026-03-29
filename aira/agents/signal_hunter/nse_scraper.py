"""AIRA module: agents/signal_hunter/nse_scraper.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NSE_BASE_URL = "https://www.nseindia.com/"
CORPORATE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"
BULK_DEALS_URL = "https://www.nseindia.com/api/snapshot-capital-market-largeDeals"
GAINERS_URL = "https://www.nseindia.com/api/live-analysis-variations?index=gainers"
LOSERS_URL = "https://www.nseindia.com/api/live-analysis-variations?index=losers"
QUOTE_URL = "https://www.nseindia.com/api/quote-equity?symbol={symbol}"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


async def _prime_session(client: httpx.AsyncClient) -> None:
    logger.info("Priming NSE session")
    response = await client.get(NSE_BASE_URL)
    if response.text:
        soup = BeautifulSoup(response.text, "lxml")
        title = soup.title.text.strip() if soup.title and soup.title.text else "nse"
        logger.debug("NSE landing page title: %s", title)
    await asyncio.sleep(2)


async def _safe_get_json(url: str) -> dict[str, Any]:
    logger.info("NSE request: %s", url)
    async with httpx.AsyncClient(headers=REQUEST_HEADERS, timeout=20.0, follow_redirects=True) as client:
        await _prime_session(client)
        response = await client.get(url)
        response.raise_for_status()
        await asyncio.sleep(2)
        return response.json()


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


def _sample_corporate_announcements() -> list[dict[str, Any]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return [
        {
            "symbol": "INFY",
            "company": "Infosys Limited",
            "subject": "Board approves special dividend",
            "date": today,
            "category": "Dividend",
            "attachment_url": "",
            "source": "sample_data",
        },
        {
            "symbol": "LT",
            "company": "Larsen & Toubro Limited",
            "subject": "Major infrastructure order win in Middle East",
            "date": today,
            "category": "Order Win",
            "attachment_url": "",
            "source": "sample_data",
        },
    ]


def _sample_bulk_deals() -> list[dict[str, Any]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return [
        {
            "symbol": "HDFCBANK",
            "company": "HDFC Bank Limited",
            "deal_type": "BUY",
            "quantity": 2500000,
            "price": 1675.5,
            "client_name": "Sample Global Fund",
            "date": today,
            "source": "sample_data",
        },
        {
            "symbol": "SBIN",
            "company": "State Bank of India",
            "deal_type": "SELL",
            "quantity": 1800000,
            "price": 782.25,
            "client_name": "Sample Domestic Fund",
            "date": today,
            "source": "sample_data",
        },
    ]


def _sample_gainers_losers() -> dict[str, list[dict[str, Any]]]:
    return {
        "gainers": [
            {
                "symbol": "TATASTEEL",
                "company": "Tata Steel Limited",
                "change_percent": 4.8,
                "volume": 9200000,
                "source": "sample_data",
            },
            {
                "symbol": "ICICIBANK",
                "company": "ICICI Bank Limited",
                "change_percent": 3.1,
                "volume": 6100000,
                "source": "sample_data",
            },
        ],
        "losers": [
            {
                "symbol": "BAJAJFINSV",
                "company": "Bajaj Finserv Limited",
                "change_percent": -2.7,
                "volume": 1200000,
                "source": "sample_data",
            }
        ],
    }


def _sample_stock_quote(symbol: str) -> dict[str, Any]:
    upper = symbol.upper()
    return {
        "symbol": upper,
        "company_name": f"{upper} Sample Limited",
        "last_price": 1234.5,
        "change": 28.5,
        "change_percent": 2.36,
        "volume": 2500000,
        "pe_ratio": 24.6,
        "week_52_high": 1480.0,
        "week_52_low": 960.0,
        "source": "sample_data",
    }


async def fetch_corporate_announcements() -> list[dict[str, Any]]:
    try:
        payload = await _safe_get_json(CORPORATE_ANNOUNCEMENTS_URL)
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            rows = []

        announcements: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            announcements.append(
                {
                    "symbol": str(row.get("symbol") or row.get("sm_name") or "").upper(),
                    "company": row.get("sm_name") or row.get("companyName") or "",
                    "subject": row.get("subject") or row.get("desc") or "",
                    "date": row.get("an_dt") or row.get("date") or row.get("bcStartDate") or "",
                    "category": row.get("ca") or row.get("category") or "General",
                    "attachment_url": row.get("attchmntFile") or row.get("attchmnt") or "",
                    "source": "live",
                }
            )

        return announcements
    except Exception as exc:
        logger.warning("Failed to fetch corporate announcements: %s", exc)
        return _sample_corporate_announcements()


async def fetch_bulk_deals() -> list[dict[str, Any]]:
    try:
        payload = await _safe_get_json(BULK_DEALS_URL)
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            rows = []

        deals: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            deal_type_raw = str(row.get("buySell") or row.get("dealType") or "").upper()
            deal_type = "BUY" if "B" in deal_type_raw or "BUY" in deal_type_raw else "SELL"
            deals.append(
                {
                    "symbol": str(row.get("symbol") or row.get("symbolName") or "").upper(),
                    "company": row.get("securityName") or row.get("company") or "",
                    "deal_type": deal_type,
                    "quantity": _to_int(row.get("quantity") or row.get("qty")),
                    "price": _to_float(row.get("price") or row.get("avgPrice")),
                    "client_name": row.get("clientName") or row.get("client") or "",
                    "date": row.get("date") or row.get("tradeDate") or "",
                    "source": "live",
                }
            )

        return deals
    except Exception as exc:
        logger.warning("Failed to fetch bulk deals: %s", exc)
        return _sample_bulk_deals()


async def fetch_nse_gainers_losers() -> dict[str, list[dict[str, Any]]]:
    try:
        gainers_payload, losers_payload = await asyncio.gather(
            _safe_get_json(GAINERS_URL),
            _safe_get_json(LOSERS_URL),
        )

        def _parse(items: Any) -> list[dict[str, Any]]:
            rows = items.get("data") if isinstance(items, dict) else items
            if not isinstance(rows, list):
                rows = []
            parsed: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                parsed.append(
                    {
                        "symbol": str(row.get("symbol") or row.get("identifier") or "").upper(),
                        "company": row.get("companyName") or row.get("meta") or row.get("symbol") or "",
                        "change_percent": _to_float(
                            row.get("pChange") or row.get("perChange365d") or row.get("change")
                        ),
                        "volume": _to_int(row.get("totalTradedVolume") or row.get("volume") or 0),
                        "source": "live",
                    }
                )
            return parsed

        return {
            "gainers": _parse(gainers_payload),
            "losers": _parse(losers_payload),
        }
    except Exception as exc:
        logger.warning("Failed to fetch gainers/losers: %s", exc)
        return _sample_gainers_losers()


async def fetch_stock_quote(symbol: str) -> dict[str, Any]:
    try:
        clean_symbol = symbol.upper().strip()
        payload = await _safe_get_json(QUOTE_URL.format(symbol=clean_symbol))
        info = payload.get("info", {}) if isinstance(payload, dict) else {}
        price_info = payload.get("priceInfo", {}) if isinstance(payload, dict) else {}
        security = payload.get("securityInfo", {}) if isinstance(payload, dict) else {}
        pre_open = payload.get("preOpenMarket", {}).get("totalTradedVolume") if isinstance(payload, dict) else None

        return {
            "symbol": clean_symbol,
            "company_name": info.get("companyName") or info.get("symbol") or clean_symbol,
            "last_price": _to_float(price_info.get("lastPrice")),
            "change": _to_float(price_info.get("change")),
            "change_percent": _to_float(price_info.get("pChange")),
            "volume": _to_int(pre_open or security.get("issuedSize") or 0),
            "pe_ratio": _to_float(security.get("pe")),
            "week_52_high": _to_float(price_info.get("weekHighLow", {}).get("max")),
            "week_52_low": _to_float(price_info.get("weekHighLow", {}).get("min")),
            "source": "live",
        }
    except Exception as exc:
        logger.warning("Failed to fetch stock quote for %s: %s", symbol, exc)
        return _sample_stock_quote(symbol)
