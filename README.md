# Nostalgia Content Pipeline

OpenClaw-powered pipeline for generating nostalgia content for three generational accounts (Gen Z, Gen X, Millennials). Produces drafts for human approval, then publishes to TikTok and Instagram Reels.

## Quick Start

1. **Verify setup** — `python scripts/verify_setup.py` (reports what's missing)
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**
   - Copy `.env.example` to `.env` and add `BUFFER_ACCESS_TOKEN`
   - Edit `config/accounts.yaml` with your Buffer profile IDs (after connecting TikTok/IG in Buffer)

3. **Populate assets**
   - Add videos/images to `assets/{theme}/` (see plan for structure)
   - Or run with `--no-video` for text-only drafts

4. **Generate drafts**
   ```bash
   python scripts/generate_batch.py --count 1
   ```

5. **Preview and approve**
   ```bash
   python preview/app.py
   ```
   Open http://localhost:8080

6. **Post** — Click Post in the dashboard to publish to Buffer (TikTok + Reels)

## Scheduling

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily (or your preferred frequency)
4. Action: Start a program
   - Program: `python` (or full path to python.exe)
   - Arguments: `scripts/generate_batch.py --count 1`
   - Start in: `C:\path\to\OpenClawAttempt`

### Mac/Linux (cron)

```bash
# Generate 1 draft per account daily at 9 AM
0 9 * * * cd /path/to/OpenClawAttempt && python scripts/generate_batch.py --count 1
```

## Project Structure

```
OpenClawAttempt/
├── personas/       # Gen Z, Gen X, Millennial configs
├── config/         # accounts.yaml, asset_mapping.yaml
├── assets/         # Curated nostalgia clips/images
├── drafts/         # Generated drafts
├── scripts/        # generate_batch, build_video, publish_to_buffer
├── preview/        # Dashboard (app.py, index.html)
└── openclaw_skills/
```

## Requirements

- OpenClaw (installed, on PATH)
- Python 3.9+
- ffmpeg (for video assembly)
- Buffer account with TikTok + Reels connected

## Cursor Cloud Agent (overnight / on-demand)

To have a Cursor Cloud Agent work on this repo autonomously (e.g. overnight), see **[CLOUD_AGENT_SETUP.md](CLOUD_AGENT_SETUP.md)**. It covers GitHub, Cloud Agent setup, secrets, and a sample task prompt.

## Notes

- Publishing uses Late API (`publish_to_late.py`); media is generated via xAI Imagine
- Ensure `openclaw` is on PATH if using OpenClaw; generation can also run via `generate_batch.py` alone
- Draft IDs use format: `YYYY-MM-DD-{account}-{seq}`
