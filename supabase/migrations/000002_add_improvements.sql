-- Add improvements table for natural phrase alternatives

-- ---------------------------------------------------------------------------
-- 1. sentence_improvements
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
CREATE INDEX IF NOT EXISTS idx_sentence_improvements_user ON public.sentences (user_id) INCLUDE (created_at);

COMMENT ON TABLE public.sentence_improvements IS 'Natural phrase improvements for revision (e.g., I want to find -> I am looking for). Stores alternative, more idiomatic expressions.';
COMMENT ON COLUMN public.sentence_improvements.original_phrase IS 'The original phrasing from the user sentence (grammatically acceptable but less natural)';
COMMENT ON COLUMN public.sentence_improvements.improved_phrase IS 'More natural, native-like alternative expressing the same meaning';
COMMENT ON COLUMN public.sentence_improvements.explanation IS 'Why the improved version is more natural (optional)';
COMMENT ON COLUMN public.sentence_improvements.context IS 'Full sentence context for the improvement';
