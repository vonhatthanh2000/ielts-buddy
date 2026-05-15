# Docker

Run the API in a container with **faster-whisper** for transcription (YouTube, speech). On Apple Silicon with `mlx-whisper` installed locally, the app still prefers MLX when not using Docker.

Shadowing routes are commented out in `main.py` (feature unused).

## Prerequisites

- Docker and Docker Compose
- `.env` with at least `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SESSION_SECRET` (copy from `.env.example`)

## Quick start

```bash
cp .env.example .env
# edit .env with your keys

docker compose up --build
```

API: `http://localhost:8000`  
Health: `GET /health`

## Build / run without Compose

```bash
docker build -t ielts-assistant .
docker run --rm -p 8000:8000 --env-file .env ielts-assistant
```

## Whisper in Docker

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `base` | faster-whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`, …) |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` if GPU available |
| `WHISPER_COMPUTE_TYPE` | `int8` | e.g. `int8`, `float16` (GPU) |

First YouTube analyze or upload may take a while while the model downloads. Compose mounts a volume on `whisper-cache` to persist Hugging Face weights.

## Notes

- **ffmpeg** and **yt-dlp** are included for YouTube audio download.
- MLX Whisper is **not** installed in the image (Linux); use local venv on Mac for MLX.
- Supabase migrations are not applied by the container; run them against your project separately.
