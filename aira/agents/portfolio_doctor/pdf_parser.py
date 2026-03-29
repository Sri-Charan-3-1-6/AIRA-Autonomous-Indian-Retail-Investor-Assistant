"""AIRA module: agents/portfolio_doctor/pdf_parser.py"""

import io
import logging
import re
from datetime import datetime
from typing import Any

import pdfplumber

logger = logging.getLogger(__name__)

_DATE_PATTERNS = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y"]


def _parse_indian_number(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = value.replace(",", "").replace("Rs.", "").replace("INR", "").strip()
    cleaned = cleaned.replace("(", "-").replace(")", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date_str(value: str) -> str:
    value = value.strip()
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def extract_transactions(page_text: str) -> list[dict[str, Any]]:
    transactions: list[dict[str, Any]] = []
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]

    patterns = [
        re.compile(
            r"(?P<date>\d{2}(?:-[A-Za-z]{3}-\d{4}|/\d{2}/\d{4}))\s+"
            r"(?P<type>[A-Za-z /-]{3,60}?)\s+"
            r"(?P<units>-?[\d,]+(?:\.\d+)?)\s+"
            r"(?P<nav>[\d,]+(?:\.\d+)?)\s+"
            r"(?P<amount>-?[\d,]+(?:\.\d+)?)"
        ),
        re.compile(
            r"(?P<date>\d{2}(?:-[A-Za-z]{3}-\d{4}|/\d{2}/\d{4}))\s+"
            r"(?P<type>[A-Za-z /-]{3,60}?)\s+"
            r"(?P<amount>-?[\d,]+(?:\.\d+)?)\s+"
            r"(?P<nav>[\d,]+(?:\.\d+)?)\s+"
            r"(?P<units>-?[\d,]+(?:\.\d+)?)"
        ),
    ]

    for line in lines:
        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            tx_type = re.sub(r"\s+", " ", match.group("type")).strip()
            transactions.append(
                {
                    "date": _parse_date_str(match.group("date")),
                    "transaction_type": tx_type,
                    "units": _parse_indian_number(match.group("units")),
                    "nav": _parse_indian_number(match.group("nav")),
                    "amount": _parse_indian_number(match.group("amount")),
                }
            )
            break

    return transactions


def parse_cams_pdf(file_bytes: bytes) -> dict[str, Any]:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_texts = [page.extract_text() or "" for page in pdf.pages]

    full_text = "\n".join(page_texts)
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    investor_name = "Unknown Investor"
    pan = "N/A"
    statement_date = datetime.utcnow().date().isoformat()

    name_patterns = [
        re.compile(r"(?:Investor|Name)\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"Mr\.?|Mrs\.?|Ms\.?|Dr\.?", re.IGNORECASE),
    ]

    for line in lines[:40]:
        if pan == "N/A":
            pan_match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", line)
            if pan_match:
                pan = pan_match.group(0)

        if investor_name == "Unknown Investor":
            m = name_patterns[0].search(line)
            if m:
                investor_name = m.group(1).strip()

        date_match = re.search(
            r"(?:Statement\s*Date|As\s*on)\s*[:\-]?\s*(\d{2}(?:-[A-Za-z]{3}-\d{4}|/\d{2}/\d{4}|-\d{2}-\d{4}))",
            line,
            re.IGNORECASE,
        )
        if date_match:
            statement_date = _parse_date_str(date_match.group(1))

    folio_indices = [idx for idx, line in enumerate(lines) if re.search(r"Folio\s*(?:No|Number)?", line, re.IGNORECASE)]
    funds: list[dict[str, Any]] = []

    if not folio_indices:
        logger.warning("No folio markers found in CAMS PDF; using fallback parsing")
        return {
            "investor_name": investor_name,
            "pan": pan,
            "statement_date": statement_date,
            "funds": [],
            "total_current_value": 0.0,
            "parse_method": "cams_pdf",
        }

    for i, folio_idx in enumerate(folio_indices):
        next_idx = folio_indices[i + 1] if i + 1 < len(folio_indices) else len(lines)
        start_idx = max(0, folio_idx - 2)
        block_lines = lines[start_idx:next_idx]
        block_text = "\n".join(block_lines)

        fund_name = "Unknown Fund"
        for candidate in block_lines[:4]:
            if re.search(r"fund|scheme", candidate, re.IGNORECASE):
                fund_name = candidate
                break

        folio_match = re.search(r"Folio\s*(?:No|Number)?\s*[:\-]?\s*([A-Za-z0-9/\-]+)", lines[folio_idx], re.IGNORECASE)
        folio_number = folio_match.group(1).strip() if folio_match else "N/A"

        isin_match = re.search(r"\b[A-Z]{2}[A-Z0-9]{10}\b", block_text)
        isin = isin_match.group(0) if isin_match else "N/A"

        units_match = re.search(r"(?:Units|Balance\s*Units?)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)", block_text, re.IGNORECASE)
        nav_match = re.search(r"(?:NAV|Nav)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)", block_text)
        current_value_match = re.search(
            r"(?:Current\s*Value|Market\s*Value|Value)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
            block_text,
            re.IGNORECASE,
        )

        units_held = _parse_indian_number(units_match.group(1) if units_match else "0")
        nav = _parse_indian_number(nav_match.group(1) if nav_match else "0")
        current_value = _parse_indian_number(current_value_match.group(1) if current_value_match else "0")

        txs = extract_transactions(block_text)
        purchase_transactions: list[dict[str, Any]] = []
        redemption_transactions: list[dict[str, Any]] = []

        for tx in txs:
            tx_type = tx.get("transaction_type", "").lower()
            if any(token in tx_type for token in ["redeem", "switch out", "sell", "stp out"]):
                redemption_transactions.append(tx)
            else:
                purchase_transactions.append(tx)

        fund = {
            "fund_name": fund_name,
            "folio_number": folio_number,
            "isin": isin,
            "units_held": units_held,
            "nav": nav,
            "current_value": current_value,
            "purchase_transactions": purchase_transactions,
            "redemption_transactions": redemption_transactions,
            "redeemed": units_held <= 0.0,
        }
        funds.append(fund)

    total_current_value = float(sum(fund.get("current_value", 0.0) for fund in funds))

    return {
        "investor_name": investor_name,
        "pan": pan,
        "statement_date": statement_date,
        "funds": funds,
        "total_current_value": total_current_value,
        "parse_method": "cams_pdf",
    }
