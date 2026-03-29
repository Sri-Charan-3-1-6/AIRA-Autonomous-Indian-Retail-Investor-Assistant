"""AIRA module: agents/portfolio_doctor/xirr.py"""

from datetime import date, datetime
from typing import Any


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return datetime.utcnow().date()


def _xnpv(rate: float, cashflows: list[tuple[date, float]]) -> float:
    if not cashflows:
        return 0.0
    t0 = cashflows[0][0]
    return sum(amount / ((1.0 + rate) ** (((dt - t0).days) / 365.0)) for dt, amount in cashflows)


def _xnpv_derivative(rate: float, cashflows: list[tuple[date, float]]) -> float:
    if not cashflows:
        return 0.0
    t0 = cashflows[0][0]
    derivative = 0.0
    for dt, amount in cashflows:
        year_frac = ((dt - t0).days) / 365.0
        derivative -= (year_frac * amount) / ((1.0 + rate) ** (year_frac + 1.0))
    return derivative


def calculate_xirr(transactions: list[dict[str, Any]], current_value: float, current_date: str | date | datetime) -> float:
    if not transactions:
        return 0.0

    cashflows: list[tuple[date, float]] = []
    for tx in transactions:
        amount = float(tx.get("amount", 0.0))
        if amount == 0.0:
            continue
        cashflows.append((_to_date(tx.get("date")), amount))

    if current_value > 0:
        cashflows.append((_to_date(current_date), float(current_value)))

    if len(cashflows) < 2:
        return 0.0

    cashflows.sort(key=lambda x: x[0])
    if all(dt == cashflows[0][0] for dt, _ in cashflows):
        return 0.0

    has_inflow = any(amount > 0 for _, amount in cashflows)
    has_outflow = any(amount < 0 for _, amount in cashflows)
    if not (has_inflow and has_outflow):
        return 0.0

    rate = 0.1
    tolerance = 1e-6
    max_iterations = 1000

    for _ in range(max_iterations):
        try:
            f_val = _xnpv(rate, cashflows)
            f_der = _xnpv_derivative(rate, cashflows)
            if abs(f_der) < 1e-12:
                break
            new_rate = rate - (f_val / f_der)
            if new_rate <= -0.9999:
                new_rate = -0.9999
            if abs(new_rate - rate) < tolerance:
                return float(new_rate)
            rate = new_rate
        except Exception:
            return 0.0

    return float(rate) if rate == rate else 0.0


def calculate_portfolio_xirr(funds: list[dict[str, Any]]) -> dict[str, Any]:
    fund_xirrs: dict[str, float] = {}
    overall_transactions: list[dict[str, Any]] = []
    total_current_value = 0.0
    current_date = datetime.utcnow().date()

    for fund in funds:
        fund_name = str(fund.get("fund_name", "Unknown Fund"))
        txs: list[dict[str, Any]] = []

        for purchase in fund.get("purchase_transactions", []):
            amount = abs(float(purchase.get("amount", 0.0)))
            txs.append({"date": purchase.get("date"), "amount": -amount})
            overall_transactions.append({"date": purchase.get("date"), "amount": -amount})

        for redemption in fund.get("redemption_transactions", []):
            amount = abs(float(redemption.get("amount", 0.0)))
            txs.append({"date": redemption.get("date"), "amount": amount})
            overall_transactions.append({"date": redemption.get("date"), "amount": amount})

        fund_current_value = float(fund.get("current_value", 0.0))
        total_current_value += fund_current_value

        fund_xirrs[fund_name] = calculate_xirr(txs, fund_current_value, current_date)

    overall_xirr = calculate_xirr(overall_transactions, total_current_value, current_date)

    if fund_xirrs:
        best_performer = max(fund_xirrs, key=fund_xirrs.get)
        worst_performer = min(fund_xirrs, key=fund_xirrs.get)
    else:
        best_performer = "N/A"
        worst_performer = "N/A"

    return {
        "overall_xirr": float(overall_xirr),
        "fund_xirrs": fund_xirrs,
        "best_performer": best_performer,
        "worst_performer": worst_performer,
    }
