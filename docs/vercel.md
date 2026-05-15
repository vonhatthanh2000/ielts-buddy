# Vercel deployment

## Do I need to remove packages and reinstall?

**On Vercel:** No. Each deploy installs dependencies fresh. There is no old venv on the server.

**Important:** If this repo has `pyproject.toml`, Vercel uses it (via `uv`) and may **ignore** `requirements.txt`. Runtime deps must be listed under `[project] dependencies` in `pyproject.toml` (they are now).

If a deploy failed after you changed dependencies:

1. Update **`pyproject.toml`** (and keep `requirements.txt` in sync for local/Docker).
2. **Deployments** → **Redeploy** → enable **Clear build cache** once.

**Locally** (only if your venv is broken):

```bash
cd /path/to/ielts-assistant
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # same as Vercel (auth, sentence, profiles)
# optional, for YouTube/speech transcription on your machine:
pip install -r requirements-local.txt    # Mac: adds mlx-whisper, yt-dlp, faster-whisper
# or Docker:
# docker compose up --build                # uses requirements-docker.txt
```

## What runs on Vercel

| Works | Does not work well on serverless |
|-------|----------------------------------|
| Auth, users, profiles | YouTube `/v1/youtube/analyze` (needs yt-dlp + Whisper) |
| Sentence correction | Speech upload (needs Whisper) |
| Health | Shadowing (disabled in `main.py`) |

Use **Docker** or **local** for YouTube/speech features.

## Environment variables

In the Vercel project → **Settings** → **Environment Variables**:

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SESSION_SECRET`

## Files

- `pyproject.toml` — **what Vercel installs** (`[project] dependencies`)
- `requirements.txt` — mirror for local `pip install -r` (keep in sync)
- `requirements-docker.txt` — Docker image (includes transcription)
- `requirements-local.txt` — optional local transcription on Mac
- `vercel.json` — function settings (entrypoint is `main:app` via `tool.vercel`)

## Shadowing

Commented out in `main.py`. Hide shadowing UI in the frontend.
