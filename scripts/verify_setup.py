#!/usr/bin/env python3
"""Verify pipeline setup. Run before generate_batch. Exits 1 if anything missing."""
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
errors = []

# .env
if not (PROJECT_ROOT / ".env").exists():
    errors.append(".env missing. Copy from .env.example and add LATE_API_KEY.")
else:
    env_text = (PROJECT_ROOT / ".env").read_text().lower()
    if "your_late_api_key" in env_text or ("late_api_key" in env_text and "sk_" not in env_text):
        errors.append(".env has placeholder. Replace with real LATE_API_KEY.")
    if "xai_api_key" not in env_text or ("xai_api_key" in env_text and "xai-" not in env_text):
        errors.append(".env: XAI_API_KEY required for content generation.")

# config/accounts.yaml
accounts = PROJECT_ROOT / "config" / "accounts.yaml"
if not accounts.exists():
    errors.append("config/accounts.yaml missing.")
else:
    import yaml
    data = yaml.safe_load(accounts.read_text()) or {}
    has_valid = False
    for persona, cfg in data.items():
        if not isinstance(cfg, dict):
            continue
        for key in ("tiktok_account_id", "instagram_account_id", "reels_profile_id"):
            val = cfg.get(key)
            if val and isinstance(val, str) and not val.startswith("YOUR_"):
                has_valid = True
                break
        if has_valid:
            break
    if not has_valid:
        errors.append("config/accounts.yaml needs at least one real account ID (from GET /v1/accounts).")

# openclaw (npm global: %APPDATA%\npm\openclaw.cmd on Windows)
openclaw_ok = shutil.which("openclaw")
if not openclaw_ok and os.name == "nt":
    npm_openclaw = os.path.join(os.environ.get("APPDATA", ""), "npm", "openclaw.cmd")
    openclaw_ok = npm_openclaw if os.path.isfile(npm_openclaw) else None
if not openclaw_ok:
    errors.append("openclaw not found. Install with: npm install -g openclaw")

# ffmpeg (needed for build_media resize; optional if Imagine returns correct size)
if not shutil.which("ffmpeg"):
    errors.append("ffmpeg not on PATH. Install ffmpeg for video assembly.")

if errors:
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    print("\nFix the above, then run verify_setup.py again.", file=sys.stderr)
    sys.exit(1)
print("Setup OK.")
sys.exit(0)
