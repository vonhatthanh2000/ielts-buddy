-- Migration 000007: Update shadowing_attempts to use composite primary key
-- OPTION 2: Start fresh - drops existing data

-- ---------------------------------------------------------------------------
-- 1. Drop existing table and start fresh
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS public.shadowing_attempts;

-- ---------------------------------------------------------------------------
-- 2. Create shadowing_attempts table with composite primary key
-- ---------------------------------------------------------------------------
CREATE TABLE public.shadowing_attempts (
    -- Composite primary key: one attempt per user per sentence per video
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    youtube_gem_id uuid NOT NULL REFERENCES public.youtube_gem (id) ON DELETE CASCADE,
    target_sentence_index integer NOT NULL,
    
    PRIMARY KEY (profile_id, youtube_gem_id, target_sentence_index),

    -- The specific sentence being practiced (stored for convenience)
    target_sentence text NOT NULL,

    -- Audio storage
    audio_url text NOT NULL,
    audio_duration_seconds integer,

    -- Transcription of user's speech
    user_transcript text NOT NULL DEFAULT '',

    -- Simple evaluation result
    similarity_score integer CHECK (similarity_score >= 0 AND similarity_score <= 100),
    word_differences jsonb DEFAULT '[]'::jsonb,
    feedback text,

    -- Track when attempt was created and last updated
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 3. Create indexes for common queries
-- ---------------------------------------------------------------------------
CREATE INDEX idx_shadowing_attempts_youtube_gem ON public.shadowing_attempts (youtube_gem_id);
CREATE INDEX idx_shadowing_attempts_created_at ON public.shadowing_attempts (created_at DESC);
CREATE INDEX idx_shadowing_attempts_profile_video ON public.shadowing_attempts (profile_id, youtube_gem_id);
CREATE INDEX idx_shadowing_attempts_score ON public.shadowing_attempts (similarity_score);

-- ---------------------------------------------------------------------------
-- 4. Create trigger to automatically update updated_at timestamp
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_shadowing_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_shadowing_updated_at
    BEFORE UPDATE ON public.shadowing_attempts
    FOR EACH ROW
    EXECUTE FUNCTION update_shadowing_updated_at();

-- ---------------------------------------------------------------------------
-- 5. Add comments
-- ---------------------------------------------------------------------------
COMMENT ON TABLE public.shadowing_attempts IS 'User shadowing practice attempts for mimicking YouTube video sentences. One record per user per sentence per video (upsert on re-practice).';
COMMENT ON COLUMN public.shadowing_attempts.target_sentence IS 'The exact sentence from the YouTube transcript being practiced.';
COMMENT ON COLUMN public.shadowing_attempts.target_sentence_index IS 'Index of the sentence in the transcript (part of primary key).';
COMMENT ON COLUMN public.shadowing_attempts.similarity_score IS 'Overall similarity score 0-100 comparing user transcript to target.';
COMMENT ON COLUMN public.shadowing_attempts.word_differences IS 'Array of word differences: {expected, actual}.';
COMMENT ON COLUMN public.shadowing_attempts.feedback IS 'Brief feedback on the shadowing attempt.';
