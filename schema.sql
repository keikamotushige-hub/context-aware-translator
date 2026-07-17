-- Run this in the Supabase SQL Editor to create the translations table.
CREATE TABLE IF NOT EXISTS translations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  original_text TEXT NOT NULL,
  translated_text TEXT NOT NULL,
  target_audience TEXT NOT NULL,
  target_language TEXT NOT NULL DEFAULT '日本語',
  source_type TEXT NOT NULL DEFAULT 'text',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE translations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can insert own translations" ON translations;
CREATE POLICY "Users can insert own translations"
ON translations FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can read own translations" ON translations;
CREATE POLICY "Users can read own translations"
ON translations FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS translations_user_id_created_at_idx
ON translations (user_id, created_at DESC);
