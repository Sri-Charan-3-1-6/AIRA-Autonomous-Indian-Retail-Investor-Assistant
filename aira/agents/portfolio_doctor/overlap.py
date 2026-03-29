"""AIRA module: agents/portfolio_doctor/overlap.py"""

import difflib
import re
from itertools import combinations
from typing import Any

FUND_HOLDINGS = {
    "Mirae Asset Large Cap Fund": ["Reliance Industries", "HDFC Bank", "Infosys", "ICICI Bank", "TCS", "Axis Bank", "Kotak Mahindra Bank", "L&T", "HUL", "Bajaj Finance"],
    "HDFC Top 100 Fund": ["HDFC Bank", "ICICI Bank", "Reliance Industries", "Infosys", "TCS", "Axis Bank", "State Bank of India", "Kotak Mahindra Bank", "L&T", "ITC"],
    "SBI Bluechip Fund": ["HDFC Bank", "Reliance Industries", "Infosys", "ICICI Bank", "TCS", "Axis Bank", "HUL", "Bajaj Finance", "Maruti Suzuki", "Titan"],
    "Axis Bluechip Fund": ["HDFC Bank", "Infosys", "TCS", "ICICI Bank", "Reliance Industries", "Bajaj Finance", "HUL", "Asian Paints", "Kotak Mahindra Bank", "Avenue Supermarts"],
    "Parag Parikh Flexi Cap Fund": ["HDFC Bank", "Coal India", "ITC", "Bajaj Holdings", "HCL Technologies", "Power Grid", "Alphabet Inc", "Meta Platforms", "Microsoft", "Amazon"],
    "Nippon India Small Cap Fund": ["HDFC Bank", "Dixon Technologies", "Tube Investments", "Karur Vysya Bank", "Apar Industries", "KPIT Technologies", "Bharat Electronics", "Persistent Systems", "Kaynes Technology", "Sansera Engineering"],
    "Quant Active Fund": ["Reliance Industries", "HDFC Bank", "ICICI Bank", "ITC", "Adani Enterprises", "SBI", "Adani Ports", "Sun Pharma", "Jio Financial", "BPCL"],
    "Kotak Emerging Equity Fund": ["Persistent Systems", "Carborundum Universal", "Schaeffler India", "Kajaria Ceramics", "Astral", "Cera Sanitaryware", "Sona BLW Precision", "Blue Star", "Grindwell Norton", "Sundaram Finance"],
    "ICICI Prudential Bluechip Fund": ["HDFC Bank", "Reliance Industries", "ICICI Bank", "Infosys", "TCS", "Larsen and Toubro", "Axis Bank", "Sun Pharma", "Maruti Suzuki", "NTPC"],
    "DSP Midcap Fund": ["Persistent Systems", "The Ramco Cements", "Coforge", "Max Healthcare", "Astral", "Sundaram Finance", "Kajaria Ceramics", "Voltas", "PI Industries", "Crompton Greaves"],
    "Franklin India Prima Fund": ["Cholamandalam Investment", "Persistent Systems", "Coforge", "Max Healthcare", "Astral Poly", "Kajaria Ceramics", "Carborundum Universal", "Schaeffler India", "Sundaram Finance", "Sona BLW"],
    "UTI Flexi Cap Fund": ["HDFC Bank", "Infosys", "ICICI Bank", "Reliance Industries", "Axis Bank", "Bajaj Finance", "TCS", "HUL", "Kotak Mahindra Bank", "Maruti Suzuki"],
    "Canara Robeco Bluechip Equity Fund": ["HDFC Bank", "Infosys", "Reliance Industries", "ICICI Bank", "TCS", "Axis Bank", "HUL", "Bajaj Finance", "Larsen and Toubro", "Asian Paints"],
    "Motilal Oswal Midcap Fund": ["Coforge", "Persistent Systems", "Kalyan Jewellers", "Polycab India", "Zomato", "Trent", "Tube Investments", "Jio Financial Services", "Mankind Pharma", "Dixon Technologies"],
    "HDFC Midcap Opportunities Fund": ["Cholamandalam Investment", "Max Healthcare", "Persistent Systems", "Indian Hotels", "Balkrishna Industries", "Crompton Greaves", "Coforge", "Sundaram Finance", "Voltas", "Tube Investments"],
    "Tata Small Cap Fund": ["Neuland Laboratories", "Kaynes Technology", "Garware Technical Fibres", "Capacite Infraprojects", "Suven Pharmaceuticals", "KPIT Technologies", "Jyothy Labs", "Birlasoft", "TD Power Systems", "Craftsman Automation"],
    "Bandhan Small Cap Fund": ["Apar Industries", "Kaynes Technology", "Neuland Laboratories", "Dixon Technologies", "Sansera Engineering", "Elgi Equipments", "PTC Industries", "Garware Technical Fibres", "KPIT Technologies", "Suven Pharmaceuticals"],
    "Mirae Asset Emerging Bluechip Fund": ["HDFC Bank", "ICICI Bank", "Reliance Industries", "Axis Bank", "Persistent Systems", "Coforge", "Cholamandalam Investment", "Max Healthcare", "Indian Hotels", "Carborundum Universal"],
    "SBI Small Cap Fund": ["Garware Technical Fibres", "Blue Star", "Elgi Equipments", "Hawkins Cookers", "Neuland Laboratories", "Sansera Engineering", "Kaynes Technology", "Craftsman Automation", "Carborundum Universal", "PTC Industries"],
    "Quant Small Cap Fund": ["Reliance Industries", "ITC", "HDFC Bank", "Adani Enterprises", "Jio Financial Services", "BPCL", "SBI", "ICICI Bank", "Adani Ports", "Sun Pharma"],
}


