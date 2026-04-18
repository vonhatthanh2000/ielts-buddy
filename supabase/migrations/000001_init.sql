-- Initial schema for IELTS Assistant (Postgres / Supabase): accounts, profiles, sentences.
-- Apply migrations in order. See 000002 for mistakes, improvements, and analyses.

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
-- 2. profiles (learner profiles under one login)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id uuid NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    display_name text NOT NULL,
    avatar_url text,
    accent_color text,
    CONSTRAINT profiles_display_name_len CHECK (
        char_length(display_name) >= 1 AND char_length(display_name) <= 120
    )
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_created ON public.profiles (user_id, created_at ASC);

COMMENT ON TABLE public.profiles IS 'Selectable profiles under one login (e.g. family); display_name for labels/initials.';
COMMENT ON COLUMN public.profiles.avatar_url IS 'Optional image URL for circular avatar.';
COMMENT ON COLUMN public.profiles.accent_color IS 'Optional UI hint (e.g. hex) when no avatar image.';

-- ---------------------------------------------------------------------------
-- 3. sentences (scoped to profile_id)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.sentences (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    profile_id uuid NOT NULL REFERENCES public.profiles (id) ON DELETE CASCADE,
    original text NOT NULL,
    corrected text NOT NULL,
    "natural" text NOT NULL,
    has_mistakes boolean NOT NULL DEFAULT false,
    analyzed boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_sentences_profile_id ON public.sentences (profile_id);
CREATE INDEX IF NOT EXISTS idx_sentences_created_at ON public.sentences (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sentences_profile_analyzed ON public.sentences (profile_id, analyzed) WHERE analyzed = false;
CREATE INDEX IF NOT EXISTS idx_sentence_improvements_profile ON public.sentences (profile_id) INCLUDE (created_at);

COMMENT ON TABLE public.sentences IS 'One corrected sentence run, owned by a learner profile.';
COMMENT ON COLUMN public.sentences.analyzed IS 'Whether this sentence has been included in a batch analysis report.';
