-- Migration 000006: Remove youtube_gem_id from speech_recordings and create shadowing_attempts table

-- ---------------------------------------------------------------------------
-- 1. Remove youtube_gem_id from speech_recordings (if it exists)
-- ---------------------------------------------------------------------------
ALTER TABLE IF EXISTS public.speech_recordings
    DROP COLUMN IF EXISTS youtube_gem_id;

DROP INDEX IF EXISTS idx_speech_recordings_youtube_gem;

-- ---------------------------------------------------------------------------
-- 2. Create shadowing_attempts table for YouTube shadowing practice
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.shadowing_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,

    -- Reference to the YouTube video being shadowed
    youtube_gem_id uuid NOT NULL REFERENCES public.youtube_gem (id) ON DELETE CASCADE,

    -- The specific sentence being practiced
    target_sentence text NOT NULL,
    target_sentence_index integer,

    -- Audio storage
    audio_url text NOT NULL,
    audio_duration_seconds integer,

    -- Transcription of user's speech
    user_transcript text NOT NULL DEFAULT '',

    -- Simple evaluation result
    similarity_score integer CHECK (similarity_score >= 0 AND similarity_score <= 100),
    word_differences jsonb DEFAULT '[]'::jsonb,
    feedback text
);

CREATE INDEX IF NOT EXISTS idx_shadowing_attempts_profile_id ON public.shadowing_attempts (profile_id);
CREATE INDEX IF NOT EXISTS idx_shadowing_attempts_youtube_gem ON public.shadowing_attempts (youtube_gem_id);
CREATE INDEX IF NOT EXISTS idx_shadowing_attempts_created_at ON public.shadowing_attempts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shadowing_attempts_profile_video ON public.shadowing_attempts (profile_id, youtube_gem_id);

COMMENT ON TABLE public.shadowing_attempts IS 'User shadowing practice attempts for mimicking YouTube video sentences.';
COMMENT ON COLUMN public.shadowing_attempts.target_sentence IS 'The exact sentence from the YouTube transcript being practiced.';
COMMENT ON COLUMN public.shadowing_attempts.target_sentence_index IS 'Index of the sentence in the transcript (for ordering).';
COMMENT ON COLUMN public.shadowing_attempts.similarity_score IS 'Overall similarity score 0-100 comparing user transcript to target.';
COMMENT ON COLUMN public.shadowing_attempts.word_differences IS 'Array of word differences: {expected, actual}.';
COMMENT ON COLUMN public.shadowing_attempts.feedback IS 'Brief feedback on the shadowing attempt.';