def _normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    cleaned = re.sub(r"\b(direct|regular|growth|plan)\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _resolve_fund_name(name: str) -> str | None:
    if name in FUND_HOLDINGS:
        return name

    key_map = {_normalize_name(k): k for k in FUND_HOLDINGS}
    normalized = _normalize_name(name)

    if normalized in key_map:
        return key_map[normalized]

    matches = difflib.get_close_matches(normalized, key_map.keys(), n=1, cutoff=0.55)
    if matches:
        return key_map[matches[0]]
    return None


def calculate_overlap(fund1_name: str, fund2_name: str) -> float:
    fund1 = _resolve_fund_name(fund1_name)
    fund2 = _resolve_fund_name(fund2_name)

    if not fund1 or not fund2:
        return 0.0

    set1 = set(FUND_HOLDINGS[fund1])
    set2 = set(FUND_HOLDINGS[fund2])

    if not set1 and not set2:
        return 0.0

    overlap = len(set1.intersection(set2)) / len(set1.union(set2))
    return round(overlap * 100.0, 2)


def analyze_portfolio_overlap(funds: list[str]) -> dict[str, Any]:
    overlap_matrix: dict[str, dict[str, float]] = {fund: {} for fund in funds}
    high_overlap_pairs: list[dict[str, Any]] = []
    redundancy_counter: dict[str, int] = {fund: 0 for fund in funds}
    pair_values: list[float] = []

    for fund in funds:
        overlap_matrix[fund][fund] = 100.0

    for fund1, fund2 in combinations(funds, 2):
        pct = calculate_overlap(fund1, fund2)
        overlap_matrix[fund1][fund2] = pct
        overlap_matrix[fund2][fund1] = pct
        pair_values.append(pct)

        if pct > 40.0:
            high_overlap_pairs.append({"fund1": fund1, "fund2": fund2, "overlap_pct": pct})
            redundancy_counter[fund1] += 1
            redundancy_counter[fund2] += 1

    redundant_funds = [fund for fund, count in redundancy_counter.items() if count > 0]
    avg_pair_overlap = sum(pair_values) / len(pair_values) if pair_values else 0.0
    diversification_score = max(0.0, min(100.0, round(100.0 - avg_pair_overlap, 2)))

    return {
        "overlap_matrix": overlap_matrix,
        "high_overlap_pairs": high_overlap_pairs,
        "redundant_funds": redundant_funds,
        "diversification_score": diversification_score,
    }
