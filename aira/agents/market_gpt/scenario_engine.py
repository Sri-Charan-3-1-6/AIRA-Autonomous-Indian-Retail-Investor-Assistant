"""AIRA module: agents/market_gpt/scenario_engine.py"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SECTOR_MAPPINGS: dict[str, list[str]] = {
    "IT": ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM"],
    "BANKING": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN"],
    "PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB"],
    "AUTO": ["MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "HEROMOTOCO"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA"],
    "ENERGY": ["RELIANCE", "ONGC", "BPCL", "POWERGRID", "NTPC"],
}


def _extract_funds(portfolio_data: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = portfolio_data.get("parsed_statement") or {}
    funds = parsed.get("funds") or portfolio_data.get("funds") or []
    if not isinstance(funds, list):
        return []
    return [f for f in funds if isinstance(f, dict)]


def _fund_value(fund: dict[str, Any]) -> float:
    return float(fund.get("current_value") or fund.get("value") or fund.get("market_value") or 0.0)


def _fund_name(fund: dict[str, Any]) -> str:
    return str(fund.get("fund_name") or fund.get("name") or "Unknown Fund")


def _estimate_sector_overlap(fund: dict[str, Any], sector_symbols: list[str]) -> float:
    text_blobs: list[str] = [_fund_name(fund).upper()]

    holdings = fund.get("holdings") or []
    if isinstance(holdings, list):
        for holding in holdings:
            if isinstance(holding, dict):
                text_blobs.append(str(holding.get("symbol") or "").upper())
                text_blobs.append(str(holding.get("name") or "").upper())
            else:
                text_blobs.append(str(holding).upper())

    merged = " ".join(text_blobs)
    hits = sum(1 for symbol in sector_symbols if symbol in merged)

    if hits == 0:
        if "INDEX" in merged or "NIFTY" in merged or "LARGE CAP" in merged:
            return 0.08
        if "FLEXI" in merged or "MULTI" in merged:
            return 0.12
        if "SECTOR" in merged:
            return 0.20
        return 0.03

    overlap = min(0.6, 0.08 + hits * 0.1)
    return round(overlap, 4)


def _recommendation_from_impact(impact_pct: float) -> str:
    if impact_pct >= 8:
        return "EXIT"
    if impact_pct >= 3:
        return "REDUCE"
    return "HOLD"


def simulate_sector_drop(portfolio_data: dict, sector: str, drop_percentage: float) -> dict[str, Any]:
    sector_key = str(sector or "").upper().strip()
    sector_symbols = SECTOR_MAPPINGS.get(sector_key)
    if not sector_symbols:
        raise ValueError(f"Unsupported sector '{sector}'. Allowed: {', '.join(SECTOR_MAPPINGS.keys())}")

    funds = _extract_funds(portfolio_data)
    total_value = sum(_fund_value(fund) for fund in funds)

    affected_funds: list[dict[str, Any]] = []
    total_impact_inr = 0.0

    for fund in funds:
        value = _fund_value(fund)
        if value <= 0:
            continue

        overlap = _estimate_sector_overlap(fund, sector_symbols)
        fund_impact_pct = max(0.0, float(drop_percentage)) * overlap
        fund_impact_inr = value * (fund_impact_pct / 100.0)
        total_impact_inr += fund_impact_inr

        affected_funds.append(
            {
                "fund_name": _fund_name(fund),
                "estimated_impact_pct": round(fund_impact_pct, 2),
                "reason": (
                    f"Estimated {overlap * 100:.1f}% exposure to {sector_key} "
                    f"stocks ({', '.join(sector_symbols[:3])}...)."
                ),
                "recommendation": _recommendation_from_impact(fund_impact_pct),
            }
        )

    total_impact_pct = (total_impact_inr / total_value * 100.0) if total_value > 0 else 0.0

    return {
        "sector": sector_key,
        "drop_percentage": round(float(drop_percentage), 2),
        "total_portfolio_impact_pct": round(total_impact_pct, 2),
        "total_portfolio_impact_inr": round(total_impact_inr, 2),
        "affected_funds": affected_funds,
    }


def _is_debt_fund(fund: dict[str, Any]) -> bool:
    name = _fund_name(fund).lower()
    return any(keyword in name for keyword in ["debt", "gilt", "liquid", "bond", "income"])


def simulate_market_crash(portfolio_data: dict, crash_percentage: float) -> dict[str, Any]:
    funds = _extract_funds(portfolio_data)
    total_value = sum(_fund_value(fund) for fund in funds)

    affected_funds: list[dict[str, Any]] = []
    total_impact_inr = 0.0

    crash = max(0.0, float(crash_percentage))

    for fund in funds:
        value = _fund_value(fund)
        if value <= 0:
            continue

        if _is_debt_fund(fund):
            fund_impact_pct = crash * 0.20
            reason = "Debt fund assumed to move at 20% of equity drawdown."
        else:
            beta = float(fund.get("beta") or 1.0)
            fund_impact_pct = crash * beta
            reason = f"Equity fund with beta {beta:.2f} to broad market." 

        fund_impact_inr = value * (fund_impact_pct / 100.0)
        total_impact_inr += fund_impact_inr

        affected_funds.append(
            {
                "fund_name": _fund_name(fund),
                "estimated_impact_pct": round(fund_impact_pct, 2),
                "reason": reason,
                "recommendation": _recommendation_from_impact(fund_impact_pct),
            }
        )

    total_impact_pct = (total_impact_inr / total_value * 100.0) if total_value > 0 else 0.0

    return {
        "scenario": "Market Crash",
        "crash_percentage": round(crash, 2),
        "total_portfolio_impact_pct": round(total_impact_pct, 2),
        "total_portfolio_impact_inr": round(total_impact_inr, 2),
        "affected_funds": affected_funds,
    }


def simulate_interest_rate_change(portfolio_data: dict, rate_change_bps: int) -> dict[str, Any]:
    funds = _extract_funds(portfolio_data)
    total_value = sum(_fund_value(fund) for fund in funds)

    hike = rate_change_bps > 0
    magnitude = abs(rate_change_bps) / 100.0

    debt_impact_pct = (-0.35 * magnitude) if hike else (0.25 * magnitude)
    banking_impact_pct = (-0.22 * magnitude) if hike else (0.18 * magnitude)
    real_estate_impact_pct = (-0.10 * magnitude) if hike else (0.30 * magnitude)

    portfolio_impact_inr = 0.0
    affected_asset_classes: list[dict[str, Any]] = []

    debt_value = 0.0
    banking_exposed_value = 0.0
    real_estate_exposed_value = 0.0

    for fund in funds:
        value = _fund_value(fund)
        name = _fund_name(fund).upper()

        if _is_debt_fund(fund):
            debt_value += value
        if any(bank in name for bank in ["BANK", "HDFC", "ICICI", "AXIS", "SBI", "KOTAK"]):
            banking_exposed_value += value * 0.25
        if any(tag in name for tag in ["REAL ESTATE", "REALTY", "HOUSING"]):
            real_estate_exposed_value += value * 0.4

    debt_impact_inr = debt_value * (debt_impact_pct / 100.0)
    banking_impact_inr = banking_exposed_value * (banking_impact_pct / 100.0)
    real_estate_impact_inr = real_estate_exposed_value * (real_estate_impact_pct / 100.0)

    portfolio_impact_inr += debt_impact_inr + banking_impact_inr + real_estate_impact_inr

    if debt_value > 0:
        affected_asset_classes.append(
            {
                "asset_class": "Debt Funds",
                "estimated_impact_pct": round(debt_impact_pct, 2),
                "estimated_impact_inr": round(debt_impact_inr, 2),
            }
        )
    if banking_exposed_value > 0:
        affected_asset_classes.append(
            {
                "asset_class": "Banking Exposure",
                "estimated_impact_pct": round(banking_impact_pct, 2),
                "estimated_impact_inr": round(banking_impact_inr, 2),
            }
        )
    if real_estate_exposed_value > 0:
        affected_asset_classes.append(
            {
                "asset_class": "Real Estate Exposure",
                "estimated_impact_pct": round(real_estate_impact_pct, 2),
                "estimated_impact_inr": round(real_estate_impact_inr, 2),
            }
        )

    portfolio_impact_pct = (portfolio_impact_inr / total_value * 100.0) if total_value > 0 else 0.0

    direction = "hike" if hike else "cut"
    return {
        "rate_change_bps": int(rate_change_bps),
        "scenario_description": f"RBI rate {direction} of {abs(rate_change_bps)} bps",
        "affected_asset_classes": affected_asset_classes,
        "portfolio_impact": {
            "total_portfolio_impact_pct": round(portfolio_impact_pct, 2),
            "total_portfolio_impact_inr": round(portfolio_impact_inr, 2),
        },
    }


async def simulate_custom_scenario(portfolio_data: dict, scenario_description: str, gemini_client) -> dict[str, Any]:
    prompt = (
        "You are a portfolio risk analyst for Indian retail investors. "
        "Given the portfolio data and custom market scenario, return a JSON object with keys: "
        "scenario, impact_summary, estimated_portfolio_impact_pct, top_risks (list), opportunities (list), "
        "recommended_actions (list), confidence (0 to 1).\n\n"
        f"Scenario: {scenario_description}\n\n"
        f"Portfolio Data: {json.dumps(portfolio_data, ensure_ascii=True)}"
    )

    try:
        response = await gemini_client.generate_text(prompt)
        text = response.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])

        return {
            "scenario": scenario_description,
            "impact_summary": text,
            "estimated_portfolio_impact_pct": None,
            "top_risks": [],
            "opportunities": [],
            "recommended_actions": [],
            "confidence": 0.6,
        }
    except Exception as exc:
        logger.exception("Custom scenario simulation failed error=%s", exc)
        return {
            "scenario": scenario_description,
            "impact_summary": "Unable to compute a structured custom scenario impact at this time.",
            "estimated_portfolio_impact_pct": None,
            "top_risks": ["Model reasoning unavailable"],
            "opportunities": [],
            "recommended_actions": ["Review diversification and keep position sizing conservative."],
            "confidence": 0.4,
        }
