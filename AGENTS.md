# OpenClawAttempt — Agent Instructions

## Project goal

Nostalgia content pipeline: generate drafts (copy + video via xAI Imagine), preview in a web UI, publish to TikTok/Instagram via Late API. The pipeline must work end-to-end with **no fallbacks** — if something is missing, fail with a clear error.

## Tech stack

- **Python 3.9+** — scripts in `scripts/`, preview in `preview/`
- **xAI** — Grok (chat) for copy, Imagine (video/image) for media. Uses `XAI_API_KEY`
- **Late API** — publishing. Uses `LATE_API_KEY`
- **Config** — `config/accounts.yaml`, `personas/*.yaml`, `.env` (secrets; use Cursor Secrets in cloud)

## How to verify the pipeline works

1. **Setup**
   ```bash
   python scripts/verify_setup.py
   ```
   Fix any reported errors (missing .env keys, ffmpeg, etc.).

2. **Generate one draft**
   ```bash
   python scripts/generate_batch.py --count 1 --accounts genz
   ```
   Must complete without timeout. Creates a draft under `drafts/` with `content.json` and `video.mp4` (or `image.png`).

3. **Preview**
   ```bash
   python preview/app.py
   ```
   Open http://localhost:8080 — drafts should list and video should play (not a red placeholder).

4. **Publish** (optional)
   Use the Post button in the UI; requires `LATE_API_KEY` and `config/accounts.yaml` with valid account IDs.

## Rules

- **No fallbacks** — Do not add generic/placeholder assets when the real asset is missing. Fail with a clear error instead.
- **Asset generation** — Media comes from xAI Imagine (video or image). No asset library lookup.
- **Draft schema** — `content.json` must have: `account`, `platform`, `caption`, `hashtags`, `hook`, `asset_type`, `video_prompt`; for video also `voiceover_text`, `music_style`.

## Key paths

- `scripts/generate_batch.py` — entrypoint for generation (Grok + build_media)
- `scripts/build_media.py` — calls Imagine for video/image
- `scripts/imagine_client.py` — xAI Imagine API client
- `preview/app.py` — Flask server; `/api/generate` starts a job, `/api/generate/status?job_id=` for progress
