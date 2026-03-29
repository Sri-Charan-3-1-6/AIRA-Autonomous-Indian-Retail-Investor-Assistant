"""AIRA module: orchestrator/orchestrator.py"""

import asyncio
from datetime import datetime
from time import perf_counter
import logging
from typing import Any

from agents.base_agent import BaseAgent
from core.supabase_client import get_supabase
from db import crud
from models.agent_task import AgentTask


logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self) -> None:
        self.agents: dict[str, BaseAgent] = {}

    def register_agent(self, agent_name: str, agent: BaseAgent) -> None:
        self.agents[agent_name] = agent

    async def dispatch(self, agent_name: str, task: AgentTask) -> AgentTask:
        if agent_name not in self.agents:
            task.status = "failed"
            task.error_message = f"Agent '{agent_name}' is not registered"
            task.completed_at = datetime.utcnow()
            await crud.log_audit(task)
            return task

        agent = self.agents[agent_name]
        task.status = "running"

        try:
            result = await agent.run(task)
            if result.completed_at is None:
                result.completed_at = datetime.utcnow()
            await agent.log_to_audit(result, crud)
            return result
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            await agent.log_to_audit(task, crud)
            return task

    async def run_morning_pipeline(self, user_id: str) -> dict:
        pipeline_started_at = perf_counter()
        now_utc = datetime.utcnow()
        if now_utc.weekday() >= 5:
            logger.warning("Morning pipeline was triggered on a weekend user_id=%s", user_id)

        logger.info("Morning pipeline step 1/2 started user_id=%s", user_id)
        step_1_2_started = perf_counter()
        signal_task = AgentTask(
            agent_name="signal_hunter",
            user_id=user_id,
            input_data={"action": "scan", "pipeline": "morning", "user_id": user_id},
        )
        chart_task = AgentTask(
            agent_name="chart_whisperer",
            user_id=user_id,
            input_data={
                "action": "scan_breakouts",
                "period": "3mo",
                "interval": "1d",
                "pipeline": "morning",
                "user_id": user_id,
            },
        )
        signal_result, chart_result = await asyncio.gather(
            self._dispatch_with_timeout("signal_hunter", signal_task, timeout_seconds=34.0),
            self._dispatch_with_timeout("chart_whisperer", chart_task, timeout_seconds=34.0),
            return_exceptions=False,
        )
        logger.info(
            "Morning pipeline step 1/2 completed in %.3fs signal_status=%s chart_status=%s",
            perf_counter() - step_1_2_started,
            signal_result.status,
            chart_result.status,
        )

        top_opportunities = await self._fetch_top_signals(limit=5)

        logger.info("Morning pipeline step 3 started user_id=%s", user_id)
        step_3_started = perf_counter()
        video_task = AgentTask(
            agent_name="video_studio",
            user_id=user_id,
            input_data={
                "action": "get_frames_only",
                "user_id": user_id,
                "signals": top_opportunities,
                "pipeline": "morning",
            },
        )
        video_result = await self._dispatch_with_timeout("video_studio", video_task, timeout_seconds=12.0)
        logger.info(
            "Morning pipeline step 3 completed in %.3fs video_status=%s",
            perf_counter() - step_3_started,
            video_result.status,
        )

        logger.info("Morning pipeline step 4 started user_id=%s", user_id)
        step_4_started = perf_counter()
        summary_task = AgentTask(
            agent_name="market_gpt",
            user_id=user_id,
            input_data={"action": "summarize", "user_id": user_id, "pipeline": "morning"},
        )
        summary_result = await self._dispatch_with_timeout("market_gpt", summary_task, timeout_seconds=10.0)
        logger.info(
            "Morning pipeline step 4 completed in %.3fs summary_status=%s",
            perf_counter() - step_4_started,
            summary_result.status,
        )

        execution_time_seconds = perf_counter() - pipeline_started_at

        signals_found = int((signal_result.output_data or {}).get("total_signals_found") or 0)
        breakouts_found = int((chart_result.output_data or {}).get("count") or 0)
        video_frames = len((video_result.output_data or {}).get("frames") or [])
        market_summary = str((summary_result.output_data or {}).get("answer") or "")

        morning_report = {
            "pipeline_run_at": datetime.utcnow().isoformat(),
            "signals_found": signals_found,
            "breakouts_found": breakouts_found,
            "video_frames": video_frames,
            "market_summary": market_summary,
            "top_opportunities": top_opportunities,
            "execution_time_seconds": round(execution_time_seconds, 3),
        }

        await self._save_daily_report(user_id=user_id, report=morning_report)

        if execution_time_seconds > 60.0:
            logger.warning("Morning pipeline exceeded 60 seconds user_id=%s duration=%.3fs", user_id, execution_time_seconds)

        return morning_report

    async def get_portfolio_intelligence(self, user_id: str) -> dict:
        started_at = perf_counter()

        latest_portfolio = await self._get_latest_portfolio(user_id)
        portfolio_health = self._build_portfolio_health(latest_portfolio)

        personalized_signals_task = AgentTask(
            agent_name="signal_hunter",
            user_id=user_id,
            input_data={"action": "get_signals", "user_id": user_id, "limit": 10},
        )
        personalized_signals_result = await self.dispatch("signal_hunter", personalized_signals_task)
        personalized_signals = (personalized_signals_result.output_data or {}).get("signals") or []

        holdings = self._extract_top_holdings_symbols(latest_portfolio)
        if not holdings:
            holdings = [str(item.get("symbol") or "").upper() for item in personalized_signals[:3] if item.get("symbol")]
        holdings = [symbol for symbol in holdings if symbol][:3]

        insight_tasks = [
            AgentTask(
                agent_name="market_gpt",
                user_id=user_id,
                input_data={"action": "analyze_stock", "symbol": symbol, "user_id": user_id},
            )
            for symbol in holdings
        ]

        insights: list[AgentTask] = []
        if insight_tasks:
            insights = list(await asyncio.gather(*[self.dispatch("market_gpt", task) for task in insight_tasks]))

        ai_insight_parts: list[str] = []
        for insight in insights:
            if insight.status == "completed":
                ai_insight_parts.append(str((insight.output_data or {}).get("answer") or ""))

        if not ai_insight_parts:
            ai_insight_parts.append("AI insights are temporarily unavailable. Please retry shortly.")

        recommended_actions = self._build_recommended_actions(latest_portfolio, personalized_signals, holdings)

        return {
            "portfolio_health": portfolio_health,
            "personalized_signals": personalized_signals,
            "ai_insights": "\n\n".join(ai_insight_parts),
            "recommended_actions": recommended_actions,
            "execution_time_seconds": round(perf_counter() - started_at, 3),
        }

    async def analyze_stock_complete(self, symbol: str, user_id: str) -> dict:
        clean_symbol = symbol.upper().strip()
        started_at = perf_counter()

        chart_task = AgentTask(
            agent_name="chart_whisperer",
            user_id=user_id,
            input_data={
                "action": "analyze",
                "symbol": clean_symbol,
                "period": "6mo",
                "interval": "1d",
                "include_chart": False,
                "user_id": user_id,
            },
        )
        market_task = AgentTask(
            agent_name="market_gpt",
            user_id=user_id,
            input_data={"action": "analyze_stock", "symbol": clean_symbol, "user_id": user_id},
        )

        chart_result, market_result = await asyncio.gather(
            self._dispatch_with_timeout("chart_whisperer", chart_task, timeout_seconds=25.0),
            self._dispatch_with_timeout("market_gpt", market_task, timeout_seconds=25.0),
        )

        technical_analysis = (chart_result.output_data or {}) if chart_result.status == "completed" else {}
        ai_analysis = str((market_result.output_data or {}).get("answer") or "")
        if not ai_analysis:
            ai_analysis = "AI analysis is temporarily unavailable."

        technical_signal = str(technical_analysis.get("overall_signal") or "NEUTRAL").upper()
        combined_signal = self._combine_signal(technical_signal, ai_analysis)

        chart_confidence = float(technical_analysis.get("confidence") or 0.0)
        ai_confidence = float((market_result.output_data or {}).get("confidence") or 0.0)
        confidence = round((chart_confidence + ai_confidence) / 2 if (chart_confidence or ai_confidence) else 0.0, 3)

        return {
            "symbol": clean_symbol,
            "technical_analysis": technical_analysis,
            "ai_analysis": ai_analysis,
            "combined_signal": combined_signal,
            "confidence": confidence,
            "execution_time_seconds": round(perf_counter() - started_at, 3),
        }

    async def get_system_status(self) -> dict:
        started_at = perf_counter()

        checks = [agent.health_check() for agent in self.agents.values()]
        agent_health = list(await asyncio.gather(*checks)) if checks else []

        supabase_status, last_pipeline_run_at, total_signals, total_conversations = await asyncio.gather(
            self._get_supabase_status(),
            self._get_last_pipeline_run_time(),
            self._get_table_count("market_signals"),
            self._get_table_count("conversations"),
        )

        return {
            "checked_at": datetime.utcnow().isoformat(),
            "agents": agent_health,
            "supabase": {"status": supabase_status},
            "last_morning_pipeline_run_at": last_pipeline_run_at,
            "total_signals": total_signals,
            "total_conversations": total_conversations,
            "system_status": "healthy" if supabase_status == "healthy" else "degraded",
            "execution_time_seconds": round(perf_counter() - started_at, 3),
        }

    async def get_all_agent_health(self) -> list[dict]:
        checks = [agent.health_check() for agent in self.agents.values()]
        if not checks:
            return []
        return list(await asyncio.gather(*checks))

    async def get_pipeline_history(self, limit: int = 7) -> list[dict[str, Any]]:
        def _op() -> list[dict[str, Any]]:
            client = get_supabase()
            response = client.table("daily_reports").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data or []

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to fetch pipeline history error=%s", exc)
            return []

    async def _fetch_top_signals(self, limit: int = 5) -> list[dict[str, Any]]:
        def _op() -> list[dict[str, Any]]:
            client = get_supabase()
            response = (
                client.table("market_signals")
                .select("symbol, signal_type, opportunity_score, data, created_at")
                .order("opportunity_score", desc=True)
                .limit(limit)
                .execute()
            )
            rows = response.data or []
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = row.get("data") or {}
                out.append(
                    {
                        "symbol": row.get("symbol"),
                        "signal_type": row.get("signal_type"),
                        "opportunity_score": row.get("opportunity_score"),
                        "category": payload.get("category"),
                        "explanation": payload.get("explanation"),
                        "created_at": row.get("created_at"),
                    }
                )
            return out

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to fetch top signals error=%s", exc)
            return []

    async def _save_daily_report(self, user_id: str, report: dict[str, Any]) -> None:
        def _op() -> None:
            client = get_supabase()
            client.table("daily_reports").insert(
                {
                    "user_id": user_id,
                    "signals_found": int(report.get("signals_found") or 0),
                    "breakouts_found": int(report.get("breakouts_found") or 0),
                    "video_frames": int(report.get("video_frames") or 0),
                    "market_summary": str(report.get("market_summary") or ""),
                    "top_opportunities": report.get("top_opportunities") or [],
                    "execution_time_seconds": float(report.get("execution_time_seconds") or 0.0),
                }
            ).execute()

        try:
            await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to save daily report user_id=%s error=%s", user_id, exc)

    async def _get_latest_portfolio(self, user_id: str) -> dict[str, Any] | None:
        def _op() -> dict[str, Any] | None:
            client = get_supabase()
            response = client.table("portfolios").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if not response.data:
                return None
            return response.data[0]

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to fetch latest portfolio user_id=%s error=%s", user_id, exc)
            return None

    def _build_portfolio_health(self, portfolio_row: dict[str, Any] | None) -> dict[str, Any]:
        if not portfolio_row:
            return {
                "status": "unavailable",
                "overall_score": 0,
                "overall_xirr": 0.0,
                "last_updated": None,
            }

        raw_data = portfolio_row.get("raw_data") or {}
        xirr_results = raw_data.get("xirr_results") or {}
        return {
            "status": "available",
            "overall_score": raw_data.get("overall_score", 0),
            "overall_xirr": xirr_results.get("overall_xirr", portfolio_row.get("xirr", 0.0)),
            "last_updated": portfolio_row.get("created_at"),
            "benchmark": (raw_data.get("benchmark_analysis") or {}).get("benchmark"),
            "tax_efficiency": (raw_data.get("tax_analysis") or {}).get("tax_efficiency_score"),
        }

    def _extract_top_holdings_symbols(self, portfolio_row: dict[str, Any] | None) -> list[str]:
        if not portfolio_row:
            return []

        raw_data = portfolio_row.get("raw_data") or {}
        parsed_statement = raw_data.get("parsed_statement") or {}
        funds = parsed_statement.get("funds") or []

        symbols: list[str] = []
        for fund in funds:
            maybe_symbol = str(fund.get("symbol") or fund.get("ticker") or "").upper().strip()
            if maybe_symbol and maybe_symbol.isalnum() and len(maybe_symbol) <= 15:
                symbols.append(maybe_symbol)

        deduped: list[str] = []
        for symbol in symbols:
            if symbol not in deduped:
                deduped.append(symbol)
        return deduped[:5]

    def _build_recommended_actions(
        self,
        portfolio_row: dict[str, Any] | None,
        personalized_signals: list[dict[str, Any]],
        holdings: list[str],
    ) -> list[str]:
        actions: list[str] = []
        if not portfolio_row:
            actions.append("Upload your latest portfolio statement to unlock deeper recommendations.")
        else:
            rebalancing = ((portfolio_row.get("raw_data") or {}).get("rebalancing_plan") or {}).get("actions") or []
            for item in rebalancing[:3]:
                if isinstance(item, str) and item.strip():
                    actions.append(item.strip())

        high_priority = [s for s in personalized_signals if float(s.get("opportunity_score") or 0.0) >= 80]
        if high_priority:
            symbols = [str(s.get("symbol") or "") for s in high_priority[:3] if s.get("symbol")]
            if symbols:
                actions.append(f"Review high-priority personalized signals for: {', '.join(symbols)}.")

        if holdings:
            actions.append(f"Track news and technical trend changes for top holdings: {', '.join(holdings)}.")

        if not actions:
            actions.append("No urgent actions identified; continue disciplined SIP and periodic review.")

        return actions[:5]

    def _combine_signal(self, technical_signal: str, ai_analysis: str) -> str:
        ai_text = (ai_analysis or "").lower()
        bearish_terms = ["strong sell", "avoid", "downside", "bearish", "negative"]
        bullish_terms = ["strong buy", "accumulate", "upside", "bullish", "positive"]

        ai_bias = "NEUTRAL"
        if any(term in ai_text for term in bearish_terms):
            ai_bias = "SELL"
        elif any(term in ai_text for term in bullish_terms):
            ai_bias = "BUY"

        if technical_signal == "STRONG_BUY" and ai_bias == "BUY":
            return "STRONG_BUY"
        if technical_signal == "STRONG_SELL" and ai_bias == "SELL":
            return "STRONG_SELL"
        if technical_signal in {"BUY", "STRONG_BUY"} and ai_bias != "SELL":
            return "BUY"
        if technical_signal in {"SELL", "STRONG_SELL"} and ai_bias != "BUY":
            return "SELL"
        return "NEUTRAL"

    async def _get_supabase_status(self) -> str:
        def _op() -> str:
            client = get_supabase()
            client.table("users").select("id").limit(1).execute()
            return "healthy"

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Supabase health check failed error=%s", exc)
            return "unhealthy"

    async def _get_last_pipeline_run_time(self) -> str | None:
        def _op() -> str | None:
            client = get_supabase()
            response = client.table("daily_reports").select("created_at").order("created_at", desc=True).limit(1).execute()
            if not response.data:
                return None
            return response.data[0].get("created_at")

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to fetch last pipeline run time error=%s", exc)
            return None

    async def _get_table_count(self, table_name: str) -> int:
        def _op() -> int:
            client = get_supabase()
            response = client.table(table_name).select("id", count="exact").limit(1).execute()
            return int(response.count or 0)

        try:
            return await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Failed to fetch count table=%s error=%s", table_name, exc)
            return 0

    async def _dispatch_with_timeout(self, agent_name: str, task: AgentTask, timeout_seconds: float) -> AgentTask:
        try:
            return await asyncio.wait_for(self.dispatch(agent_name, task), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "Agent dispatch timed out agent=%s timeout_seconds=%.1f task_id=%s",
                agent_name,
                timeout_seconds,
                task.task_id,
            )
            task.status = "failed"
            task.error_message = f"Timed out after {timeout_seconds:.1f}s"
            task.completed_at = datetime.utcnow()
            return task
        except Exception as exc:
            logger.exception("Agent dispatch failed agent=%s task_id=%s error=%s", agent_name, task.task_id, exc)
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            return task
