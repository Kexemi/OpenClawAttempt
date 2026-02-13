# Cursor Cloud Agent Setup — Checklist

Use this so a Cursor **Cloud Agent** can work on this repo overnight (or on demand). Do these steps once.

---

## 1. Put the project on GitHub

If the repo is not on GitHub yet:

1. Create a new repository on GitHub (e.g. `OpenClawAttempt`).
2. In this folder (OpenClawAttempt), run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/OpenClawAttempt.git
   git push -u origin main
   ```
3. Replace `YOUR_USERNAME` with your GitHub username.

---

## 2. Run Cloud Agent Setup in Cursor

1. Open this project in **Cursor**.
2. **Ctrl+Shift+P** (or Cmd+Shift+P on Mac) → run **"Cursor: Start Cloud Agent Setup"**.
3. Follow the wizard:
   - **Connect GitHub** — grant Cursor read/write to this repo.
   - **Base environment** — the repo already has `.cursor/environment.json` with `pip install -r requirements.txt`. Use the default or confirm it.
   - **Create a snapshot** — let it run the install and save the snapshot.
   - You can leave **Start command** and **Terminals** empty unless you want the preview server running in the cloud.

---

## 3. Add secrets (required for generation)

Cloud agents need your API keys. **Do not commit `.env`.**

1. **Cursor Settings** (Ctrl+,) → **Cloud Agents** (or **Features** → **Cloud**) → **Secrets**.
2. Or: [Cursor Dashboard](https://cursor.com/dashboard) → **Cloud Agents** → **Secrets**.

Add these (same names as in `.env`):

| Name           | Description                    |
|----------------|--------------------------------|
| `XAI_API_KEY`  | xAI API key (Grok + Imagine)   |
| `LATE_API_KEY` | Late API key for publishing    |

Use the same values as in your local `.env`. Save.

---

## 4. (Optional) Set default repo

In [Cursor Dashboard → Cloud Agents](https://cursor.com/dashboard?tab=cloud-agents), under **Default repository**, set:

`https://github.com/YOUR_USERNAME/OpenClawAttempt`

so you don’t have to pick the repo every time.

---

## 5. Start an overnight (or any) run

**From Cursor**

1. In the agent input, open the model dropdown and choose **Cloud**.
2. Paste a task, e.g.:

   ```
   Work on this repo. Goal: full pipeline works end-to-end.
   1. Run scripts/verify_setup.py and fix any errors.
   2. Run scripts/generate_batch.py --count 1 --accounts genz and fix any failures.
   3. Iterate until verify_setup passes and generate_batch completes with a real video (no red placeholder).
   4. Open a PR with your changes and a short summary.
   ```

3. Send the message. The agent runs in the cloud; you can close your laptop.

**From the web**

1. Go to [cursor.com/agents](https://cursor.com/agents).
2. Start an agent, select this repo, and use the same task text as above.

---

## 6. Next morning

- In Cursor (or the agents dashboard), check the run status and any **PR** link.
- On GitHub, review the branch and PR, then merge or request changes.

---

## Files added for Cloud Agents

- **`.cursor/environment.json`** — install command and snapshot hint for Cursor.
- **`AGENTS.md`** — project goals and verification steps for the agent.
- **`CLOUD_AGENT_SETUP.md`** — this checklist.

Secrets are only in Cursor Settings; they are not stored in the repo.

---

## Optional: .cursorignore

If you want to keep `.env` and `drafts/` out of agent context, create `.cursorignore` in the project root with:

```
.env
.env.*
*.env.local
drafts/
__pycache__/
venv/
.venv/
```
