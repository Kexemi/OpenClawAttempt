#!/usr/bin/env python3
"""
Build video or image for a draft via xAI Imagine.
Reads content.json (video_prompt, voiceover_text, music_style), calls Imagine API.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_SIZE = (1080, 1920)  # 9:16 for TikTok/Reels


def _build_combined_video_prompt(content: dict) -> str:
    """Build combined visual + audio prompt for Imagine video."""
    video_prompt = content.get("video_prompt") or ""
    voiceover_text = content.get("voiceover_text") or ""
    music_style = content.get("music_style") or ""
    parts = [video_prompt]
    if voiceover_text:
        parts.append(f'Narrator voiceover saying: "{voiceover_text}"')
    if music_style:
        parts.append(f"Background music: {music_style}")
    return ". ".join(p for p in parts if p)


def build_media(draft_dir: Path) -> None:
    """Build video.mp4 or image.png for draft via xAI Imagine. Raises on failure."""
    import sys
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))
    from imagine_client import generate_video, generate_image

    content_path = draft_dir / "content.json"
    if not content_path.exists():
        raise FileNotFoundError(f"{draft_dir}/content.json not found")

    content = json.loads(content_path.read_text(encoding="utf-8"))
    asset_type = content.get("asset_type", "video")
    video_prompt = content.get("video_prompt")
    if not video_prompt:
        raise ValueError("content.json missing required field: video_prompt")

    output_video = draft_dir / "video.mp4"
    output_image = draft_dir / "image.png"

    if asset_type == "video":
        prompt = _build_combined_video_prompt(content)
        generate_video(
            prompt,
            output_video,
            duration=10,
            aspect_ratio="9:16",
            resolution="720p",
            timeout=1800,  # 30 min — xAI Imagine can be slow
            poll_interval=5,
        )
        # Ensure 9:16 1080x1920 for Late API if Imagine returns different size
        _ensure_output_size(output_video, OUTPUT_SIZE)
        return

    if asset_type == "image":
        generate_image(video_prompt, output_image, aspect_ratio="9:16")
        return

    raise ValueError(f"content.json asset_type must be 'video' or 'image', got: {asset_type!r}")


def _ensure_output_size(video_path: Path, size: tuple[int, int]) -> None:
    """Re-encode video to exact size if needed. No-op if already correct."""
    w, h = size
    try:
        # Quick check: if ffmpeg can probe and dimensions match, skip
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            dims = result.stdout.strip().split(",")
            if len(dims) >= 2:
                try:
                    cw, ch = int(dims[0]), int(dims[1])
                    if cw == w and ch == h:
                        return
                except ValueError:
                    pass
    except FileNotFoundError:
        return  # ffprobe not available, skip

    tmp = video_path.with_suffix(".tmp.mp4")
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(tmp)
        ], capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and tmp.exists():
            tmp.replace(video_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 2:
        print("Usage: build_media.py <draft_dir>", file=sys.stderr)
        sys.exit(1)

    draft_dir = Path(sys.argv[1]).resolve()
    if not draft_dir.is_dir():
        print(f"Not a directory: {draft_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        build_media(draft_dir)
        sys.exit(0)
    except (FileNotFoundError, ValueError, RuntimeError, TimeoutError) as e:
        print(f"build_media failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
