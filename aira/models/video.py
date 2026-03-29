"""AIRA module: models/video.py"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoFrame(BaseModel):
    frame_type: str = Field(...)
    image_base64: str = Field(...)
    duration_seconds: float = Field(..., gt=0)
    caption: str = Field(...)


class VideoScript(BaseModel):
    intro: str
    market_overview: str
    top_opportunities: str
    sector_watch: str
    closing: str
    duration_seconds: int
    tone: str


class VideoOutput(BaseModel):
    script: VideoScript
    frames: list[VideoFrame]
    video_base64: Optional[str] = None
    generated_at: Optional[datetime] = None
    cached: bool = False


class TriggerVideoRequest(BaseModel):
    user_id: str = "system"
    include_video: bool = False
