/**
 * Ensure AIO visibility tables exist (ops-admin tool, manual ChatGPT audits first).
 * Uses AUTH/DATABASE Postgres via getAuthPgPool — not the finance warehouse.
 */

import { getAuthPgPool } from "@/lib/auth/db";

let ensured = false;

const DDL = `
CREATE TABLE IF NOT EXISTS aio_queries (
  id TEXT PRIMARY KEY,
  query_text TEXT NOT NULL,
  category TEXT NOT NULL,
  intent TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 2,
  baseline_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  target_topic TEXT,
  target_page_hint TEXT,
  notes TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aio_competitors (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  aliases_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS aio_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  source_type TEXT NOT NULL DEFAULT 'manual_chatgpt',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aio_manual_audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID REFERENCES aio_batches(id) ON DELETE SET NULL,
  query_id TEXT REFERENCES aio_queries(id) ON DELETE SET NULL,
  query_text TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  product_note TEXT,
  raw_response TEXT NOT NULL,
  citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  clean_session_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  evaluation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluator_version TEXT NOT NULL DEFAULT 'rules_v1',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_aio_manual_audits_query_id ON aio_manual_audits(query_id);
CREATE INDEX IF NOT EXISTS ix_aio_manual_audits_observed_at ON aio_manual_audits(observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_aio_queries_priority ON aio_queries(priority DESC, category);

CREATE TABLE IF NOT EXISTS aio_content (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  content_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'live',
  published_at DATE,
  hypothesis TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aio_content_query_map (
  content_id TEXT NOT NULL REFERENCES aio_content(id) ON DELETE CASCADE,
  query_id TEXT NOT NULL REFERENCES aio_queries(id) ON DELETE CASCADE,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (content_id, query_id)
);

CREATE TABLE IF NOT EXISTS aio_settings (
  key TEXT PRIMARY KEY,
  value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_aio_content_query_map_query ON aio_content_query_map(query_id);
`;

const ALTERS = `
ALTER TABLE aio_queries ADD COLUMN IF NOT EXISTS pulse_enabled BOOLEAN NOT NULL DEFAULT FALSE;
`;

export async function ensureAioSchema(): Promise<void> {
  if (ensured) return;
  const pool = getAuthPgPool();
  // gen_random_uuid needs pgcrypto on some Postgres installs
  await pool.query(`CREATE EXTENSION IF NOT EXISTS pgcrypto`);
  await pool.query(DDL);
  await pool.query(ALTERS);
  ensured = true;
}

export function resetAioSchemaCache(): void {
  ensured = false;
}
