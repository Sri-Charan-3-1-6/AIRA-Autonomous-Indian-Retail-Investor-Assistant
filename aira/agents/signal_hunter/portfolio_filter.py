"""AIRA module: agents/signal_hunter/portfolio_filter.py"""

import asyncio
from typing import Any


def _infer_sector(symbol: str) -> str:
    symbol_upper = symbol.upper()
    mapping = {
        "INFY": "IT",
        "TCS": "IT",
        "HCLTECH": "IT",
        "HDFCBANK": "Banking",
        "ICICIBANK": "Banking",
        "SBIN": "Banking",
        "SUNPHARMA": "Pharma",
        "DRREDDY": "Pharma",
        "TATAMOTORS": "Auto",
        "MARUTI": "Auto",
        "RELIANCE": "Energy",
        "ONGC": "Energy",
        "HINDUNILVR": "FMCG",
        "ITC": "FMCG",
        "TATASTEEL": "Metals",
        "JSWSTEEL": "Metals",
        "DLF": "Realty",
    }
    return mapping.get(symbol_upper, "Unknown")


def filter_signals_by_portfolio(signals: list[dict[str, Any]], user_portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    held_symbols = {str(s).upper() for s in user_portfolio.get("symbols", [])}
    held_sectors = {str(s) for s in user_portfolio.get("sectors", [])}
    risk_profile = str(user_portfolio.get("risk_profile") or "moderate").lower()

    ranked: list[dict[str, Any]] = []

    for signal in signals:
        symbol = str(signal.get("symbol") or "").upper()
        sector = str(signal.get("sector") or _infer_sector(symbol))
        category = str(signal.get("category") or "NEUTRAL")
        base_score = float(signal.get("opportunity_score") or signal.get("score") or 0.0)

        relevance = 0.0
        reasons: list[str] = []

        if symbol in held_symbols:
            relevance += 20.0
            reasons.append("existing holding")

        if sector in held_sectors and sector != "Unknown":
            relevance += 10.0
            reasons.append("sector familiarity")

        if sector not in held_sectors and sector != "Unknown":
            relevance += 5.0
            reasons.append("diversification")

        if risk_profile == "conservative" and category in {"STRONG_BUY", "BUY"}:
            if base_score < 70:
                relevance -= 10.0
                reasons.append("risk-profile mismatch")
        elif risk_profile == "aggressive" and category in {"AVOID", "NEUTRAL"}:
            relevance -= 10.0
            reasons.append("risk-profile mismatch")

        final_score = round(base_score + relevance, 2)
        enriched = dict(signal)
        enriched["sector"] = sector
        enriched["relevance_adjustment"] = round(relevance, 2)
        enriched["relevance_reasons"] = reasons
        enriched["final_score"] = final_score
        ranked.append(enriched)

    ranked.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    return ranked[:10]


async def get_user_portfolio_context(user_id: str, supabase_client) -> dict[str, Any]:
    def _op() -> dict[str, Any]:
        response = (
            supabase_client.table("portfolios")
            .select("raw_data, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return {
                "symbols": [],
                "sectors": [],
                "risk_profile": "moderate",
                "total_value": 0.0,
            }

        row = response.data[0]
        raw_data = row.get("raw_data") or {}
        parsed = raw_data.get("parsed_statement") or {}
        funds = parsed.get("funds") or []

        symbols: set[str] = set()
        sectors: set[str] = set()
        total_value = 0.0

        for fund in funds:
            holdings = fund.get("holdings") or []
            fund_value = float(fund.get("current_value") or 0.0)
            total_value += fund_value

            for holding in holdings:
                symbol = str(holding.get("symbol") or "").upper().strip()
                if symbol:
                    symbols.add(symbol)
                    sectors.add(_infer_sector(symbol))

            fallback_symbol = str(fund.get("symbol") or "").upper().strip()
            if fallback_symbol:
                symbols.add(fallback_symbol)
                sectors.add(_infer_sector(fallback_symbol))

        user_response = (
            supabase_client.table("users")
            .select("risk_profile")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        risk_profile = "moderate"
        if user_response.data:
            risk_profile = str(user_response.data[0].get("risk_profile") or "moderate")

        sectors.discard("Unknown")
        return {
            "symbols": sorted(symbols),
            "sectors": sorted(sectors),
            "risk_profile": risk_profile,
            "total_value": round(total_value, 2),
        }

    return await asyncio.to_thread(_op)
