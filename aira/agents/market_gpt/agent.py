"""AIRA module: agents/market_gpt/agent.py"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from agents.market_gpt import article_fetcher, context_builder, conversation_store, response_formatter, scenario_engine
from core.gemini_client import get_gemini_client
from core.supabase_client import get_supabase
from db import crud
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are MarketGPT Pro, an AI-powered market analyst for Indian retail investors built by AIRA. "
    "You have access to real-time portfolio data, market signals, technical analysis, and financial news. "
    "Always respond in clear simple English that a retail investor can understand. "
    "Never give direct buy or sell advice — instead provide data-driven insights and let the investor decide. "
    "Always cite your sources when making claims. "
    "When discussing Indian stocks use NSE symbols. "
    "Format numbers in Indian style using lakhs and crores. "
    "Be concise but thorough. "
    "If you are uncertain about something say so clearly."
)


class MarketGPTAgent(BaseAgent):
    agent_name = "market_gpt"
    agent_version = "2.0.0"

    def _build_prompt(self, user_prompt: str) -> str:
        return f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\n{user_prompt.strip()}"

    async def _generate_with_fallback(self, prompt: str, fallback: str) -> str:
        gemini_client = get_gemini_client()
        try:
            return await gemini_client.generate_text(self._build_prompt(prompt))
        except Exception as exc:
            logger.exception(
                "Groq generation failed in MarketGPT fallback_triggered=true prompt_len=%d error_type=%s error=%s",
                len(prompt or ""),
                type(exc).__name__,
                exc,
            )
            return fallback

    async def _fetch_latest_portfolio(self, user_id: str, supabase_client) -> dict[str, Any] | None:
        def _op() -> dict[str, Any] | None:
            response = (
                supabase_client.table("portfolios")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None
            return response.data[0]

        return await asyncio.to_thread(_op)

    async def _handle_ask(self, task: AgentTask, supabase_client) -> dict[str, Any]:
        input_data = task.input_data or {}
        user_id = str(input_data.get("user_id") or task.user_id)
        question = str(input_data.get("question") or "").strip()
        if not question:
            raise ValueError("question is required for action=ask")

        symbol = str(input_data.get("symbol") or "").upper().strip()
        include_portfolio_context = bool(input_data.get("include_portfolio_context", True))
        session_id = str(input_data.get("session_id") or "").strip()

        logger.info("MarketGPT ask started user_id=%s session_id=%s", user_id, session_id or "new")

        if not session_id:
            session_id = await conversation_store.create_session(user_id=user_id, supabase_client=supabase_client)

        history = await conversation_store.get_recent_history(
            session_id=session_id,
            max_messages=10,
            supabase_client=supabase_client,
        )

        if include_portfolio_context:
            full_context = await context_builder.build_full_context(
                user_id=user_id,
                symbol=symbol,
                supabase_client=supabase_client,
            )
        else:
            market_context = await context_builder.build_market_context(supabase_client=supabase_client)
            technical_context = await context_builder.build_chart_context(symbol) if symbol else "No symbol provided."
            full_context = "\n\n".join(
                [
                    "PORTFOLIO CONTEXT\nSkipped by request.",
                    "MARKET CONTEXT\n" + market_context,
                    "TECHNICAL CONTEXT\n" + technical_context,
                ]
            )

        news_context = await article_fetcher.build_news_context(query=question)
        sources = ["Supabase portfolios", "Supabase market_signals", "ET Markets"]

        conversation_text = "\n".join([f"{item['role']}: {item['content']}" for item in history])
        prompt = (
            "User Question:\n"
            f"{question}\n\n"
            "Conversation History (recent):\n"
            f"{conversation_text or 'No prior conversation.'}\n\n"
            "Portfolio and Market Context:\n"
            f"{full_context}\n\n"
            "News Context:\n"
            f"{news_context}\n\n"
            "Respond with clear explanation, mention uncertainty if needed, and cite sources in-line."
        )

        raw = await self._generate_with_fallback(
            prompt=prompt,
            fallback=(
                "I am unable to generate a detailed answer right now. "
                "Please retry in a minute while I refresh market context."
            ),
        )

        await conversation_store.add_message(
            session_id=session_id,
            role="user",
            content=question,
            supabase_client=supabase_client,
        )
        await conversation_store.add_message(
            session_id=session_id,
            role="assistant",
            content=raw,
            supabase_client=supabase_client,
        )

        formatted = response_formatter.format_response(raw, sources=sources, query_type="conversational")
        final = response_formatter.add_disclaimer(formatted)

        return {
            "session_id": session_id,
            "answer": final,
            "sources": sources,
            "disclaimer": final.split("\n\n")[-1],
            "query_type": "conversational",
            "confidence": 0.82,
        }

    async def _handle_scenario(self, task: AgentTask, supabase_client) -> dict[str, Any]:
        input_data = task.input_data or {}
        user_id = str(input_data.get("user_id") or task.user_id)
        scenario_type = str(input_data.get("scenario_type") or "").strip().lower()
        scenario_params = input_data.get("scenario_params") or {}

        if not scenario_type:
            raise ValueError("scenario_type is required for action=scenario")

        latest_portfolio = await self._fetch_latest_portfolio(user_id=user_id, supabase_client=supabase_client)
        if not latest_portfolio:
            raise ValueError("No portfolio found for this user. Upload portfolio first.")

        portfolio_data = latest_portfolio.get("raw_data") or {}

        if scenario_type == "sector_drop":
            simulation = scenario_engine.simulate_sector_drop(
                portfolio_data=portfolio_data,
                sector=str(scenario_params.get("sector") or "IT"),
                drop_percentage=float(scenario_params.get("drop_percentage") or 10.0),
            )
        elif scenario_type == "market_crash":
            simulation = scenario_engine.simulate_market_crash(
                portfolio_data=portfolio_data,
                crash_percentage=float(scenario_params.get("crash_percentage") or 15.0),
            )
        elif scenario_type == "interest_rate":
            simulation = scenario_engine.simulate_interest_rate_change(
                portfolio_data=portfolio_data,
                rate_change_bps=int(scenario_params.get("rate_change_bps") or 25),
            )
        elif scenario_type == "custom":
            simulation = await scenario_engine.simulate_custom_scenario(
                portfolio_data=portfolio_data,
                scenario_description=str(scenario_params.get("scenario_description") or "Custom market event"),
                gemini_client=get_gemini_client(),
            )
        else:
            raise ValueError("scenario_type must be one of sector_drop, market_crash, interest_rate, custom")

        prompt = (
            "Explain this portfolio scenario simulation in plain English for an Indian retail investor. "
            "Give practical risk-management ideas without direct buy/sell advice.\n\n"
            f"Simulation Result:\n{json.dumps(simulation, ensure_ascii=True)}"
        )

        raw = await self._generate_with_fallback(
            prompt=prompt,
            fallback="I could not generate detailed commentary, but the simulation outputs are still valid.",
        )

        formatted = response_formatter.format_response(raw, sources=["Portfolio data", "Scenario engine"], query_type="scenario")
        final = response_formatter.add_disclaimer(formatted)

        return {
            "session_id": None,
            "answer": final,
            "sources": ["Portfolio data", "Scenario engine"],
            "disclaimer": final.split("\n\n")[-1],
            "query_type": "scenario",
            "confidence": 0.8,
            "simulation": simulation,
        }

    async def _handle_summarize(self, task: AgentTask, supabase_client) -> dict[str, Any]:
        headlines = await article_fetcher.fetch_et_markets_headlines()

        def _signals_op() -> list[dict[str, Any]]:
            response = (
                supabase_client.table("market_signals")
                .select("symbol, opportunity_score, data")
                .order("opportunity_score", desc=True)
                .limit(10)
                .execute()
            )
            return response.data or []

        signals = await asyncio.to_thread(_signals_op)

        prompt = (
            "Prepare a daily Indian market summary for a retail investor. Include:\n"
            "1) Market tone\n2) Key sectors in focus\n3) Top actionable watch-outs\n"
            "4) What this means for SIP and long-term investors.\n\n"
            f"Headlines: {json.dumps(headlines, ensure_ascii=True)}\n"
            f"Signals: {json.dumps(signals, ensure_ascii=True)}"
        )

        raw = await self._generate_with_fallback(
            prompt=prompt,
            fallback="Market summary is temporarily unavailable. Please retry shortly.",
        )

        formatted = response_formatter.format_response(raw, sources=["ET Markets", "Supabase market_signals"], query_type="analysis")
        final = response_formatter.add_disclaimer(formatted)

        return {
            "session_id": None,
            "answer": final,
            "sources": ["ET Markets", "Supabase market_signals"],
            "disclaimer": final.split("\n\n")[-1],
            "query_type": "analysis",
            "confidence": 0.79,
        }

    async def _handle_analyze_stock(self, task: AgentTask, supabase_client) -> dict[str, Any]:
        input_data = task.input_data or {}
        symbol = str(input_data.get("symbol") or "").upper().strip()
        if not symbol:
            raise ValueError("symbol is required for action=analyze_stock")

        user_id = str(input_data.get("user_id") or task.user_id or "system")
        chart_context = await context_builder.build_chart_context(symbol)
        news_context = await article_fetcher.search_market_news(query=symbol, symbols=[symbol])
        full_context = await context_builder.build_full_context(
            user_id=user_id,
            symbol=symbol,
            supabase_client=supabase_client,
        )

        prompt = (
            f"Provide comprehensive analysis for NSE symbol {symbol}.\n\n"
            f"Technical Context:\n{chart_context}\n\n"
            f"News Context:\n{news_context}\n\n"
            f"Additional User Context:\n{full_context}\n\n"
            "Return: technical view, sentiment view, risks, and investor-friendly assessment."
        )

        raw = await self._generate_with_fallback(
            prompt=prompt,
            fallback=f"Detailed stock analysis for {symbol} is currently unavailable.",
        )

        formatted = response_formatter.format_response(raw, sources=["ChartWhisperer", "ET Markets"], query_type="analysis")
        final = response_formatter.add_disclaimer(formatted)

        return {
            "session_id": None,
            "answer": final,
            "sources": ["ChartWhisperer", "ET Markets"],
            "disclaimer": final.split("\n\n")[-1],
            "query_type": "analysis",
            "confidence": 0.81,
            "symbol": symbol,
        }

    async def run(self, task: AgentTask) -> AgentTask:
        logger.info("MarketGPTAgent started task_id=%s", task.task_id)
        task.status = "running"

        try:
            input_data = task.input_data or {}
            action = str(input_data.get("action") or "ask").strip().lower()
            supabase_client = get_supabase()

            if action == "ask":
                task.output_data = await self._handle_ask(task, supabase_client=supabase_client)
            elif action == "scenario":
                task.output_data = await self._handle_scenario(task, supabase_client=supabase_client)
            elif action == "summarize":
                task.output_data = await self._handle_summarize(task, supabase_client=supabase_client)
            elif action == "analyze_stock":
                task.output_data = await self._handle_analyze_stock(task, supabase_client=supabase_client)
            else:
                raise ValueError("action must be one of: ask, scenario, summarize, analyze_stock")

            task.status = "completed"
            task.confidence_score = float(task.output_data.get("confidence", 0.8))
            task.completed_at = datetime.utcnow()

            await self.log_to_audit(task, crud)
            logger.info("MarketGPTAgent completed task_id=%s", task.task_id)
            return task
        except Exception as exc:
            logger.exception("MarketGPTAgent failed task_id=%s error=%s", task.task_id, exc)
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            task.output_data = {
                "session_id": str((task.input_data or {}).get("session_id") or "") or None,
                "answer": response_formatter.add_disclaimer(
                    "I could not process this request due to an internal error. Please try again."
                ),
                "sources": [],
                "disclaimer": (
                    "Disclaimer: This analysis is for informational purposes only and does not constitute financial advice. "
                    "Please consult a SEBI-registered financial advisor before making investment decisions."
                ),
                "query_type": "conversational",
                "confidence": 0.3,
            }
            await self.log_to_audit(task, crud)
            return task

    async def health_check(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": "healthy",
            "version": self.agent_version,
            "phase": "phase_5",
            "capabilities": [
                "portfolio_aware_conversation",
                "scenario_simulation",
                "native_rag_with_gemini_context",
                "multi_turn_memory",
                "stock_analysis",
                "daily_market_summary",
            ],
        }


class MarketGptAgent(MarketGPTAgent):
    pass
