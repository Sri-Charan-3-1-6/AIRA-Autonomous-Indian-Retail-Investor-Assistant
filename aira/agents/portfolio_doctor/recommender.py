"""AIRA module: agents/portfolio_doctor/recommender.py"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _fallback_response() -> dict[str, Any]:
    return {
        "summary": "Portfolio analysis completed. Rebalancing recommendations are currently in fallback mode due to AI response issues.",
        "overall_score": 55,
        "recommendations": [
            {
                "action": "HOLD",
                "fund_name": "Portfolio",
                "reason": "Awaiting validated AI recommendation output.",
                "priority": "MEDIUM",
                "amount_suggestion": "Review manually",
            }
        ],
        "red_flags": ["AI recommendation service unavailable or returned invalid response."],
        "positive_highlights": ["Core diagnostics (XIRR, overlap, expense, benchmark, tax) completed successfully."],
    }


async def generate_rebalancing_plan(portfolio_analysis: dict[str, Any], gemini_client) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "overall_score": {"type": "integer"},
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["BUY", "SELL", "SWITCH", "HOLD"]},
                        "fund_name": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
                        "amount_suggestion": {"type": "string"},
                    },
                    "required": ["action", "fund_name", "reason", "priority", "amount_suggestion"],
                },
            },
            "red_flags": {"type": "array", "items": {"type": "string"}},
            "positive_highlights": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "overall_score", "recommendations", "red_flags", "positive_highlights"],
    }

    prompt = (
        "You are Portfolio Doctor for Indian retail investors. Analyze the provided full portfolio data and "
        "produce a practical rebalancing plan. Respond with valid JSON only and no markdown. "
        "Recommendations must be investor-friendly and specific to overlap, XIRR, fees, benchmark alpha, and tax impact.\n\n"
        f"Portfolio analysis input:\n{portfolio_analysis}"
    )

    try:
        response = await gemini_client.generate_json(prompt=prompt, schema=schema)
        if not isinstance(response, dict):
            logger.error("Gemini response was not a dict")
            return _fallback_response()

        output = _fallback_response()
        output.update(response)

        if not isinstance(output.get("overall_score"), int):
            output["overall_score"] = int(float(output.get("overall_score", 55)))
        output["overall_score"] = max(0, min(100, output["overall_score"]))

        if not isinstance(output.get("recommendations"), list):
            output["recommendations"] = _fallback_response()["recommendations"]

        return output
    except Exception as exc:
        logger.exception("Gemini rebalancing generation failed: %s", exc)
        return _fallback_response()
