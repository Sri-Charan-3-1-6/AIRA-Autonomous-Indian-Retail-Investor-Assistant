"""AIRA module: core/gemini_client.py"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from groq import Groq

from core.config import get_settings


logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile") -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        if self.client is None:
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as exc:
                logger.exception(
                    "Groq client initialization failed model=%s error_type=%s error=%s",
                    self.model_name,
                    type(exc).__name__,
                    exc,
                )
                raise
        return self.client

    def _generate_sync(self, prompt: str) -> str:
        prompt_preview = (prompt or "")[:240].replace("\n", " ")
        try:
            completion = self._get_client().chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
            )
        except Exception as exc:
            logger.exception(
                "Groq completion failed model=%s prompt_len=%d prompt_preview=%s error_type=%s error=%s",
                self.model_name,
                len(prompt or ""),
                prompt_preview,
                type(exc).__name__,
                exc,
            )
            raise
        content = completion.choices[0].message.content if completion.choices else ""
        return (content or "").strip()

    async def generate_text(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt)

    async def generate_json(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        json_prompt = (
            "Return ONLY valid JSON that matches this schema. "
            "Do not include markdown, backticks, or explanations.\n"
            f"Schema: {json.dumps(schema, ensure_ascii=True)}\n"
            f"Task: {prompt}"
        )
        raw = await self.generate_text(json_prompt)

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise ValueError("Groq model did not return valid JSON content")


_gemini_client: Optional[GeminiClient] = None


def init_gemini_client() -> GeminiClient:
    global _gemini_client
    if _gemini_client is None:
        settings = get_settings()
        _gemini_client = GeminiClient(api_key=settings.GROQ_API_KEY)
    return _gemini_client


def get_gemini_client() -> GeminiClient:
    if _gemini_client is None:
        return init_gemini_client()
    return _gemini_client
