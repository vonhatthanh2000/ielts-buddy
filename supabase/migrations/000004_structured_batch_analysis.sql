-- Migration: Convert sentence_analyses from markdown content to structured JSON
-- Table is empty, so we simply drop the old column and add the new one

-- ---------------------------------------------------------------------------
-- 1. Drop the old markdown content column
-- ---------------------------------------------------------------------------
ALTER TABLE public.sentence_analyses
DROP COLUMN IF EXISTS content;

-- ---------------------------------------------------------------------------
-- 2. Add new JSONB column for structured analysis data
-- ---------------------------------------------------------------------------
ALTER TABLE public.sentence_analyses
ADD COLUMN IF NOT EXISTS analysis_data jsonb NOT NULL DEFAULT '{}'::jsonb;

-- ---------------------------------------------------------------------------
-- 3. Add comment
-- ---------------------------------------------------------------------------
COMMENT ON COLUMN public.sentence_analyses.analysis_data IS 
'Structured JSON analysis report containing executive_summary, mistake_categories, improvement_opportunities, key_takeaways, action_items, and next_steps';
