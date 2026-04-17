-- Initial schema for IELTS Assistant (Postgres / Supabase).
-- Apply in Supabase: SQL Editor → New query → paste → Run.

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    username text,
    email text NOT NULL,
    password_hash text NOT NULL,
    name text NOT NULL,
    CONSTRAINT users_username_unique UNIQUE (username),
    CONSTRAINT users_email_unique UNIQUE (email)
);

COMMENT ON TABLE public.users IS 'Application accounts; usernames and emails should be stored lowercase.';

-- ---------------------------------------------------------------------------
-- 2. sentences
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id uuid NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    original text NOT NULL,
    corrected text NOT NULL,
    "natural" text NOT NULL,
    has_mistakes boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_sentences_user_id ON public.sentences (user_id);
CREATE INDEX IF NOT EXISTS idx_sentences_created_at ON public.sentences (created_at DESC);

COMMENT ON TABLE public.sentences IS 'One corrected sentence run, owned by a user.';

-- ---------------------------------------------------------------------------
-- 3. sentence_mistakes
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
