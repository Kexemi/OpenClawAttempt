#!/usr/bin/env python3
"""
Build video or image for a draft from the asset library.
Reads content.json, resolves asset_key via asset_mapping, assembles 9:16 output.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
CONFIG_DIR = PROJECT_ROOT / "config"
OUTPUT_SIZE = (1080, 1920)  # 9:16 for TikTok/Reels


def load_asset_mapping() -> dict:
    """Load config/asset_mapping.yaml. Raises on missing or invalid file."""
    path = CONFIG_DIR / "asset_mapping.yaml"
    if not path.exists():
        raise FileNotFoundError(f"config/asset_mapping.yaml not found. Create it with asset_key -> theme/asset_key mappings.")
    import yaml
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ValueError(f"config/asset_mapping.yaml invalid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("config/asset_mapping.yaml must be a dict of asset_key -> path")
    return data


def resolve_asset_path(asset_key: str) -> Path:
    """Resolve asset_key to path in assets/. Raises with clear error if not found."""
    mapping = load_asset_mapping()
    if asset_key not in mapping:
        raise ValueError(
            f"asset_key '{asset_key}' not in config/asset_mapping.yaml. "
            f"Add mapping for '{asset_key}' or use a key from: {list(mapping.keys())[:10]}"
        )
    rel = mapping[asset_key]
    full = ASSETS_DIR / rel

    # Check for video.mp4
    if (full / "video.mp4").exists():
        return full / "video.mp4"
    if full.with_suffix(".mp4").exists():
        return full.with_suffix(".mp4")
    if full.exists() and full.suffix.lower() in (".mp4", ".mov", ".webm"):
        return full

    # Check for images/ folder (slideshow)
    images_dir = full / "images" if full.is_dir() else full.parent / "images"
    if images_dir.exists():
        imgs = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg"))
        if imgs:
            return images_dir

    # Check for single image file
    if full.exists() and full.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return full

    raise FileNotFoundError(
        f"Asset path assets/{rel} has no video.mp4, images/*.png, or *.mp4. "
        f"Add video or images to assets/{rel} or fix config/asset_mapping.yaml."
    )


def build_slideshow_from_images(images_dir: Path, output_path: Path, duration_per_image: float = 3.0) -> None:
    """Use ffmpeg to create video from images. 9:16, scale and pad. Raises on failure."""
    imgs = sorted(images_dir.glob("*.png")) + sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.jpeg"))
    if not imgs:
        raise FileNotFoundError(f"No .png/.jpg images in {images_dir}")

    concat_file = output_path.parent / "_concat.txt"
    lines = []
    for img in imgs:
        lines.append(f"file '{img.resolve()}'")
        lines.append(f"duration {duration_per_image}")
    lines.append(f"file '{imgs[-1].resolve()}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")

    w, h = OUTPUT_SIZE
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        str(output_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        concat_file.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr or result.stdout}")
    except subprocess.TimeoutExpired:
        concat_file.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg timed out after 60s")
    except FileNotFoundError:
        concat_file.unlink(missing_ok=True)
        raise FileNotFoundError("ffmpeg not found. Install ffmpeg and add to PATH.")


def build_video(draft_dir: Path) -> None:
    """Build video.mp4 or copy image to draft folder. Raises on failure with defined error."""
    content_path = draft_dir / "content.json"
    if not content_path.exists():
        raise FileNotFoundError(f"{draft_dir}/content.json not found")

    content = json.loads(content_path.read_text(encoding="utf-8"))
    asset_key = content.get("asset_key")
    if not asset_key:
        raise ValueError("content.json missing required field: asset_key")
    asset_type = content.get("asset_type", "video")

    asset_path = resolve_asset_path(asset_key)
    output_video = draft_dir / "video.mp4"
    output_image = draft_dir / "image.png"

    # Asset is a video file
    if asset_path.suffix.lower() in (".mp4", ".mov", ".webm"):
        w, h = OUTPUT_SIZE
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(asset_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "60",
            str(output_video)
        ], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {asset_path}: {result.stderr or result.stdout}")
        return

    # Asset is images directory (slideshow)
    if asset_path.is_dir():
        build_slideshow_from_images(asset_path, output_video)
        return

    # Single image
    if asset_path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        if asset_type == "image":
            shutil.copy(asset_path, output_image)
            return
        w, h = OUTPUT_SIZE
        result = subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(asset_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "5", "-r", "30",
            str(output_video)
        ], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for image {asset_path}: {result.stderr or result.stdout}")
        return

    raise RuntimeError(f"Unsupported asset type at {asset_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: build_video.py <draft_dir>", file=sys.stderr)
        sys.exit(1)

    draft_dir = Path(sys.argv[1]).resolve()
    if not draft_dir.is_dir():
        print(f"Not a directory: {draft_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        build_video(draft_dir)
        sys.exit(0)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"build_video failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
