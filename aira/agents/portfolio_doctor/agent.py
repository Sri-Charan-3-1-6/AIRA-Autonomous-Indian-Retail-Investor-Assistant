"""AIRA module: agents/portfolio_doctor/agent.py"""

import asyncio
import base64
import logging
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from agents.portfolio_doctor.analyzer import (
    analyze_tax_implications,
    calculate_expense_drag,
    compare_to_benchmark,
)
from agents.portfolio_doctor.excel_parser import parse_generic_csv, parse_kfintech_excel
from agents.portfolio_doctor.overlap import analyze_portfolio_overlap
from agents.portfolio_doctor.pdf_parser import parse_cams_pdf
from agents.portfolio_doctor.recommender import generate_rebalancing_plan
from agents.portfolio_doctor.xirr import calculate_portfolio_xirr
from core.gemini_client import get_gemini_client
from core.supabase_client import get_supabase
from db import crud
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)


class PortfolioDoctorAgent(BaseAgent):
    agent_name = "portfolio_doctor"
    agent_version = "2.0.0"

    async def _save_portfolio_analysis(self, user_id: str, analysis: dict[str, Any], overall_xirr: float) -> None:
        def _op() -> None:
            client = get_supabase()
            client.table("portfolios").insert(
                {
                    "user_id": user_id,
                    "raw_data": analysis,
                    "xirr": overall_xirr,
                }
            ).execute()

        await asyncio.to_thread(_op)

    async def run(self, task: AgentTask) -> AgentTask:
        logger.info("PortfolioDoctorAgent started task_id=%s", task.task_id)
        task.status = "running"
        try:
            input_data = task.input_data or {}
            encoded_file = str(input_data.get("file_bytes_base64", "")).strip()
            file_type = str(input_data.get("file_type", "")).lower().strip()
            user_id = str(input_data.get("user_id") or task.user_id)
            investment_horizon_years = int(input_data.get("investment_horizon_years", 10))

            if not encoded_file:
                raise ValueError("Missing file_bytes_base64 in input_data")
            if file_type not in {"pdf", "excel", "csv"}:
                raise ValueError("file_type must be one of: pdf, excel, csv")

            logger.info("Step 1: decoding base64 file payload")
            file_bytes = base64.b64decode(encoded_file)

            logger.info("Step 2: parsing statement file_type=%s", file_type)
            if file_type == "pdf":
                parsed_data = parse_cams_pdf(file_bytes)
            elif file_type == "excel":
                parsed_data = parse_kfintech_excel(file_bytes)
            else:
                parsed_data = parse_generic_csv(file_bytes)

            funds = parsed_data.get("funds", [])
            fund_names = [str(fund.get("fund_name", "Unknown Fund")) for fund in funds]

            logger.info("Step 3: calculating XIRR")
            xirr_results = calculate_portfolio_xirr(funds)

            logger.info("Step 4: analyzing fund overlap")
            overlap_analysis = analyze_portfolio_overlap(fund_names)

            logger.info("Step 5: calculating expense drag")
            expense_analysis = calculate_expense_drag(funds, investment_horizon_years=investment_horizon_years)

            logger.info("Step 6: benchmark comparison")
            benchmark_analysis = compare_to_benchmark(
                portfolio_xirr=float(xirr_results.get("overall_xirr", 0.0)),
                time_period_years=investment_horizon_years,
            )

            logger.info("Step 7: tax analysis")
            tax_analysis = analyze_tax_implications(funds)

            portfolio_analysis = {
                "parsed_statement": parsed_data,
                "xirr_results": xirr_results,
                "overlap_analysis": overlap_analysis,
                "expense_analysis": expense_analysis,
                "benchmark_analysis": benchmark_analysis,
                "tax_analysis": tax_analysis,
                "investment_horizon_years": investment_horizon_years,
            }

            logger.info("Step 8: generating Gemini-powered recommendations")
            gemini_client = get_gemini_client()
            rebalancing_plan = await generate_rebalancing_plan(portfolio_analysis, gemini_client)

            complete_analysis = {
                **portfolio_analysis,
                "rebalancing_plan": rebalancing_plan,
                "overall_score": rebalancing_plan.get("overall_score", 55),
                "generated_at": datetime.utcnow().isoformat(),
            }

            logger.info("Step 9: saving portfolio analysis to Supabase")
            await self._save_portfolio_analysis(
                user_id=user_id,
                analysis=complete_analysis,
                overall_xirr=float(xirr_results.get("overall_xirr", 0.0)),
            )

            task.output_data = complete_analysis
            task.status = "completed"
            task.confidence_score = 0.85
            task.completed_at = datetime.utcnow()

            logger.info("Step 10: writing audit log")
            await self.log_to_audit(task, crud)

            logger.info("PortfolioDoctorAgent completed task_id=%s", task.task_id)
            return task
        except Exception as exc:
            logger.exception("PortfolioDoctorAgent failed task_id=%s: %s", task.task_id, exc)
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
            "phase": "phase_2",
            "capabilities": [
                "cams_pdf_parsing",
                "kfintech_excel_parsing",
                "xirr_calculation",
                "overlap_detection",
                "expense_analysis",
                "benchmark_comparison",
                "tax_analysis",
                "ai_recommendations",
            ],
        }
