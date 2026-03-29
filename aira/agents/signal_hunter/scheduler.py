"""AIRA module: agents/signal_hunter/scheduler.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.signal_hunter import fii_dii_tracker, nse_scraper
from agents.signal_hunter.opportunity_scorer import categorize_signal, generate_signal_explanation, score_opportunity
from core.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _build_signal_payload(symbol: str, company: str, signal_type: str, data: dict[str, Any]) -> dict[str, Any]:
    score = score_opportunity(data)
    return {
        "symbol": symbol,
        "company": company,
        "signal_type": signal_type,
        "opportunity_score": score,
        "category": categorize_signal(score),
        "explanation": generate_signal_explanation({"symbol": symbol, **data}, score),
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
    }


async def _save_signals(signals: list[dict[str, Any]]) -> None:
    if not signals:
        return

    def _op() -> None:
        client = get_supabase()
        rows = [
            {
                "symbol": signal["symbol"],
                "signal_type": signal["signal_type"],
                "opportunity_score": signal["opportunity_score"],
                "data": {
                    "company": signal.get("company"),
                    "category": signal.get("category"),
                    "explanation": signal.get("explanation"),
                    "payload": signal.get("data", {}),
                },
            }
            for signal in signals
            if float(signal.get("opportunity_score", 0.0)) > 40.0
        ]
        if rows:
            client.table("market_signals").insert(rows).execute()

    await asyncio.to_thread(_op)


async def run_morning_scan() -> None:
    logger.info("Starting morning market scan")
    announcements, bulk_deals, fii_snapshot = await asyncio.gather(
        nse_scraper.fetch_corporate_announcements(),
        nse_scraper.fetch_bulk_deals(),
        fii_dii_tracker.fetch_fii_dii_data(),
    )

    signals: list[dict[str, Any]] = []

    for item in announcements:
        symbol = str(item.get("symbol") or "").upper()
        if not symbol:
            continue
        quote = await nse_scraper.fetch_stock_quote(symbol)
        payload = {
            "announcement": item,
            "quote": quote,
            "fii_dii": fii_snapshot,
            "volume_surge_percent": 160,
        }
        signals.append(_build_signal_payload(symbol, str(item.get("company") or symbol), "announcement", payload))

    for item in bulk_deals:
        symbol = str(item.get("symbol") or "").upper()
        if not symbol:
            continue
        quote = await nse_scraper.fetch_stock_quote(symbol)
        payload = {
            "bulk_deal": item,
            "quote": quote,
            "fii_dii": fii_snapshot,
            "volume_surge_percent": 220 if item.get("deal_type") == "BUY" else 110,
        }
        signals.append(_build_signal_payload(symbol, str(item.get("company") or symbol), "bulk_deal", payload))

    await _save_signals(signals)
    high_priority = sum(1 for signal in signals if float(signal.get("opportunity_score", 0.0)) > 80)
    logger.info(
        "Morning scan complete: found %s signals, %s high priority",
        len(signals),
        high_priority,
    )


async def run_midday_scan() -> None:
    logger.info("Midday scan triggered")
    await run_morning_scan()


async def run_closing_scan() -> None:
    logger.info("Closing scan triggered")
    await run_morning_scan()


async def run_bulk_deals_scan() -> None:
    logger.info("Bulk deals scan triggered")
    deals = await nse_scraper.fetch_bulk_deals()
    fii_snapshot = await fii_dii_tracker.fetch_fii_dii_data()

    signals: list[dict[str, Any]] = []
    for item in deals:
        symbol = str(item.get("symbol") or "").upper()
        if not symbol:
            continue
        quote = await nse_scraper.fetch_stock_quote(symbol)
        payload = {
            "bulk_deal": item,
            "quote": quote,
            "fii_dii": fii_snapshot,
            "volume_surge_percent": 210,
        }
        signals.append(_build_signal_payload(symbol, str(item.get("company") or symbol), "bulk_deal", payload))

    await _save_signals(signals)
    logger.info("Bulk deals scan complete: found %s signals", len(signals))


def create_scheduler() -> AsyncIOScheduler:
    tz = ZoneInfo("Asia/Kolkata")
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(run_morning_scan, CronTrigger(day_of_week="mon-fri", hour=9, minute=15, timezone=tz))
    scheduler.add_job(run_midday_scan, CronTrigger(day_of_week="mon-fri", hour=12, minute=30, timezone=tz))
    scheduler.add_job(run_closing_scan, CronTrigger(day_of_week="mon-fri", hour=15, minute=45, timezone=tz))
    scheduler.add_job(run_bulk_deals_scan, CronTrigger(day_of_week="mon-fri", hour=16, minute=0, timezone=tz))

    return scheduler


def start_scheduler(app) -> None:
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    if not _scheduler.running:
        _scheduler.start()
        logger.info("Signal Hunter scheduler started")
    app.state.signal_scheduler = _scheduler


def stop_scheduler(app) -> None:
    global _scheduler
    scheduler = getattr(app.state, "signal_scheduler", None) or _scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Signal Hunter scheduler stopped")
