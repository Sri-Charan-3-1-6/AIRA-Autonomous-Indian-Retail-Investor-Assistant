"""AIRA module: agents/market_gpt/response_formatter.py"""

import json
import logging

logger = logging.getLogger(__name__)


def format_response(raw_response: str, sources: list, query_type: str) -> str:
    response = (raw_response or "").strip()
    qtype = (query_type or "conversational").strip().lower()

    if qtype == "analysis":
        formatted = "\n\n".join(
            [
                "Analysis Overview",
                response,
            ]
        )
    elif qtype == "scenario":
        first_line = response.splitlines()[0] if response else "Impact Summary"
        formatted = "\n\n".join(
            [
                f"Impact Summary: {first_line}",
                "Detailed Breakdown",
                response,
            ]
        )
    elif qtype == "recommendation":
        formatted = "\n".join(
            [
                "Actionable Recommendations",
                response,
            ]
        )
    else:
        formatted = response

    if sources:
        source_lines = ["Sources:"]
        for source in sources:
            source_lines.append(f"- {source}")
        formatted = formatted + "\n\n" + "\n".join(source_lines)

    return formatted.strip()


async def extract_action_items(response: str, gemini_client) -> list[str]:
    prompt = (
        "Extract clear action items from the text below. "
        "Return ONLY JSON array of short strings.\n\n"
        f"Text:\n{response}"
    )

    try:
        raw = await gemini_client.generate_text(prompt)
        text = raw.strip()

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]

        return []
    except Exception as exc:
        logger.exception("Failed to extract action items error=%s", exc)
        return []


def add_disclaimer(response: str) -> str:
    disclaimer = (
        "Disclaimer: This analysis is for informational purposes only and does not constitute financial advice. "
        "Please consult a SEBI-registered financial advisor before making investment decisions."
    )
    base = (response or "").rstrip()
    return base + "\n\n" + disclaimer
