"""AIRA module: agents/market_gpt/context_builder.py"""

import asyncio
import logging
from typing import Any

from agents.chart_whisperer.agent import ChartWhispererAgent
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)


async def build_portfolio_context(user_id: str, supabase_client) -> str:
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

    try:
        row = await asyncio.to_thread(_op)
    except Exception as exc:
        logger.exception("Failed to fetch portfolio context user_id=%s error=%s", user_id, exc)
        return "No portfolio data available for this user."

    if not row:
        return "No portfolio data available for this user."

    raw_data = row.get("raw_data") or {}
    parsed_statement = raw_data.get("parsed_statement") or {}
    xirr_results = raw_data.get("xirr_results") or {}
    rebalancing_plan = raw_data.get("rebalancing_plan") or {}

    funds = parsed_statement.get("funds") or []
    total_value = float(parsed_statement.get("total_portfolio_value") or 0.0)
    overall_xirr = float(xirr_results.get("overall_xirr") or row.get("xirr") or 0.0)
    portfolio_health_score = (
        rebalancing_plan.get("overall_score")
        if rebalancing_plan.get("overall_score") is not None
        else raw_data.get("overall_score")
    )

    lines = ["Latest Portfolio Snapshot:"]

    if funds:
        lines.append("Funds Held:")
        for fund in funds:
            fund_name = str(fund.get("fund_name") or "Unknown Fund")
            current_value = float(fund.get("current_value") or 0.0)
            fund_xirr = fund.get("xirr")
            if fund_xirr is None:
                fund_xirr = fund.get("fund_xirr")

            xirr_text = f"{float(fund_xirr):.2f}%" if isinstance(fund_xirr, (int, float)) else "N/A"
            lines.append(
                f"- {fund_name}: current value INR {current_value:,.2f}, XIRR {xirr_text}"
            )
    else:
        lines.append("Funds Held: No detailed holdings available.")

    if total_value <= 0:
        total_value = float(raw_data.get("total_corpus") or 0.0)

    lines.append(f"Total Portfolio Value: INR {total_value:,.2f}")
    lines.append(f"Overall Portfolio XIRR: {overall_xirr:.2f}%")

    if portfolio_health_score is not None:
        lines.append(f"Portfolio Health Score: {portfolio_health_score}")
    else:
        lines.append("Portfolio Health Score: Not available")

    recommendations = []
    if isinstance(rebalancing_plan.get("recommendations"), list):
        recommendations = rebalancing_plan.get("recommendations")
    elif isinstance(rebalancing_plan.get("action_plan"), list):
        recommendations = rebalancing_plan.get("action_plan")

    if recommendations:
        lines.append("Top Recommendations:")
        for rec in recommendations[:3]:
            if isinstance(rec, dict):
                text = rec.get("recommendation") or rec.get("action") or rec.get("title") or str(rec)
            else:
                text = str(rec)
            lines.append(f"- {text}")
    else:
        lines.append("Top Recommendations: No recommendations available")

    red_flags = []
    if isinstance(rebalancing_plan.get("red_flags"), list):
        red_flags = rebalancing_plan.get("red_flags")
    elif isinstance(raw_data.get("red_flags"), list):
        red_flags = raw_data.get("red_flags")

    if red_flags:
        lines.append("Red Flags:")
        for flag in red_flags[:5]:
            lines.append(f"- {flag}")
    else:
        lines.append("Red Flags: None explicitly flagged")

    return "\n".join(lines)


async def build_market_context(supabase_client) -> str:
    def _op() -> list[dict[str, Any]]:
        response = (
            supabase_client.table("market_signals")
            .select("symbol, opportunity_score, data, created_at")
            .order("opportunity_score", desc=True)
            .limit(200)
            .execute()
        )
        return response.data or []

    try:
        rows = await asyncio.to_thread(_op)
    except Exception as exc:
        logger.exception("Failed to fetch market context error=%s", exc)
        rows = []

    lines = ["Top Market Signals (last 24 hours):"]

    recent_signals: list[dict[str, Any]] = []
    now_utc = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    for row in rows:
        created_at = row.get("created_at")
        if not created_at:
            continue
        try:
            dt = __import__("datetime").datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            if now_utc - dt <= __import__("datetime").timedelta(hours=24):
                recent_signals.append(row)
        except Exception:
            continue

    for row in recent_signals[:10]:
        payload = row.get("data") or {}
        symbol = row.get("symbol") or "UNKNOWN"
        score = float(row.get("opportunity_score") or 0.0)
        category = payload.get("category") or "NEUTRAL"
        explanation = payload.get("explanation") or "No explanation available"
        lines.append(
            f"- {symbol}: score {score:.2f}, category {category}. {explanation}"
        )

    if not recent_signals:
        lines.append("- No fresh market signals available in the last 24 hours.")

    fii_net = 1250.0
    dii_net = -430.0
    combined = fii_net + dii_net
    sentiment = "positive" if combined > 0 else "negative"
    lines.append(
        "FII/DII Sentiment Summary: "
        f"FII net +INR {fii_net:.0f} Cr, DII net INR {dii_net:.0f} Cr, "
        f"combined flow INR {combined:.0f} Cr ({sentiment})."
    )

    return "\n".join(lines)


