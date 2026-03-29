"""AIRA module: agents/signal_hunter/agent.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from agents.signal_hunter import fii_dii_tracker, insider_tracker, nse_scraper
from agents.signal_hunter.opportunity_scorer import categorize_signal, generate_signal_explanation, score_opportunity
from agents.signal_hunter.portfolio_filter import filter_signals_by_portfolio, get_user_portfolio_context
from core.supabase_client import get_supabase
from db import crud
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)


class SignalHunterAgent(BaseAgent):
    agent_name = "signal_hunter"
    agent_version = "2.0.0"

    async def _save_signals(self, signals: list[dict[str, Any]]) -> int:
        if not signals:
            return 0

        def _op() -> int:
            client = get_supabase()
            rows = []
            for signal in signals:
                rows.append(
                    {
                        "symbol": signal["symbol"],
                        "signal_type": signal["signal_type"],
                        "opportunity_score": signal["opportunity_score"],
                        "data": {
                            "company": signal.get("company", ""),
                            "category": signal.get("category", "NEUTRAL"),
                            "explanation": signal.get("explanation", ""),
                            "payload": signal.get("data", {}),
                        },
                    }
                )

            response = client.table("market_signals").insert(rows).execute()
            return len(response.data or rows)

        return await asyncio.to_thread(_op)

    async def _fetch_recent_signals(self, limit: int) -> list[dict[str, Any]]:
        def _op() -> list[dict[str, Any]]:
            client = get_supabase()
            try:
                # Prefer database-side de-duplication: keep the highest-score row per symbol.
                # DISTINCT ON requires symbol to appear first in ORDER BY.
                response = (
                    client.table("market_signals")
                    .select("distinct on (symbol) *")
                    .order("symbol")
                    .order("opportunity_score", desc=True)
                    .limit(limit)
                    .execute()
                )
                rows = response.data or []
            except Exception:
                # Fallback path if DISTINCT ON is not supported by the active PostgREST setup.
                response = (
                    client.table("market_signals")
                    .select("*")
                    .order("opportunity_score", desc=True)
                    .limit(max(limit * 10, 100))
                    .execute()
                )
                rows = response.data or []

            deduped: dict[str, dict[str, Any]] = {}
            for row in rows:
                symbol = str(row.get("symbol") or "").upper()
                if not symbol:
                    continue
                current = deduped.get(symbol)
                if current is None or float(row.get("opportunity_score") or 0.0) > float(
                    current.get("opportunity_score") or 0.0
                ):
                    deduped[symbol] = row

            return sorted(
                deduped.values(), key=lambda item: float(item.get("opportunity_score") or 0.0), reverse=True
            )[:limit]

        return await asyncio.to_thread(_op)

    async def _run_market_scan(self) -> dict[str, Any]:
        logger.info("SignalHunter scan started")
        announcements_task = nse_scraper.fetch_corporate_announcements()
        bulk_deals_task = nse_scraper.fetch_bulk_deals()
        gainers_losers_task = nse_scraper.fetch_nse_gainers_losers()
        insider_trades_task = insider_tracker.fetch_insider_trades()
        fii_snapshot_task = fii_dii_tracker.fetch_fii_dii_data()
        fii_trend_task = fii_dii_tracker.analyze_fii_dii_trend(7)

        announcements, bulk_deals, gainers_losers, insider_trades, fii_snapshot, fii_trend = await asyncio.gather(
            announcements_task,
            bulk_deals_task,
            gainers_losers_task,
            insider_trades_task,
            fii_snapshot_task,
            fii_trend_task,
        )

        sentiment_by_symbol = insider_tracker.analyze_insider_sentiment(insider_trades)
        unusual_activity = insider_tracker.detect_unusual_insider_activity(insider_trades)
        unusual_by_symbol = {item["symbol"]: item for item in unusual_activity}

        symbols: set[str] = set()
        symbols.update([str(item.get("symbol") or "").upper() for item in announcements])
        symbols.update([str(item.get("symbol") or "").upper() for item in bulk_deals])
        symbols.update([str(item.get("symbol") or "").upper() for item in insider_trades])
        symbols = {symbol for symbol in symbols if symbol}

        quotes_raw = await asyncio.gather(*[nse_scraper.fetch_stock_quote(symbol) for symbol in symbols])
        quotes = {str(item.get("symbol") or "").upper(): item for item in quotes_raw if isinstance(item, dict)}

        announcements_by_symbol = {str(item.get("symbol") or "").upper(): item for item in announcements}
        bulk_buy_by_symbol = {
            str(item.get("symbol") or "").upper(): item
            for item in bulk_deals
            if str(item.get("deal_type") or "").upper() == "BUY"
        }

        gainers = {str(item.get("symbol") or "").upper() for item in gainers_losers.get("gainers", [])}
        losers = {str(item.get("symbol") or "").upper() for item in gainers_losers.get("losers", [])}

        scored_signals: list[dict[str, Any]] = []
        for symbol in symbols:
            quote = quotes.get(symbol, {})
            signal_payload = {
                "symbol": symbol,
                "announcement": announcements_by_symbol.get(symbol, {}),
                "bulk_deal": bulk_buy_by_symbol.get(symbol, {}),
                "insider": sentiment_by_symbol.get(symbol, unusual_by_symbol.get(symbol, {})),
                "quote": quote,
                "fii_dii": {
                    **fii_snapshot,
                    "consecutive_fii_buying_days": fii_trend.get("consecutive_fii_buying_days", 0),
                },
                "volume_surge_percent": 220.0 if symbol in gainers else (90.0 if symbol in losers else 140.0),
            }

            score = score_opportunity(signal_payload)
            category = categorize_signal(score)
            explanation = generate_signal_explanation(signal_payload, score)

            scored_signals.append(
                {
                    "symbol": symbol,
                    "company": quote.get("company_name")
                    or signal_payload["announcement"].get("company")
                    or signal_payload["bulk_deal"].get("company")
                    or symbol,
                    "signal_type": "composite",
                    "opportunity_score": score,
                    "category": category,
                    "explanation": explanation,
                    "data": {
                        **signal_payload,
                        "fii_trend": fii_trend,
                        "source": "live" if quote.get("source") == "live" else "sample_data",
                    },
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

        saved_count = await self._save_signals(scored_signals)
        high_priority_count = sum(1 for item in scored_signals if float(item.get("opportunity_score", 0.0)) > 80)

        return {
            "total_signals_found": len(scored_signals),
            "high_priority_count": high_priority_count,
            "saved_signals": saved_count,
            "scan_time": datetime.utcnow().isoformat(),
        }

    async def _get_personalized_signals(self, user_id: str, limit: int) -> dict[str, Any]:
        raw_signals = await self._fetch_recent_signals(max(limit * 5, 50))
        formatted: list[dict[str, Any]] = []
        for row in raw_signals:
            payload = row.get("data") or {}
            formatted.append(
                {
                    "id": row.get("id"),
                    "symbol": row.get("symbol"),
                    "company": payload.get("company") or row.get("symbol"),
                    "signal_type": row.get("signal_type"),
                    "opportunity_score": row.get("opportunity_score"),
                    "category": payload.get("category") or "NEUTRAL",
                    "explanation": payload.get("explanation") or "",
                    "data": payload.get("payload") or {},
                }
            )

        client = get_supabase()
        portfolio_context = await get_user_portfolio_context(user_id, client)
        personalized = filter_signals_by_portfolio(formatted, portfolio_context)

        return {
            "user_id": user_id,
            "portfolio_context": portfolio_context,
            "signals": personalized[:limit],
        }

    async def _score_single_symbol(self, symbol: str) -> dict[str, Any]:
        clean_symbol = symbol.upper().strip()
        quote, insider_trades, fii_snapshot, fii_trend = await asyncio.gather(
            nse_scraper.fetch_stock_quote(clean_symbol),
            insider_tracker.fetch_insider_trades(),
            fii_dii_tracker.fetch_fii_dii_data(),
            fii_dii_tracker.analyze_fii_dii_trend(7),
        )

        symbol_trades = [trade for trade in insider_trades if str(trade.get("symbol") or "").upper() == clean_symbol]
        insider_sentiment = insider_tracker.analyze_insider_sentiment(symbol_trades).get(clean_symbol, {})
        unusual = insider_tracker.detect_unusual_insider_activity(symbol_trades)

        signal_payload = {
            "symbol": clean_symbol,
            "insider": insider_sentiment if insider_sentiment else (unusual[0] if unusual else {}),
            "quote": quote,
            "fii_dii": {
                **fii_snapshot,
                "consecutive_fii_buying_days": fii_trend.get("consecutive_fii_buying_days", 0),
            },
            "announcement": {},
            "bulk_deal": {},
            "volume_surge_percent": 150.0,
        }

        score = score_opportunity(signal_payload)
        category = categorize_signal(score)
        explanation = generate_signal_explanation(signal_payload, score)

        return {
            "symbol": clean_symbol,
            "company": quote.get("company_name") or clean_symbol,
            "score": score,
            "category": category,
            "explanation": explanation,
            "quote": quote,
            "insider_activity": symbol_trades[:5],
            "fii_dii": fii_snapshot,
            "fii_dii_trend": fii_trend,
        }

    async def run(self, task: AgentTask) -> AgentTask:
        logger.info("SignalHunterAgent started task_id=%s", task.task_id)
        task.status = "running"
        try:
            input_data = task.input_data or {}
            action = str(input_data.get("action") or "scan").strip().lower()
            user_id = str(input_data.get("user_id") or task.user_id)
            symbol = str(input_data.get("symbol") or "").strip().upper()
            limit = int(input_data.get("limit") or 10)

            if action == "scan":
                task.output_data = await self._run_market_scan()
                task.confidence_score = 0.84
            elif action == "get_signals":
                task.output_data = await self._get_personalized_signals(user_id, limit)
                task.confidence_score = 0.82
            elif action == "score_symbol":
                if not symbol:
                    raise ValueError("symbol is required for action=score_symbol")
                task.output_data = await self._score_single_symbol(symbol)
                task.confidence_score = 0.8
            else:
                raise ValueError("action must be one of: scan, get_signals, score_symbol")

            task.status = "completed"
            task.completed_at = datetime.utcnow()
            await self.log_to_audit(task, crud)
            logger.info("SignalHunterAgent completed task_id=%s", task.task_id)
            return task
        except Exception as exc:
            logger.exception("SignalHunterAgent failed task_id=%s: %s", task.task_id, exc)
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            await self.log_to_audit(task, crud)
            return task

    async def health_check(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": "healthy",
            "version": self.agent_version,
            "phase": "phase_3",
            "capabilities": [
                "nse_filings_monitoring",
                "insider_trade_detection",
                "bulk_deal_tracking",
                "fii_dii_flow_analysis",
                "portfolio_personalized_filtering",
                "opportunity_scoring",
            ],
        }
