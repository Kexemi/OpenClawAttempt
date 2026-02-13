#!/usr/bin/env python3
"""
xAI Imagine API client: video and image generation.
Uses XAI_API_KEY. Video: POST /v1/videos/generations, poll until done, download.
Image: POST /v1/images/generations, save result.
"""
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv = PROJECT_ROOT / ".env"
if _dotenv.exists():
    from dotenv import load_dotenv
    load_dotenv(_dotenv)


def _get_api_key() -> str:
    key = os.environ.get("XAI_API_KEY")
    if not key or key.startswith("your_"):
        raise ValueError("XAI_API_KEY not set in .env")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


def generate_video(
    prompt: str,
    output_path: Path,
    *,
    duration: int = 10,
    aspect_ratio: str = "9:16",
    resolution: str = "720p",
    timeout: int = 1800,  # 30 min — video generation can be slow
    poll_interval: int = 5,
) -> None:
    """
    Generate video via xAI Imagine. Submits request, polls until done, downloads.
    Raises on failure or timeout.
    """
    import requests

    url = "https://api.x.ai/v1/videos/generations"
    payload = {
        "model": "grok-imagine-video",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=60)
    resp.raise_for_status()
    data = resp.json()
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"xAI video API did not return request_id: {data}")

    poll_url = f"https://api.x.ai/v1/videos/{request_id}"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        poll_resp = requests.get(poll_url, headers=_headers(), timeout=30)
        poll_resp.raise_for_status()
        result = poll_resp.json()
        status = result.get("status", "").lower()
        if status == "done":
            video = result.get("video") or {}
            video_url = video.get("url")
            if not video_url:
                raise RuntimeError(f"xAI video done but no url: {result}")
            if not video.get("respect_moderation", True):
                raise RuntimeError("xAI video filtered by content moderation")
            # Download
            dl_resp = requests.get(video_url, timeout=60)
            dl_resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(dl_resp.content)
            return
        if status == "expired":
            raise RuntimeError(f"xAI video request expired: {request_id}")
        time.sleep(poll_interval)

    raise TimeoutError(f"xAI video generation timed out after {timeout}s (request_id={request_id})")


def generate_image(
    prompt: str,
    output_path: Path,
    *,
    aspect_ratio: str = "9:16",
) -> None:
    """
    Generate image via xAI Imagine. Saves to output_path.
    Raises on failure.
    """
    import requests

    url = "https://api.x.ai/v1/images/generations"
    payload = {
        "model": "grok-imagine-image",
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=120)
    resp.raise_for_status()
    data = resp.json()
    # Response format: typically {"data": [{"url": "..."}]} or {"url": "..."}
    url_or_data = data.get("data")
    if url_or_data and isinstance(url_or_data, list) and url_or_data:
        img_url = url_or_data[0].get("url")
    else:
        img_url = data.get("url")
    if not img_url:
        raise RuntimeError(f"xAI image API did not return url: {data}")

    dl_resp = requests.get(img_url, timeout=60)
    dl_resp.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(dl_resp.content)
