"""AIRA module: api/video_studio.py"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from agents.video_studio.agent import VideoStudioAgent
from models.agent_task import AgentTask
from models.video import TriggerVideoRequest

router = APIRouter()
logger = logging.getLogger(__name__)

_daily_cache: dict[str, Any] = {
    "expires_at": None,
    "payload": None,
}


def _get_video_agent(request: Request) -> VideoStudioAgent:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator and "video_studio" in orchestrator.agents:
        agent = orchestrator.agents["video_studio"]
        if isinstance(agent, VideoStudioAgent):
            return agent
    return VideoStudioAgent()


def _serialize_payload(payload: dict[str, Any], cached: bool) -> dict[str, Any]:
    result = dict(payload)
    result["cached"] = cached
    return result


@router.get("/daily")
async def get_daily_video(
    request: Request,
    include_video: bool = Query(default=False),
    user_id: str = Query(default="system"),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if not include_video:
        expires_at = _daily_cache.get("expires_at")
        cached_payload = _daily_cache.get("payload")
        if isinstance(expires_at, datetime) and expires_at > now and isinstance(cached_payload, dict):
            logger.info("VideoStudio daily cache hit user_id=%s", user_id)
            return _serialize_payload(cached_payload, cached=True)

    agent = _get_video_agent(request)
    task = AgentTask(
        agent_name="video_studio",
        user_id=user_id,
        input_data={
            "action": "generate_daily",
            "user_id": user_id,
            "include_video": include_video,
        },
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Daily video generation failed")

    payload = _serialize_payload(result.output_data, cached=False)
    if not include_video:
        _daily_cache["payload"] = dict(payload)
        _daily_cache["expires_at"] = now + timedelta(minutes=60)
    return payload


@router.get("/stock/{symbol}")
async def get_stock_video(symbol: str, request: Request, include_video: bool = Query(default=False), user_id: str = Query(default="system")) -> dict[str, Any]:
    agent = _get_video_agent(request)
    task = AgentTask(
        agent_name="video_studio",
        user_id=user_id,
        input_data={
            "action": "generate_stock",
            "user_id": user_id,
            "symbol": symbol.upper(),
            "include_video": include_video,
        },
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Stock video generation failed")
    return _serialize_payload(result.output_data, cached=False)


@router.get("/frames")
async def get_frames_only(request: Request, user_id: str = Query(default="system")) -> dict[str, Any]:
    agent = _get_video_agent(request)
    task = AgentTask(
        agent_name="video_studio",
        user_id=user_id,
        input_data={
            "action": "get_frames_only",
            "user_id": user_id,
            "include_video": False,
        },
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Frames generation failed")

    payload = _serialize_payload(result.output_data, cached=False)
    payload["video_base64"] = None
    return payload


@router.post("/trigger")
async def trigger_video_generation(body: TriggerVideoRequest, request: Request) -> dict[str, Any]:
    _daily_cache["payload"] = None
    _daily_cache["expires_at"] = None

    agent = _get_video_agent(request)
    task = AgentTask(
        agent_name="video_studio",
        user_id=body.user_id,
        input_data={
            "action": "generate_daily",
            "user_id": body.user_id,
            "include_video": body.include_video,
        },
    )
    result = await agent.run(task)
    if result.status != "completed":
        raise HTTPException(status_code=500, detail=result.error_message or "Manual trigger failed")
    return _serialize_payload(result.output_data, cached=False)
