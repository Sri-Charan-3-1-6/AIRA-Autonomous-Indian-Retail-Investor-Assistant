"""AIRA module: agents/portfolio_doctor/excel_parser.py"""

import io
import logging
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _parse_indian_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    text = text.replace(",", "").replace("Rs.", "").replace("INR", "")
    text = text.replace("(", "-").replace(")", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _pick_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {col.lower().strip(): col for col in columns}
    for cand in candidates:
        for key, original in normalized.items():
            if cand in key:
                return original
    return None


def _normalize_date(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return datetime.utcnow().date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def _build_fund_rows(df: pd.DataFrame, parse_method: str) -> dict[str, Any]:
    columns = list(df.columns)
    fund_col = _pick_column(columns, ["fund name", "scheme", "scheme name", "fund"])
    units_col = _pick_column(columns, ["units", "balance units"]) 
    nav_col = _pick_column(columns, ["nav"]) 
    value_col = _pick_column(columns, ["current value", "market value", "value", "amount"]) 
    folio_col = _pick_column(columns, ["folio"]) 
    isin_col = _pick_column(columns, ["isin"]) 
    purchase_date_col = _pick_column(columns, ["purchase date", "transaction date", "date"]) 
    amount_col = _pick_column(columns, ["amount", "invested amount", "purchase amount"]) 

    if not fund_col:
        raise ValueError("Could not detect fund name column")

    grouped: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        fund_name = str(row.get(fund_col, "")).strip()
        if not fund_name:
            continue

        folio_number = str(row.get(folio_col, "N/A")).strip() if folio_col else "N/A"
        key = f"{fund_name}|{folio_number}"

        if key not in grouped:
            grouped[key] = {
                "fund_name": fund_name,
                "folio_number": folio_number,
                "isin": str(row.get(isin_col, "N/A")).strip() if isin_col else "N/A",
                "units_held": 0.0,
                "nav": 0.0,
                "current_value": 0.0,
                "purchase_transactions": [],
                "redemption_transactions": [],
                "redeemed": False,
            }

        fund = grouped[key]
        fund["units_held"] = _parse_indian_number(row.get(units_col)) if units_col else fund["units_held"]
        fund["nav"] = _parse_indian_number(row.get(nav_col)) if nav_col else fund["nav"]
        fund["current_value"] = _parse_indian_number(row.get(value_col)) if value_col else fund["current_value"]

        tx_date = _normalize_date(row.get(purchase_date_col)) if purchase_date_col else datetime.utcnow().date().isoformat()
        tx_amount = _parse_indian_number(row.get(amount_col)) if amount_col else fund["current_value"]
        tx_nav = fund["nav"]
        tx_units = fund["units_held"]

        if tx_amount > 0:
            fund["purchase_transactions"].append(
                {
                    "date": tx_date,
                    "units": tx_units,
                    "amount": tx_amount,
                    "nav": tx_nav,
                    "transaction_type": "purchase",
                }
            )

        fund["redeemed"] = fund["units_held"] <= 0.0

    funds = list(grouped.values())
    total_current_value = float(sum(item.get("current_value", 0.0) for item in funds))

    return {
        "investor_name": "Unknown Investor",
        "pan": "N/A",
        "statement_date": datetime.utcnow().date().isoformat(),
        "funds": funds,
        "total_current_value": total_current_value,
        "parse_method": parse_method,
    }


def parse_generic_csv(file_bytes: bytes) -> dict[str, Any]:
    df = pd.read_csv(io.BytesIO(file_bytes))
    return _build_fund_rows(df, parse_method="generic_csv")


def parse_kfintech_excel(file_bytes: bytes) -> dict[str, Any]:
    if not file_bytes:
        raise ValueError("Empty file content")

    if not file_bytes.startswith(b"PK"):
        try:
            return parse_generic_csv(file_bytes)
        except Exception:
            logger.info("Input is not an XLSX zip and generic CSV parse failed")

    xls = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")

    best_sheet = None
    best_score = -1
    for sheet_name in xls.sheet_names:
        sheet_df = xls.parse(sheet_name)
        cols = [str(c).lower() for c in sheet_df.columns]
        score = 0
        for token in ("fund", "scheme", "units", "nav", "value"):
            if any(token in col for col in cols):
                score += 1
        if score > best_score:
            best_score = score
            best_sheet = sheet_name

    if best_sheet is None:
        raise ValueError("Could not detect portfolio data sheet")

    df = xls.parse(best_sheet)
    return _build_fund_rows(df, parse_method="kfintech_excel")
