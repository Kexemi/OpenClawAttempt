#!/usr/bin/env python3
"""
Preview backend: serves drafts, Post and Retry endpoints.
Run: python preview/app.py
Open: http://localhost:8080
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_ROOT / "drafts"

# Allow importing from scripts/
_scripts = PROJECT_ROOT / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

# Job store for progress reporting: { job_id: { status, step, message, progress, error } }
_generate_jobs: dict = {}
_jobs_lock = threading.Lock()

# Load .env from project root
_dotenv_path = PROJECT_ROOT / ".env"
if _dotenv_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_dotenv_path)

app = Flask(__name__, static_folder=".", static_url_path="")


def _call_xai(prompt: str, timeout: int = 120) -> str:
    """Call xAI chat completions API. Returns assistant content."""
    key = os.environ.get("XAI_API_KEY")
    if not key or key.startswith("your_"):
        raise ValueError("XAI_API_KEY not set in .env")

    import urllib.request
    body = json.dumps({
        "model": "grok-3-mini",
        "messages": [
            {"role": "system", "content": (
                "You regenerate nostalgia content drafts for TikTok/Instagram Reels. "
                "Respond with ONLY a JSON object:\n"
                '{"drafts":[{"account":"...","platform":"tiktok","caption":"...","hashtags":"#...","hook":"...",'
                '"asset_type":"video","video_prompt":"...","voiceover_text":"...","music_style":"..."}]}\n'
                "video_prompt: visual scene description. voiceover_text: narrator says (often hook). "
                "music_style: background music style. For asset_type image, omit voiceover_text and music_style."
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def list_drafts(status_filter: str | None = None) -> list[dict]:
    """List drafts, optionally filtered by status. Sort newest first."""
    results = []
    if not DRAFTS_DIR.exists():
        return results

    for draft_dir in sorted(DRAFTS_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        if not draft_dir.is_dir() or draft_dir.name.startswith("."):
            continue
        if draft_dir.name == "failed":
            continue

        content_path = draft_dir / "content.json"
        if not content_path.exists():
            continue

        try:
            content = json.loads(content_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        s = content.get("status", "pending")
        if status_filter == "all" or s in ("pending", "video_pending"):
            draft_id = draft_dir.name
            has_video = (draft_dir / "video.mp4").exists()
            has_image = (draft_dir / "image.png").exists()
            results.append({
                "id": draft_id,
                "account": content.get("account", ""),
                "platform": content.get("platform", ""),
                "caption": content.get("caption", ""),
                "hashtags": content.get("hashtags", ""),
                "hook": content.get("hook", ""),
                "status": s,
                "has_media": has_video or has_image,
                "media_type": "video" if has_video else ("image" if has_image else None),
            })

    return results


def get_draft_path(draft_id: str) -> Path | None:
    """Return draft directory if it exists and is valid."""
    safe_id = secure_filename(draft_id)
    if safe_id != draft_id:
        return None
    path = DRAFTS_DIR / safe_id
    if path.exists() and path.is_dir() and (path / "content.json").exists():
        return path
    return None


@app.route("/")
def index():
    return send_file(Path(__file__).parent / "index.html")


def _run_generate_job(job_id: str, count: int, accounts: list[str]) -> None:
    """Background worker: run generation and update job progress."""
    from generate_batch import run_generate

    def progress(step: str, message: str, pct: float):
        with _jobs_lock:
            if job_id in _generate_jobs:
                _generate_jobs[job_id].update(
                    step=step,
                    message=message,
                    progress=round(pct * 100),
                )

    try:
        with _jobs_lock:
            _generate_jobs[job_id]["status"] = "running"
        created, err = run_generate(count=count, accounts=accounts, progress_callback=progress)
        with _jobs_lock:
            if job_id in _generate_jobs:
                if err:
                    _generate_jobs[job_id].update(status="failed", error=err, progress=0)
                else:
                    _generate_jobs[job_id].update(status="done", message="Drafts created", progress=100)
    except Exception as e:
        with _jobs_lock:
            if job_id in _generate_jobs:
                _generate_jobs[job_id].update(status="failed", error=str(e), progress=0)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Start generation job. Returns job_id. Poll /api/generate/status for progress."""
    data = request.get_json(silent=True) or {}
    count = data.get("count", 1)
    accounts = data.get("accounts", ["genz", "genx", "millennial"])
    if not isinstance(accounts, list) or not accounts:
        accounts = ["genz", "genx", "millennial"]

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _generate_jobs[job_id] = {
            "status": "started",
            "step": "queued",
            "message": "Starting...",
            "progress": 0,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_generate_job,
        args=(job_id, count, accounts),
        daemon=True,
    )
    thread.start()

    return jsonify({"success": True, "job_id": job_id})