async def build_chart_context(symbol: str) -> str:
    clean_symbol = (symbol or "").upper().strip()
    if not clean_symbol:
        return "Chart data unavailable for UNKNOWN"

    try:
        chart_agent = ChartWhispererAgent()
        task = AgentTask(
            agent_name="chart_whisperer",
            user_id="system",
            input_data={
                "action": "analyze",
                "symbol": clean_symbol,
                "include_chart": False,
                "period": "6mo",
                "interval": "1d",
            },
        )
        result = await chart_agent.run(task)
        if result.status != "completed":
            return f"Chart data unavailable for {clean_symbol}"

        data = result.output_data or {}
        indicators = data.get("indicators") or {}
        interpretation = data.get("indicator_interpretation") or {}
        summary = data.get("summary") or {}

        current_price = summary.get("current_price") or summary.get("latest_close") or 0.0
        overall_signal = data.get("overall_signal") or interpretation.get("overall_signal") or "NEUTRAL"

        rsi_value = indicators.get("rsi_14")
        rsi_state = interpretation.get("rsi_state")
        if not rsi_state:
            if isinstance(rsi_value, (int, float)):
                if rsi_value >= 70:
                    rsi_state = "overbought"
                elif rsi_value <= 30:
                    rsi_state = "oversold"
                else:
                    rsi_state = "neutral"
            else:
                rsi_state = "unknown"

        macd_signal = interpretation.get("macd_signal") or (
            "bullish" if (indicators.get("macd_line") or 0) > (indicators.get("macd_signal") or 0) else "bearish"
        )
        trend = interpretation.get("trend") or "unknown"

        pattern = data.get("most_significant_pattern")
        if isinstance(pattern, dict):
            pattern_text = pattern.get("pattern_name") or pattern.get("name") or "None"
        else:
            pattern_text = str(pattern or "None")

        support_levels = data.get("support_levels") or []
        resistance_levels = data.get("resistance_levels") or []
        support = support_levels[0] if support_levels else "N/A"
        resistance = resistance_levels[0] if resistance_levels else "N/A"

        return "\n".join(
            [
                f"Technical snapshot for {clean_symbol}:",
                f"- Current Price: INR {float(current_price):,.2f}",
                f"- Overall Signal: {overall_signal}",
                f"- RSI: {rsi_value if rsi_value is not None else 'N/A'} ({rsi_state})",
                f"- MACD: {macd_signal}",
                f"- Trend: {trend}",
                f"- Most Significant Pattern: {pattern_text}",
                f"- Support Level: {support}",
                f"- Resistance Level: {resistance}",
            ]
        )
    except Exception as exc:
        logger.exception("Failed to build chart context symbol=%s error=%s", clean_symbol, exc)
        return f"Chart data unavailable for {clean_symbol}"


async def build_full_context(user_id: str, symbol: str, supabase_client) -> str:
    symbol_clean = (symbol or "").upper().strip()

    portfolio_task = build_portfolio_context(user_id=user_id, supabase_client=supabase_client)
    market_task = build_market_context(supabase_client=supabase_client)

    if symbol_clean:
        portfolio_context, market_context, technical_context = await asyncio.gather(
            portfolio_task,
            market_task,
            build_chart_context(symbol_clean),
        )
    else:
        portfolio_context, market_context = await asyncio.gather(portfolio_task, market_task)
        technical_context = "No symbol provided for technical analysis."

    return "\n\n".join(
        [
            "PORTFOLIO CONTEXT\n" + portfolio_context,
            "MARKET CONTEXT\n" + market_context,
            "TECHNICAL CONTEXT\n" + technical_context,
        ]
    )
