-- Timestamped transcript segments for YouTube shadowing (per-sentence playback).

ALTER TABLE public.youtube_gem
ADD COLUMN IF NOT EXISTS transcript_segments jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.youtube_gem.transcript_segments IS
    'JSON array of {text, start_time, end_time} for shadowing; times in seconds from video start.';
