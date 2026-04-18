-- Mistakes, phrase improvements, and batch markdown analyses.
-- Requires: public.sentences, public.profiles (from 000001_init.sql).

-- ---------------------------------------------------------------------------
-- 1. sentence_mistakes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentence_mistakes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sentence_id uuid NOT NULL REFERENCES public.sentences (id) ON DELETE CASCADE,
    type text NOT NULL,
    original text,
    fix text,
    explanation text
);

CREATE INDEX IF NOT EXISTS idx_sentence_mistakes_sentence_id ON public.sentence_mistakes (sentence_id);

COMMENT ON TABLE public.sentence_mistakes IS 'Normalized mistakes for a sentence (grammar | word_choice | fluency).';
COMMENT ON COLUMN public.sentence_mistakes.type IS 'grammar | word_choice | fluency';

-- ---------------------------------------------------------------------------
-- 2. sentence_improvements
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentence_improvements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    sentence_id uuid NOT NULL REFERENCES public.sentences (id) ON DELETE CASCADE,
    original_phrase text NOT NULL,
    improved_phrase text NOT NULL,
    explanation text,
    context text
);

CREATE INDEX IF NOT EXISTS idx_sentence_improvements_sentence_id ON public.sentence_improvements (sentence_id);

COMMENT ON TABLE public.sentence_improvements IS 'Natural phrase improvements for revision (e.g. I want to find -> I am looking for).';
COMMENT ON COLUMN public.sentence_improvements.original_phrase IS 'The original phrasing from the user sentence (grammatically acceptable but less natural)';
COMMENT ON COLUMN public.sentence_improvements.improved_phrase IS 'More natural, native-like alternative expressing the same meaning';
COMMENT ON COLUMN public.sentence_improvements.explanation IS 'Why the improved version is more natural (optional)';
COMMENT ON COLUMN public.sentence_improvements.context IS 'Full sentence context for the improvement';

-- ---------------------------------------------------------------------------
-- 3. sentence_analyses (markdown reports; scoped to profile_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentence_analyses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    content text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sentence_analyses_profile_id ON public.sentence_analyses (profile_id);
CREATE INDEX IF NOT EXISTS idx_sentence_analyses_created_at ON public.sentence_analyses (created_at DESC);

COMMENT ON TABLE public.sentence_analyses IS 'Markdown analysis reports for unreviewed sentences.';
COMMENT ON COLUMN public.sentence_analyses.content IS 'Full markdown report content for frontend rendering.';
