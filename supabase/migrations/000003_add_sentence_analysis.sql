-- Add sentence analysis tracking and simple markdown storage

-- ---------------------------------------------------------------------------
-- 1. Add analyzed flag to sentences table
-- ---------------------------------------------------------------------------
ALTER TABLE public.sentences
ADD COLUMN IF NOT EXISTS analyzed boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.sentences.analyzed IS 'Whether this sentence has been included in a batch analysis report';

-- Index for efficient querying of unanalyzed sentences
CREATE INDEX IF NOT EXISTS idx_sentences_analyzed ON public.sentences (analyzed) WHERE analyzed = false;
CREATE INDEX IF NOT EXISTS idx_sentences_user_analyzed ON public.sentences (user_id, analyzed) WHERE analyzed = false;

-- ---------------------------------------------------------------------------
-- 2. sentence_analyses - Simple markdown storage for frontend display
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentence_analyses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id uuid NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    content text NOT NULL  -- Full markdown content for frontend display
);

CREATE INDEX IF NOT EXISTS idx_sentence_analyses_user_id ON public.sentence_analyses (user_id);
CREATE INDEX IF NOT EXISTS idx_sentence_analyses_created_at ON public.sentence_analyses (created_at DESC);

COMMENT ON TABLE public.sentence_analyses IS 'Markdown analysis reports for unreviewed sentences';
COMMENT ON COLUMN public.sentence_analyses.content IS 'Full markdown report content for frontend rendering';
