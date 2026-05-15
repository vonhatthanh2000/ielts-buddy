# Vercel deployment

## Shadowing

Shadowing is **commented out** in `main.py` (routes not registered). Hide shadowing UI in the frontend.

To re-enable: uncomment the `shadowing_router` import and `app.include_router` lines in `main.py`.

## Environment variables

Set in the Vercel project (same as `.env.example`):

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SESSION_SECRET`

YouTube analyze and speech upload use transcription and heavy dependencies; you may hit timeouts or size limits on serverless.
