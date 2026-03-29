"""AIRA module: agents/video_studio/video_builder.py"""

import base64
import io
import logging
import os
import tempfile
from typing import Any

import numpy as np
from moviepy.editor import CompositeVideoClip, ImageClip, TextClip, concatenate_videoclips
from PIL import Image

logger = logging.getLogger(__name__)


def _decode_frame_to_array(image_base64: str) -> np.ndarray:
    raw = base64.b64decode(image_base64.encode("ascii"))
    with Image.open(io.BytesIO(raw)) as img:
        return np.array(img.convert("RGB"))


def _clip_with_optional_caption(image_clip: ImageClip, caption: str) -> Any:
    if not caption:
        return image_clip
    try:
        txt = TextClip(
            caption,
            fontsize=28,
            color="white",
            method="caption",
            size=(1160, None),
            align="center",
        ).set_duration(image_clip.duration)
        txt = txt.set_position((60, image_clip.h - 110))
        return CompositeVideoClip([image_clip, txt], size=image_clip.size)
    except Exception as exc:
        logger.warning("Text overlay skipped due to TextClip failure: %s", exc)
        return image_clip


def build_video_from_frames(frames: list[dict[str, Any]], output_path: str, fps: int = 24) -> str | None:
    clips = []
    try:
        for frame in frames:
            image_base64 = frame.get("image_base64")
            if not image_base64:
                continue
            duration = float(frame.get("duration_seconds") or 2.0)
            caption = str(frame.get("caption") or "")

            image_array = _decode_frame_to_array(image_base64)
            image_clip = ImageClip(image_array).set_duration(max(0.5, duration))
            clip = _clip_with_optional_caption(image_clip, caption)
            clips.append(clip)

        if not clips:
            logger.error("No valid clips generated from input frames")
            return None

        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, codec="libx264", audio=False, fps=fps, logger=None)
        final_clip.close()

        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass

        return output_path
    except Exception as exc:
        logger.exception("Video build failed error=%s", exc)
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
        return None


def build_video_to_bytes(frames: list[dict[str, Any]]) -> bytes | None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp:
            temp_path = temp.name

        built_path = build_video_from_frames(frames=frames, output_path=temp_path)
        if not built_path:
            return None

        with open(built_path, "rb") as f:
            return f.read()
    except Exception as exc:
        logger.exception("Failed converting video to bytes error=%s", exc)
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                logger.warning("Could not delete temp video file path=%s", temp_path)


def encode_video_to_base64(frames: list[dict[str, Any]]) -> str | None:
    try:
        video_bytes = build_video_to_bytes(frames)
        if not video_bytes:
            return None
        return base64.b64encode(video_bytes).decode("ascii")
    except Exception as exc:
        logger.exception("Failed encoding video to base64 error=%s", exc)
        return None
