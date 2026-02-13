#!/usr/bin/env python3
"""
Generate nostalgia content drafts via xAI API (direct).
Uses XAI_API_KEY to call grok, parses JSON output, writes drafts to drafts/, runs build_video.
(OpenClaw remains available for scheduled tasks and Discord.)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

# Resolve project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv = PROJECT_ROOT / ".env"
if _dotenv.exists():
    from dotenv import load_dotenv
    load_dotenv(_dotenv)
DRAFTS_DIR = PROJECT_ROOT / "drafts"
FAILED_DIR = PROJECT_ROOT / "drafts" / "failed"
PERSONAS_DIR = PROJECT_ROOT / "personas"


def load_persona(account: str) -> str:
    """Load persona YAML content for inclusion in prompt."""
    path = PERSONAS_DIR / f"{account}.yaml"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def extract_json_from_output(text: str) -> dict | None:
    """Extract JSON block from OpenClaw output. Handles markdown code blocks."""
    # Try markdown code block first
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try raw JSON object
    match = re.search(r"\{[\s\S]*\"drafts\"[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def validate_draft(d: dict) -> bool:
    """Validate a single draft has required fields."""
    required = ["account", "platform", "caption", "hashtags", "hook", "asset_type", "video_prompt"]
    if not all(k in d and d[k] for k in required):
        return False
    if d.get("asset_type") == "video":
        return all(k in d and d[k] for k in ("voiceover_text", "music_style"))
    return True


def generate_draft_id(account: str, seq: int) -> str:
    """Generate draft folder ID: YYYY-MM-DD-{account}-{seq:03d}"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{today}-{account}-{seq:03d}"


def call_xai(prompt: str, timeout: int = 120) -> str:
    """Call xAI chat completions API directly. Returns assistant content."""
    key = os.environ.get("XAI_API_KEY")
    if not key or key.startswith("your_"):
        raise ValueError("XAI_API_KEY not set in .env")

    import requests
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    # Try grok-4 first (current), then grok-3-mini, then grok-beta
    for model in ("grok-4", "grok-3-mini", "grok-beta"):
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": (
                    "You generate nostalgia content drafts for TikTok/Instagram Reels. "
                    "Always respond with ONLY a JSON object in this exact format, no other text:\n"
                    '{"drafts": [{"account":"...","platform":"tiktok","caption":"...","hashtags":"#...","hook":"...",'
                    '"asset_type":"video","video_prompt":"...","voiceover_text":"...","music_style":"..."}]}\n'
                    "video_prompt: visual scene description for AI video generation (e.g. cozy 2000s bedroom, Webkinz on shelf). "
                    "voiceover_text: text for narrator to say (often the hook). "
                    "music_style: background music style (e.g. upbeat 2000s pop, nostalgic). "
                    "For asset_type image, omit voiceover_text and music_style."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                return msg.get("content", "")
            if resp.status_code == 403:
                hint = resp.text
                try:
                    err = resp.json()
                    hint = err.get("error", {}).get("message", hint) if isinstance(err.get("error"), dict) else err.get("message", hint)
                except Exception:
                    pass
                if model != "grok-beta":
                    continue
                raise RuntimeError(
                    f"xAI API 403 (Cloudflare blocked). Error 1010 often means your IP/region is blocked. "
                    f"Try: 1) VPN to US, 2) run from a different network, 3) check console.x.ai model access. Last: {hint}"
                )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            if "403" in str(e):
                if model != "grok-beta":
                    continue
                raise RuntimeError(
                    f"xAI API 403. Error 1010 = Cloudflare blocking. Try VPN (US) or different network."
                ) from e
            raise


def write_draft(draft: dict, draft_id: str) -> Path:
    """Write draft to drafts/{draft_id}/."""
    draft_dir = DRAFTS_DIR / draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)

    content = {
        "account": draft["account"],
        "platform": draft["platform"],
        "caption": draft["caption"],
        "hashtags": draft["hashtags"],
        "hook": draft["hook"],
        "asset_type": draft["asset_type"],
        "video_prompt": draft["video_prompt"],
        "status": "pending",
    }
    if draft.get("asset_type") == "video":
        content["voiceover_text"] = draft["voiceover_text"]
        content["music_style"] = draft["music_style"]
    (draft_dir / "content.json").write_text(json.dumps(content, indent=2), encoding="utf-8")

    spec = f"# {draft_id}\n\n{draft.get('caption', '')}\n\nVideo prompt: {draft.get('video_prompt', '')}"
    (draft_dir / "spec.md").write_text(spec, encoding="utf-8")

    return draft_dir




