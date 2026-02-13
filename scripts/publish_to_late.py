#!/usr/bin/env python3
"""
Publish a draft to Late API (TikTok + Instagram Reels).
Reads draft content.json, loads config/accounts.yaml for Late account IDs,
uploads media via presign, creates post with publishNow=true.

Requires: LATE_API_KEY in .env
"""
import json
import os
import sys
from pathlib import Path

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv = PROJECT_ROOT / ".env"
if _dotenv.exists():
    from dotenv import load_dotenv
    load_dotenv(_dotenv)

CONFIG_DIR = PROJECT_ROOT / "config"
LATE_BASE = "https://getlate.dev/api/v1"


def load_accounts() -> dict:
    path = CONFIG_DIR / "accounts.yaml"
    if not path.exists():
        raise FileNotFoundError("config/accounts.yaml not found")
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_late_api_key() -> str:
    key = os.environ.get("LATE_API_KEY")
    if not key or key.startswith("your_"):
        raise ValueError("LATE_API_KEY not set in .env")
    return key


def _req(method: str, path: str, api_key: str, json_body: dict = None, data: bytes = None, headers: dict = None) -> dict:
    import urllib.request
    url = f"{LATE_BASE}{path}"
    h = {"Authorization": f"Bearer {api_key}"}
    if headers:
        h.update(headers)
    if json_body is not None:
        h["Content-Type"] = "application/json"
        body = json.dumps(json_body).encode()
    elif data is not None:
        body = data
    else:
        body = None
    req = urllib.request.Request(url, data=body, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def upload_media(file_path: Path, api_key: str) -> str:
    """Upload file via Late presign. Returns publicUrl."""
    ext = file_path.suffix.lower()
    content_types = {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    content_type = content_types.get(ext, "video/mp4")
    presign = _req("POST", "/media/presign", api_key, json_body={
        "filename": file_path.name,
        "contentType": content_type,
    })
    upload_url = presign["uploadUrl"]
    public_url = presign["publicUrl"]

    # PUT file to uploadUrl
    data = file_path.read_bytes()
    import urllib.request
    req = urllib.request.Request(upload_url, data=data, method="PUT", headers={"Content-Type": content_type})
    with urllib.request.urlopen(req, timeout=120) as _:
        pass
    return public_url


def publish(draft_dir: Path) -> bool:
    content_path = draft_dir / "content.json"
    if not content_path.exists():
        print("content.json not found", file=sys.stderr)
        return False

    content = json.loads(content_path.read_text(encoding="utf-8"))
    account = content.get("account", "genz")
    caption = content.get("caption", "")
    hashtags = content.get("hashtags", "")
    text = f"{caption}\n\n{hashtags}".strip()

    accounts = load_accounts()
    if account not in accounts:
        print(f"Account '{account}' not in config/accounts.yaml", file=sys.stderr)
        return False

    cfg = accounts[account]
    tiktok_id = cfg.get("tiktok_account_id") or cfg.get("tiktok_profile_id")
    instagram_id = cfg.get("instagram_account_id") or cfg.get("reels_profile_id")
    account_ids = [tiktok_id, instagram_id]
    account_ids = [a for a in account_ids if a and not str(a).startswith("YOUR_")]

    if not account_ids:
        print(f"No valid Late account IDs for '{account}'", file=sys.stderr)
        return False

    api_key = get_late_api_key()

    media_path = draft_dir / "video.mp4"
    if not media_path.exists():
        media_path = draft_dir / "image.png"

    media_items = []
    if media_path.exists():
        public_url = upload_media(media_path, api_key)
        media_type = "video" if media_path.suffix.lower() in (".mp4", ".mov", ".webm") else "image"
        media_items = [{"type": media_type, "url": public_url}]

    # Late uses platform names: tiktok, instagram
    platform_map = {"tiktok": tiktok_id, "instagram": instagram_id}
    platforms = []
    for plat, acc_id in platform_map.items():
        if acc_id and not str(acc_id).startswith("YOUR_"):
            platforms.append({"platform": plat, "accountId": acc_id})

    if not platforms:
        print("No valid platforms", file=sys.stderr)
        return False

    body = {
        "content": text,
        "platforms": platforms,
        "publishNow": True,
        "timezone": "UTC",
    }
    if media_items:
        body["mediaItems"] = media_items

    result = _req("POST", "/posts", api_key, json_body=body)
    if "post" in result or "error" not in result:
        return True
    print("Late API error:", result.get("error", result), file=sys.stderr)
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: publish_to_late.py <draft_dir>", file=sys.stderr)
        sys.exit(1)

    draft_dir = Path(sys.argv[1]).resolve()
    if not draft_dir.is_dir():
        print(f"Not a directory: {draft_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        ok = publish(draft_dir)
        sys.exit(0 if ok else 1)
    except (FileNotFoundError, ValueError, Exception) as e:
        print(f"publish failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
