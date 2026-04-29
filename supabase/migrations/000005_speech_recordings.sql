-- Speech recordings table for storing user audio recordings and AI evaluations
-- Used for IELTS speaking practice and pronunciation evaluation

-- ---------------------------------------------------------------------------
-- 1. speech_recordings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.speech_recordings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,

    -- Audio storage
    audio_url text NOT NULL,
    audio_duration_seconds integer,

    -- Transcription
    transcript text NOT NULL DEFAULT '',

    -- AI Evaluation results (stored as JSONB for flexibility)
    overall_score integer CHECK (overall_score >= 0 AND overall_score <= 100),
    pronunciation_score integer CHECK (pronunciation_score >= 0 AND pronunciation_score <= 100),
    fluency_score integer CHECK (fluency_score >= 0 AND fluency_score <= 100),
    grammar_score integer CHECK (grammar_score >= 0 AND grammar_score <= 100),
    vocabulary_score integer CHECK (vocabulary_score >= 0 AND vocabulary_score <= 100),

    -- Detailed feedback (structured data)
    strengths jsonb DEFAULT '[]'::jsonb,
    improvements jsonb DEFAULT '[]'::jsonb,
    detailed_feedback text,
    learning_tip text
);

CREATE INDEX IF NOT EXISTS idx_speech_recordings_profile_id ON public.speech_recordings (profile_id);
CREATE INDEX IF NOT EXISTS idx_speech_recordings_created_at ON public.speech_recordings (created_at DESC);

COMMENT ON TABLE public.speech_recordings IS 'User audio recordings for IELTS speaking practice with AI evaluation.';
COMMENT ON COLUMN public.speech_recordings.audio_url IS 'URL to the stored audio file (e.g., Supabase Storage).';
COMMENT ON COLUMN public.speech_recordings.overall_score IS 'Overall speaking score 0-100.';
COMMENT ON COLUMN public.speech_recordings.pronunciation_score IS 'Pronunciation clarity score 0-100.';
COMMENT ON COLUMN public.speech_recordings.fluency_score IS 'Speech flow and naturalness score 0-100.';
COMMENT ON COLUMN public.speech_recordings.grammar_score IS 'Grammar accuracy score 0-100.';
COMMENT ON COLUMN public.speech_recordings.vocabulary_score IS 'Vocabulary usage score 0-100.';
COMMENT ON COLUMN public.speech_recordings.strengths IS 'Array of strength feedback items as JSON.';
COMMENT ON COLUMN public.speech_recordings.improvements IS 'Array of improvement suggestions as JSON.';