def run_generate(
    count: int = 1,
    accounts: list[str] | None = None,
    no_media: bool = False,
    progress_callback: Callable[[str, str, float], None] | None = None,
) -> tuple[list[Path], str | None]:
    """
    Run generation. Returns (list of created draft dirs, error message or None).
    progress_callback(step: str, message: str, progress: float) called with progress 0.0-1.0.
    """
    if accounts is None:
        accounts = ["genz", "genx", "millennial"]

    def progress(step: str, msg: str, pct: float):
        if progress_callback:
            progress_callback(step, msg, pct)
        else:
            print(f"[{pct:.0%}] {step}: {msg}", file=sys.stderr)

    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    total_steps = len(accounts) * 2  # copy + media per account (simplified)
    step_idx = 0

    for ai, account in enumerate(accounts):
        progress("grok", f"Generating copy for {account}...", (ai + 0.2) / max(len(accounts), 1))
        persona = load_persona(account)
        prompt = (
            f"Generate {count} nostalgia content draft(s) for the {account} account. "
            f"Use the persona from personas/{account}.yaml. "
            "Output platform-optimized caption, hashtags, hook for TikTok/Reels. "
            "Include video_prompt (visual scene), voiceover_text (narrator says hook), music_style (background music). "
            "End your response with a JSON block: {{\"drafts\": [{{...}}]}}\n\n"
            f"Persona:\n{persona}"
        )

        output = call_xai(prompt)
        data = extract_json_from_output(output)

        if not data or "drafts" not in data:
            failed_path = FAILED_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{account}.txt"
            failed_path.write_text(output or "(no output)", encoding="utf-8")
            return created, f"Parse failed for {account}. Output saved to {failed_path.name}"

        progress("grok", f"Copy ready for {account}", (ai + 0.5) / max(len(accounts), 1))

        for i, d in enumerate(data["drafts"]):
            required = ["account", "platform", "caption", "hashtags", "hook", "asset_type", "video_prompt"]
            if d.get("asset_type") == "video":
                required.extend(["voiceover_text", "music_style"])
            missing = [k for k in required if k not in d or not d[k]]
            if missing:
                return created, f"Invalid draft for {account}: missing {missing}"

            draft_id = generate_draft_id(account, i + 1)
            draft_dir = write_draft(d, draft_id)
            created.append(draft_dir)

            if not no_media:
                progress("imagine", f"Creating video for {draft_id}... (may take 5–20 min)", (ai + 0.6) / max(len(accounts), 1))
                result = subprocess.run(
                    [sys.executable, str(PROJECT_ROOT / "scripts" / "build_media.py"), str(draft_dir)],
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=1800,  # 30 min — Imagine video can be slow
                )
                if result.returncode != 0:
                    return created, f"build_media failed for {draft_id}: {result.stderr or result.stdout}"
                progress("imagine", f"Video ready: {draft_id}", (ai + 1.0) / max(len(accounts), 1))

    return created, None


def main():
    parser = argparse.ArgumentParser(description="Generate nostalgia content drafts via xAI API")
    parser.add_argument("--count", "-n", type=int, default=1, help="Drafts per account (default: 1)")
    parser.add_argument("--accounts", nargs="+", default=["genz", "genx", "millennial"],
                        help="Accounts to generate for")
    parser.add_argument("--no-media", action="store_true", help="Skip build_media (text-only drafts)")
    args = parser.parse_args()

    def log_progress(step: str, msg: str, pct: float):
        print(f"[{pct:.0%}] {step}: {msg}", file=sys.stderr)

    created, err = run_generate(
        count=args.count,
        accounts=args.accounts,
        no_media=args.no_media,
        progress_callback=log_progress,
    )
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)
    for d in created:
        print(f"Created: {d.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
