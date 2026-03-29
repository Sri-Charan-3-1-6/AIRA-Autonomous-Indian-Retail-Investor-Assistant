"""AIRA module: api/audit.py"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from core.supabase_client import get_supabase
from db import crud
from models.audit import AuditLog, AuditStats, ComplianceReport

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@router.get("/logs")
async def get_audit_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str | None = Query(default=None),
    agent_name: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict:
    logger.info(
        "Fetching audit logs page=%s limit=%s user_id=%s agent_name=%s",
        page,
        limit,
        user_id,
        agent_name,
    )

    client = get_supabase()

    all_logs = await asyncio.to_thread(
        crud.get_audit_logs,
        client,
        user_id,
        None,
        agent_name,
        start_date,
        end_date,
    )

    total = len(all_logs)
    offset = (page - 1) * limit
    page_logs = all_logs[offset : offset + limit]

    return {
        "logs": page_logs,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/stats", response_model=AuditStats)
async def get_audit_stats() -> AuditStats:
    logger.info("Fetching audit statistics")
    client = get_supabase()
    stats = await asyncio.to_thread(crud.get_audit_stats, client)
    return AuditStats(**stats)


@router.get("/decision/{task_id}", response_model=AuditLog)
async def get_decision_trail(task_id: str) -> AuditLog:
    logger.info("Fetching audit decision trail for task_id=%s", task_id)
    client = get_supabase()
    row = await asyncio.to_thread(crud.get_agent_decision_trail, client, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Audit trail not found for task_id")
    return AuditLog(**row)


@router.get("/compliance-report", response_model=ComplianceReport)
async def get_compliance_report() -> ComplianceReport:
    logger.info("Generating compliance report")
    client = get_supabase()

    logs = await asyncio.to_thread(crud.get_audit_logs, client)
    total_decisions = len(logs)

    high_confidence_count = sum(1 for row in logs if _to_float(row.get("confidence_score")) > 0.7)
    confidence_above_0_7_percentage = (high_confidence_count / total_decisions * 100.0) if total_decisions else 0.0

    # Lightweight compliance heuristic: treat records as data-driven unless output includes direct-advice phrases.
    direct_advice_markers = (
        "buy now",
        "sell now",
        "guaranteed return",
        "certain profit",
        "risk free",
    )
    data_driven_not_direct_advice = True

    marketgpt_total = 0
    marketgpt_with_disclaimer = 0

    for row in logs:
        output_data = row.get("output_data") or {}
        output_text = json.dumps(output_data, default=str).lower()

        if any(marker in output_text for marker in direct_advice_markers):
            data_driven_not_direct_advice = False

        if str(row.get("agent_name") or "").lower() == "market_gpt":
            marketgpt_total += 1
            disclaimer = output_data.get("disclaimer") if isinstance(output_data, dict) else None
            answer_text = str(output_data.get("answer") or "") if isinstance(output_data, dict) else ""
            if disclaimer or "does not constitute financial advice" in answer_text.lower():
                marketgpt_with_disclaimer += 1

    marketgpt_disclaimer_present_in_all = (
        marketgpt_with_disclaimer == marketgpt_total if marketgpt_total > 0 else True
    )

    return ComplianceReport(
        total_ai_decisions=total_decisions,
        confidence_above_0_7_percentage=confidence_above_0_7_percentage,
        data_driven_not_direct_advice=data_driven_not_direct_advice,
        marketgpt_disclaimer_present_in_all=marketgpt_disclaimer_present_in_all,
        marketgpt_total_responses=marketgpt_total,
        marketgpt_responses_with_disclaimer=marketgpt_with_disclaimer,
        generated_at=datetime.now(timezone.utc),
    )
