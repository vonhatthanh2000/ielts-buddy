-- YouTube video analysis table (youtube_gem)
-- Stores AI-analyzed YouTube transcripts with extracted learning content
-- Requires: public.profiles (from 000001_init.sql)

-- ---------------------------------------------------------------------------
-- 1. youtube_gem (main analysis table)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.youtube_gem (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    video_title text NOT NULL,
    video_url text NOT NULL,
    transcript text NOT NULL,
    useful_sentences jsonb NOT NULL DEFAULT '[]'::jsonb,
    grammar_patterns jsonb NOT NULL DEFAULT '[]'::jsonb,
    everyday_phrases jsonb NOT NULL DEFAULT '[]'::jsonb,
    learning_tip text
);

CREATE INDEX IF NOT EXISTS idx_youtube_gem_profile_id ON public.youtube_gem (profile_id);
CREATE INDEX IF NOT EXISTS idx_youtube_gem_created_at ON public.youtube_gem (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_youtube_gem_video_url ON public.youtube_gem (video_url);

COMMENT ON TABLE public.youtube_gem IS 'AI-analyzed YouTube videos with extracted learning content (sentences, grammar, phrases).';
COMMENT ON COLUMN public.youtube_gem.video_title IS 'Title of the YouTube video';
COMMENT ON COLUMN public.youtube_gem.video_url IS 'Full YouTube URL that was analyzed';
COMMENT ON COLUMN public.youtube_gem.transcript IS 'Full transcript text extracted from the video';
COMMENT ON COLUMN public.youtube_gem.useful_sentences IS 'JSON array of useful sentences with sentence, why_useful, grammar_pattern, usage_context';
COMMENT ON COLUMN public.youtube_gem.grammar_patterns IS 'JSON array of grammar patterns with pattern, example, usage';
COMMENT ON COLUMN public.youtube_gem.everyday_phrases IS 'JSON array of everyday phrases with phrase, meaning, usage_context';
COMMENT ON COLUMN public.youtube_gem.learning_tip IS 'One practical tip for improving spoken English';
