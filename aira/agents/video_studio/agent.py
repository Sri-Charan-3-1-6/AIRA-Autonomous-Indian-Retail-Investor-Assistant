"""AIRA module: agents/video_studio/agent.py"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent
from agents.chart_whisperer.agent import ChartWhispererAgent
from agents.signal_hunter import fii_dii_tracker
from agents.video_studio import chart_renderer, script_generator, video_builder
from core.gemini_client import get_gemini_client
from core.supabase_client import get_supabase
from db import crud
from models.agent_task import AgentTask

logger = logging.getLogger(__name__)


class VideoStudioAgent(BaseAgent):
    agent_name = "video_studio"
    agent_version = "2.0.0"

    async def _fetch_top_signals(self, limit: int = 5) -> list[dict[str, Any]]:
        def _op() -> list[dict[str, Any]]:
            client = get_supabase()
            response = (
                client.table("market_signals")
                .select("symbol, signal_type, opportunity_score, data, created_at")
                .order("opportunity_score", desc=True)
                .limit(limit)
                .execute()
            )
            rows = response.data or []
            out: list[dict[str, Any]] = []
            for row in rows:
                payload = row.get("data") or {}
                out.append(
                    {
                        "symbol": row.get("symbol"),
                        "signal_type": row.get("signal_type"),
                        "opportunity_score": row.get("opportunity_score"),
                        "category": payload.get("category") or "WATCH",
                        "explanation": payload.get("explanation") or "",
                        "technical_indicators": (payload.get("payload") or {}).get("technical_indicators", {}),
                        "data": payload.get("payload") or {},
                        "created_at": row.get("created_at"),
                    }
                )
            return out

        return await asyncio.to_thread(_op)

    async def _save_video_output(
        self,
        user_id: str,
        video_type: str,
        script: dict[str, Any],
        frames: list[dict[str, Any]],
        video_base64: str | None,
    ) -> None:
        def _op() -> None:
            client = get_supabase()
            client.table("video_outputs").insert(
                {
                    "user_id": user_id,
                    "video_type": video_type,
                    "script": script,
                    "frames": frames,
                    "video_base64": video_base64,
                }
            ).execute()

        try:
            await asyncio.to_thread(_op)
        except Exception as exc:
            logger.exception("Saving video output failed user_id=%s type=%s error=%s", user_id, video_type, exc)

    def _build_sector_performance(self, signals: list[dict[str, Any]]) -> dict[str, float]:
        if not signals:
            return {
                "BANKING": 0.8,
                "IT": 0.5,
                "AUTO": 0.2,
                "PHARMA": -0.3,
                "METALS": -0.6,
            }

        sector_acc: dict[str, list[float]] = {}
        for signal in signals:
            payload = signal.get("data") or {}
            sector = str(payload.get("sector") or "MIXED").upper()
            score = float(signal.get("opportunity_score") or 0.0)
            perf = (score - 50.0) / 25.0
            sector_acc.setdefault(sector, []).append(perf)

        return {k: round(sum(v) / len(v), 2) for k, v in list(sector_acc.items())[:6]}

    async def _encode_video_with_timeout(self, frames: list[dict[str, Any]]) -> str | None:
        try:
            return await asyncio.wait_for(asyncio.to_thread(video_builder.encode_video_to_base64, frames), timeout=60)
        except asyncio.TimeoutError:
            logger.warning("Video encoding timed out after 60 seconds, returning frames only")
            return None
        except Exception as exc:
            logger.exception("Video encoding failed error=%s", exc)
            return None

    async def _generate_daily(self, user_id: str, include_video: bool, fast_mode: bool = False) -> dict[str, Any]:
        logger.info(
            "VideoStudio daily generation started user_id=%s include_video=%s fast_mode=%s",
            user_id,
            include_video,
            fast_mode,
        )
        top_signals = await self._fetch_top_signals(limit=5)
        fii_data = await fii_dii_tracker.fetch_fii_dii_data()

        top_gainers = sorted(top_signals, key=lambda x: float(x.get("opportunity_score") or 0.0), reverse=True)[:3]
        top_losers = sorted(top_signals, key=lambda x: float(x.get("opportunity_score") or 0.0))[:3]

        market_data = {
            "top_signals": top_signals,
            "fii_net": fii_data.get("fii_net", 0.0),
            "dii_net": fii_data.get("dii_net", 0.0),
            "nifty_change_pct": 0.5,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "date": datetime.utcnow().strftime("%d %b %Y"),
            "sector_performance": self._build_sector_performance(top_signals),
        }

        script = await script_generator.generate_market_script(
            market_data,
            get_gemini_client(),
            use_groq=not fast_mode,
        )
        frames = chart_renderer.render_all_frames(script, market_data)

        video_base64 = None
        if include_video:
            video_base64 = await self._encode_video_with_timeout(frames)

        await self._save_video_output(
            user_id=user_id,
            video_type="daily",
            script=script,
            frames=frames,
            video_base64=video_base64,
        )

        return {
            "script": script,
            "frames": frames,
            "video_base64": video_base64,
            "generated_at": datetime.utcnow().isoformat(),
            "cached": False,
        }

    async def _generate_stock(self, user_id: str, symbol: str, include_video: bool) -> dict[str, Any]:
        logger.info("VideoStudio stock generation started user_id=%s symbol=%s include_video=%s", user_id, symbol, include_video)
        chart_agent = ChartWhispererAgent()
        analysis_task = AgentTask(
            agent_name="chart_whisperer",
            user_id=user_id,
            input_data={
                "action": "analyze",
                "symbol": symbol,
                "include_chart": False,
                "period": "6mo",
                "interval": "1d",
            },
        )
        analysis_result = await chart_agent.run(analysis_task)
        analysis = analysis_result.output_data if analysis_result.status == "completed" else {}

        script = await script_generator.generate_stock_script(symbol=symbol, analysis=analysis, groq_client=get_gemini_client())

        signal_frame = chart_renderer.render_signal_frame(
            {
                "symbol": symbol,
                "opportunity_score": float(analysis.get("confidence", 0.0)) * 100.0,
                "category": analysis.get("overall_signal", "WATCH"),
                "explanation": str(analysis.get("indicator_interpretation", {}).get("summary") or "Technical setup monitor."),
                "technical_indicators": analysis.get("indicators", {}),
            }
        )
        title_frame = chart_renderer.render_title_frame(
            title=f"{symbol} Focus",
            subtitle=str(script.get("tone") or "NEUTRAL"),
            date=datetime.utcnow().strftime("%d %b %Y"),
        )
        closing_frame = chart_renderer.render_closing_frame(str(script.get("closing") or "Stay disciplined."))

        frames = [
            {
                "frame_type": "title",
                "image_base64": title_frame,
                "duration_seconds": 2.0,
                "caption": str(script.get("intro") or "Stock overview."),
            },
            {
                "frame_type": "signal",
                "image_base64": signal_frame,
                "duration_seconds": 4.0,
                "caption": str(script.get("market_overview") or "Technical snapshot."),
            },
            {
                "frame_type": "closing",
                "image_base64": closing_frame,
                "duration_seconds": 2.3,
                "caption": str(script.get("closing") or "Monitor risk."),
            },
        ]

        video_base64 = None
        if include_video:
            video_base64 = await self._encode_video_with_timeout(frames)

        await self._save_video_output(
            user_id=user_id,
            video_type="stock",
            script=script,
            frames=frames,
            video_base64=video_base64,
        )

        return {
            "script": script,
            "frames": frames,
            "video_base64": video_base64,
            "generated_at": datetime.utcnow().isoformat(),
            "cached": False,
        }

    async def run(self, task: AgentTask) -> AgentTask:
        logger.info("VideoStudioAgent started task_id=%s", task.task_id)
        task.status = "running"
        try:
            data = task.input_data or {}
            action = str(data.get("action") or "generate_daily").strip().lower()
            user_id = str(data.get("user_id") or task.user_id or "system")
            symbol = str(data.get("symbol") or "").upper().strip()
            include_video = bool(data.get("include_video", False))

            if action == "generate_daily":
                task.output_data = await self._generate_daily(user_id=user_id, include_video=include_video)
            elif action == "generate_stock":
                if not symbol:
                    raise ValueError("symbol is required for generate_stock")
                task.output_data = await self._generate_stock(user_id=user_id, symbol=symbol, include_video=include_video)
            elif action == "get_frames_only":
                task.output_data = await self._generate_daily(user_id=user_id, include_video=False, fast_mode=True)
            else:
                raise ValueError("action must be one of generate_daily, generate_stock, get_frames_only")

            task.status = "completed"
            task.confidence_score = 0.84
            task.completed_at = datetime.utcnow()
            await self.log_to_audit(task, crud)
            logger.info("VideoStudioAgent completed task_id=%s", task.task_id)
            return task
        except Exception as exc:
            logger.exception("VideoStudioAgent failed task_id=%s error=%s", task.task_id, exc)
            task.status = "failed"
            task.error_message = str(exc)
            task.completed_at = datetime.utcnow()
            task.output_data = {
                "script": {},
                "frames": [],
                "video_base64": None,
                "generated_at": datetime.utcnow().isoformat(),
                "cached": False,
            }
            await self.log_to_audit(task, crud)
            return task

    async def health_check(self) -> dict:
        return {
            "agent": self.agent_name,
            "status": "healthy",
            "version": self.agent_version,
            "phase": "phase_6",
            "capabilities": [
                "market_summary_video_script",
                "animated_chart_frame_rendering",
                "mp4_base64_video_build",
                "stock_focus_video_generation",
                "frames_only_fast_mode",
            ],
        }
