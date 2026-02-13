#!/usr/bin/env python3
"""
Publish a draft to Buffer (TikTok + Reels).
Reads draft content.json, loads config/accounts.yaml for profile IDs,
calls Buffer API POST /updates/create with profile_ids array and now=true.

Requires: BUFFER_ACCESS_TOKEN in .env
Buffer API may require video at a public URL; if local file upload is not supported,
this script will need to upload to temp storage first.
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


def load_accounts() -> dict:
    """Load config/accounts.yaml."""
    path = CONFIG_DIR / "accounts.yaml"
    if not path.exists():
        raise FileNotFoundError("config/accounts.yaml not found")
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_buffer_token() -> str:
    """Get Buffer access token from env."""
    token = os.environ.get("BUFFER_ACCESS_TOKEN")
    if not token:
        raise ValueError("BUFFER_ACCESS_TOKEN not set in .env")
    return token


def publish(draft_dir: Path) -> bool:
    """Publish draft to Buffer. Returns True on success."""
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

    profile_ids = [
        accounts[account].get("tiktok_profile_id"),
        accounts[account].get("reels_profile_id"),
    ]
    profile_ids = [p for p in profile_ids if p and not str(p).startswith("YOUR_")]

    if not profile_ids:
        print(f"No valid profile IDs for account '{account}'", file=sys.stderr)
        return False

    token = get_buffer_token()

    media_path = draft_dir / "video.mp4"
    if not media_path.exists():
        media_path = draft_dir / "image.png"

    if media_path.exists():
        raise NotImplementedError(
            f"Draft has {media_path.name} but Buffer API requires a public URL for media. "
            "Implement upload-to-temp-storage (e.g. S3) and pass URL to Buffer, or remove media from draft. "
            "Refusing to post text-only when media exists."
        )

    # Buffer API: POST https://api.bufferapp.com/1/updates/create.json
    url = "https://api.bufferapp.com/1/updates/create.json"
    from urllib.parse import urlencode
    flat = [
        ("access_token", token),
        ("text", text),
        ("now", "true"),
    ]
    for pid in profile_ids:
        flat.append(("profile_ids[]", pid))
    body = urlencode(flat)

    try:
        import urllib.request
        req = urllib.request.Request(url, data=body.encode(), method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if result.get("success"):
                return True
            print("Buffer API error:", result, file=sys.stderr)
            return False
    except Exception as e:
        print(f"Buffer API request failed: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: publish_to_buffer.py <draft_dir>", file=sys.stderr)
        sys.exit(1)

    draft_dir = Path(sys.argv[1]).resolve()
    if not draft_dir.is_dir():
        print(f"Not a directory: {draft_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        ok = publish(draft_dir)
        sys.exit(0 if ok else 1)
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        print(f"publish failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