@app.route("/api/generate/status")
def api_generate_status():
    """Get generation job progress. Query: job_id"""
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id required"}), 400
    with _jobs_lock:
        job = _generate_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "step": job.get("step", ""),
        "message": job.get("message", ""),
        "progress": job.get("progress", 0),
        "error": job.get("error"),
    })


@app.route("/api/drafts")
def api_drafts():
    status = request.args.get("status", "pending")
    drafts = list_drafts(status)
    return jsonify(drafts)


@app.route("/api/drafts/<draft_id>/media")
def api_draft_media(draft_id):
    path = get_draft_path(draft_id)
    if not path:
        return jsonify({"error": "Draft not found"}), 404

    if (path / "video.mp4").exists():
        return send_file(path / "video.mp4", mimetype="video/mp4")
    if (path / "image.png").exists():
        return send_file(path / "image.png", mimetype="image/png")

    return jsonify({"error": "No media"}), 404


@app.route("/api/drafts/<draft_id>/post", methods=["POST"])
def api_post(draft_id):
    path = get_draft_path(draft_id)
    if not path:
        return jsonify({"error": "Draft not found"}), 404

    content_path = path / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))

    if content.get("status") == "published":
        return jsonify({"success": True, "message": "Already published"})

    # Call publish_to_late
    try:
        publish_script = PROJECT_ROOT / "scripts" / "publish_to_late.py"
        result = subprocess.run(
            [sys.executable, str(publish_script), str(path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            content["status"] = "failed"
            content_path.write_text(json.dumps(content, indent=2), encoding="utf-8")
            return jsonify({"success": False, "error": result.stderr or result.stdout}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Publish timeout"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    content["status"] = "published"
    content_path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return jsonify({"success": True})


@app.route("/api/drafts/<draft_id>/retry", methods=["POST"])
def api_retry(draft_id):
    path = get_draft_path(draft_id)
    if not path:
        return jsonify({"error": "Draft not found"}), 404

    feedback = ""
    if request.is_json:
        data = request.get_json() or {}
        feedback = data.get("feedback", "")

    content_path = path / "content.json"
    content = json.loads(content_path.read_text(encoding="utf-8"))
    account = content.get("account", "genz")
    spec = (path / "spec.md").read_text(encoding="utf-8") if (path / "spec.md").exists() else ""

    message = (
        f"Regenerate draft {draft_id} for account {account}. "
        f"Previous spec: {spec[:500]}"
    )
    if feedback:
        message += f" User feedback: {feedback}"

    try:
        output = _call_xai(message)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    # Parse JSON from output
    import re
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", output)
    if not match:
        match = re.search(r"\{[\s\S]*\"drafts\"[\s\S]*\}", output)
    if not match:
        return jsonify({"success": False, "error": "Could not parse output"}), 500

    try:
        json_str = match.group(1) if match.lastindex else match.group(0)
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "Invalid JSON in output"}), 500

    drafts = data.get("drafts", [])
    if not drafts:
        return jsonify({"success": False, "error": "No drafts in output"}), 500

    d = drafts[0]
    required = ("account", "caption", "hashtags", "hook", "asset_type", "video_prompt")
    if not all(k in d for k in required):
        return jsonify({"success": False, "error": "Missing fields in draft"}), 500
    if d.get("asset_type") == "video" and not all(k in d for k in ("voiceover_text", "music_style")):
        return jsonify({"success": False, "error": "Missing voiceover_text or music_style for video"}), 500

    # Atomic replace: write to temp, then rename
    with tempfile.TemporaryDirectory(dir=DRAFTS_DIR) as tmpdir:
        tmp_path = Path(tmpdir)
        new_content = {
            "account": d["account"],
            "platform": d.get("platform", "tiktok"),
            "caption": d["caption"],
            "hashtags": d["hashtags"],
            "hook": d["hook"],
            "asset_type": d["asset_type"],
            "video_prompt": d["video_prompt"],
            "status": "pending",
        }
        if d.get("asset_type") == "video":
            new_content["voiceover_text"] = d["voiceover_text"]
            new_content["music_style"] = d["music_style"]
        (tmp_path / "content.json").write_text(json.dumps(new_content, indent=2), encoding="utf-8")
        (tmp_path / "spec.md").write_text(f"# {draft_id}\n\n{d.get('caption','')}", encoding="utf-8")

        # Run build_media - must succeed, no fallback
        build_script = PROJECT_ROOT / "scripts" / "build_media.py"
        if build_script.exists():
            result = subprocess.run(
                [sys.executable, str(build_script), str(tmp_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 min — Imagine video can be slow
            )
            if result.returncode != 0:
                return jsonify({
                    "success": False,
                    "error": f"build_media failed: {result.stderr or result.stdout}"
                }), 500

        # Move temp contents over existing draft
        for f in tmp_path.iterdir():
            shutil.move(str(f), str(path / f.name))

    return jsonify({"success": True, "id": draft_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
