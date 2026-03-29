"""AIRA module: agents/portfolio_doctor/analyzer.py"""

from datetime import datetime
from typing import Any

EXPENSE_RATIOS = {
    "Mirae Asset Large Cap Fund Direct": 0.54,
    "HDFC Top 100 Fund Direct": 0.59,
    "Axis Bluechip Fund Direct": 0.61,
    "Parag Parikh Flexi Cap Fund Direct": 0.63,
    "Quant Active Fund Direct": 0.58,
    "SBI Bluechip Fund Direct": 0.57,
    "ICICI Prudential Bluechip Fund Direct": 0.55,
    "Kotak Emerging Equity Fund Direct": 0.52,
    "Nippon India Small Cap Fund Direct": 0.68,
    "Mirae Asset Emerging Bluechip Fund Direct": 0.66,
    "Mirae Asset Large Cap Fund Regular": 1.54,
    "HDFC Top 100 Fund Regular": 1.59,
    "Axis Bluechip Fund Regular": 1.61,
    "SBI Bluechip Fund Regular": 1.57,
    "ICICI Prudential Bluechip Fund Regular": 1.55,
    "default_equity": 1.05,
    "default_debt": 0.45,
    "default_elss": 1.10,
}


def _match_expense_ratio(fund_name: str) -> float:
    lower_name = fund_name.lower()
    for key, value in EXPENSE_RATIOS.items():
        if key.startswith("default_"):
            continue
        if key.lower() in lower_name or lower_name in key.lower():
            return value

    if "debt" in lower_name:
        return EXPENSE_RATIOS["default_debt"]
    if "elss" in lower_name or "tax" in lower_name:
        return EXPENSE_RATIOS["default_elss"]
    return EXPENSE_RATIOS["default_equity"]


def calculate_expense_drag(funds: list[dict[str, Any]], investment_horizon_years: int = 10) -> dict[str, Any]:
    total_corpus = 0.0
    annual_expense_cost = 0.0
    ten_year_expense_drag = 0.0
    potential_savings_switching_to_direct = 0.0
    funds_with_high_expense: list[dict[str, Any]] = []

    gross_expected_return = 0.12

    for fund in funds:
        fund_name = str(fund.get("fund_name", "Unknown Fund"))
        current_value = float(fund.get("current_value", 0.0))
        expense_ratio = _match_expense_ratio(fund_name)

        total_corpus += current_value
        annual_expense_cost += current_value * (expense_ratio / 100.0)

        without_expense = current_value * ((1 + gross_expected_return) ** investment_horizon_years)
        with_expense = current_value * ((1 + max(-0.95, gross_expected_return - (expense_ratio / 100.0))) ** investment_horizon_years)
        ten_year_expense_drag += max(0.0, without_expense - with_expense)

        suggestion = "Keep as is"
        if expense_ratio > 1.0:
            suggestion = "Consider switching to lower-cost direct plan"
            funds_with_high_expense.append(
                {
                    "fund_name": fund_name,
                    "expense_ratio": expense_ratio,
                    "suggestion": suggestion,
                }
            )

        if "regular" in fund_name.lower():
            direct_name = fund_name.lower().replace("regular", "direct")
            direct_ratio = None
            for key, value in EXPENSE_RATIOS.items():
                if key.lower() == direct_name:
                    direct_ratio = value
                    break
            if direct_ratio is not None and expense_ratio > direct_ratio:
                potential_savings_switching_to_direct += current_value * ((expense_ratio - direct_ratio) / 100.0)

    return {
        "total_corpus": round(total_corpus, 2),
        "annual_expense_cost": round(annual_expense_cost, 2),
        "ten_year_expense_drag": round(ten_year_expense_drag, 2),
        "funds_with_high_expense": funds_with_high_expense,
        "potential_savings_switching_to_direct": round(potential_savings_switching_to_direct, 2),
    }


def compare_to_benchmark(portfolio_xirr: float, time_period_years: int) -> dict[str, Any]:
    benchmark_map = {1: 0.142, 3: 0.156, 5: 0.148, 10: 0.132}

    if time_period_years not in benchmark_map:
        closest_period = min(benchmark_map.keys(), key=lambda k: abs(k - time_period_years))
    else:
        closest_period = time_period_years

    benchmark_return = benchmark_map[closest_period]
    alpha = portfolio_xirr - benchmark_return

    if alpha > 0.01:
        label = "Outperforming"
    elif alpha < -0.01:
        label = "Underperforming"
    else:
        label = "Inline"

    return {
        "portfolio_xirr": float(portfolio_xirr),
        "benchmark_return": float(benchmark_return),
        "alpha": float(alpha),
        "performance_label": label,
        "benchmark_name": "Nifty 50 TRI",
    }


def _parse_date(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def analyze_tax_implications(funds: list[dict[str, Any]]) -> dict[str, Any]:
    ltcg_amount = 0.0
    stcg_amount = 0.0
    debt_taxable_gain = 0.0
    now = datetime.utcnow()

    for fund in funds:
        name = str(fund.get("fund_name", ""))
        is_debt = "debt" in name.lower()

        purchases = fund.get("purchase_transactions", [])
        redemptions = fund.get("redemption_transactions", [])

        invested = sum(abs(float(tx.get("amount", 0.0))) for tx in purchases)
        redeemed = sum(abs(float(tx.get("amount", 0.0))) for tx in redemptions)
        current_value = float(fund.get("current_value", 0.0))

        gross_gain = max(0.0, current_value + redeemed - invested)

        if purchases:
            oldest_purchase = min(_parse_date(tx.get("date")) for tx in purchases)
            holding_days = (now - oldest_purchase).days
        else:
            holding_days = 0

        if is_debt:
            debt_taxable_gain += gross_gain
        else:
            if holding_days > 365:
                ltcg_amount += gross_gain
            else:
                stcg_amount += gross_gain

    ltcg_tax = max(0.0, ltcg_amount - 125000.0) * 0.125
    stcg_tax = stcg_amount * 0.20
    debt_tax = debt_taxable_gain * 0.30
    estimated_tax = ltcg_tax + stcg_tax + debt_tax

    suggestions: list[str] = []
    if stcg_amount > 0:
        suggestions.append("Delay equity redemptions beyond 1 year where possible to reduce STCG tax.")
    if ltcg_amount > 125000:
        suggestions.append("Use staggered redemptions across financial years to optimize LTCG exemption.")
    if debt_taxable_gain > 0:
        suggestions.append("Evaluate debt fund exits against your income slab impact before booking gains.")
    if not suggestions:
        suggestions.append("Current portfolio appears tax-efficient under assumed holding periods.")

    return {
        "ltcg_amount": round(ltcg_amount, 2),
        "stcg_amount": round(stcg_amount, 2),
        "estimated_tax": round(estimated_tax, 2),
        "tax_efficient_exit_suggestions": suggestions,
    }
