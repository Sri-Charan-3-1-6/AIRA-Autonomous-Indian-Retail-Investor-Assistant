"""AIRA module: agents/signal_hunter/opportunity_scorer.py"""

from typing import Any


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _score_insider(signal: dict[str, Any]) -> float:
    insider = signal.get("insider") or {}
    buy_count = float(insider.get("buy_count") or insider.get("num_insiders") or 0)
    net_value = float(insider.get("net_value") or insider.get("total_buy_value") or 0.0)
    score = min(12.0, buy_count * 3.0) + min(13.0, net_value / 100000000.0 * 4.0)
    return _clamp(score, 0.0, 25.0)


def _score_bulk(signal: dict[str, Any]) -> float:
    bulk = signal.get("bulk_deal") or {}
    if str(bulk.get("deal_type") or "").upper() != "BUY":
        return 0.0
    quantity = float(bulk.get("quantity") or 0)
    price = float(bulk.get("price") or 0)
    value = quantity * price
    institution_bonus = 5.0 if bulk.get("client_name") else 0.0
    score = min(15.0, value / 100000000.0 * 2.0) + institution_bonus
    return _clamp(score, 0.0, 20.0)


def _score_fii(signal: dict[str, Any]) -> float:
    fii = signal.get("fii_dii") or {}
    fii_net = float(fii.get("fii_net") or 0.0)
    streak = float(fii.get("consecutive_fii_buying_days") or 0)
    score = min(10.0, max(0.0, fii_net) / 500.0 * 2.0) + min(5.0, streak)
    return _clamp(score, 0.0, 15.0)


def _score_announcement(signal: dict[str, Any]) -> float:
    text = str((signal.get("announcement") or {}).get("subject") or "").lower()
    positive_terms = ["order", "expansion", "dividend", "acquisition", "contract", "growth"]
    negative_terms = ["penalty", "regulatory", "fraud", "default", "litigation", "resignation"]

    score = 6.0
    score += sum(4.0 for term in positive_terms if term in text)
    score -= sum(5.0 for term in negative_terms if term in text)
    return _clamp(score, 0.0, 20.0)


def _score_momentum(signal: dict[str, Any]) -> float:
    quote = signal.get("quote") or {}
    change_percent = float(quote.get("change_percent") or 0.0)
    if change_percent <= 0:
        return 0.0
    return _clamp(change_percent * 1.5, 0.0, 10.0)


def _score_volume(signal: dict[str, Any]) -> float:
    volume_surge = float(signal.get("volume_surge_percent") or 100.0)
    if volume_surge >= 200:
        return 10.0
    if volume_surge <= 100:
        return 0.0
    return _clamp((volume_surge - 100.0) / 10.0, 0.0, 10.0)


def score_opportunity(signal: dict[str, Any]) -> float:
    insider_score = _score_insider(signal)
    bulk_score = _score_bulk(signal)
    fii_score = _score_fii(signal)
    announcement_score = _score_announcement(signal)
    momentum_score = _score_momentum(signal)
    volume_score = _score_volume(signal)

    total = insider_score + bulk_score + fii_score + announcement_score + momentum_score + volume_score
    return round(_clamp(total, 0.0, 100.0), 2)


def categorize_signal(score: float) -> str:
    if score > 80:
        return "STRONG_BUY"
    if score > 65:
        return "BUY"
    if score > 45:
        return "WATCH"
    if score > 30:
        return "NEUTRAL"
    return "AVOID"


def generate_signal_explanation(signal: dict[str, Any], score: float) -> str:
    factors: list[tuple[str, float]] = [
        ("insider activity", _score_insider(signal)),
        ("bulk deals", _score_bulk(signal)),
        ("FII flow", _score_fii(signal)),
        ("corporate announcement", _score_announcement(signal)),
        ("technical momentum", _score_momentum(signal)),
        ("volume surge", _score_volume(signal)),
    ]

    top_factors = sorted(factors, key=lambda item: item[1], reverse=True)[:3]
    rendered = ", ".join([f"{name} (+{value:.1f})" for name, value in top_factors])
    symbol = str(signal.get("symbol") or "this stock")

    return (
        f"{symbol} scored {score:.1f}/100 primarily due to {rendered}. "
        "Lower-impact factors were weighted but contributed less to conviction."
    )
