CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS fatwas (
  id uuid PRIMARY KEY,
  external_id bigint NOT NULL,
  title text NOT NULL,
  question text,
  answer text NOT NULL,
  full_original_text text NOT NULL,
  retrieval_text text NOT NULL,
  answer_segments jsonb NOT NULL DEFAULT '[]',
  follow_up_dialogue jsonb NOT NULL DEFAULT '[]',
  tags jsonb NOT NULL DEFAULT '[]',
  source_collection text NOT NULL CHECK (source_collection IN ('OFFICIAL_HACKATHON_REFERENCE','BINBAZ_REFERENCE','FUTURE_REFERENCE')),
  source_collection_name text NOT NULL,
  source_authority text,
  source_author text,
  scholar text,
  scholars jsonb NOT NULL DEFAULT '[]',
  madhhab text,
  madhhabs jsonb NOT NULL DEFAULT '[]',
  book text,
  volume text,
  page text,
  fatwa_number text,
  category text,
  subcategory text,
  topic text,
  evidence jsonb NOT NULL DEFAULT '[]',
  original_reference jsonb NOT NULL DEFAULT '[]',
  qa_pairs jsonb NOT NULL DEFAULT '[]',
  source_organization text NOT NULL,
  source_domain text NOT NULL,
  source_url text NOT NULL,
  canonical_url text NOT NULL UNIQUE,
  source_type text NOT NULL DEFAULT 'fatwa' CHECK (source_type IN ('fatwa','fiqh_encyclopedia_entry')),
  language text NOT NULL DEFAULT 'ar',
  audio_url text,
  has_audio boolean NOT NULL DEFAULT false,
  original_metadata jsonb NOT NULL DEFAULT '{}',
  scraped_at timestamptz NOT NULL,
  content_hash text NOT NULL,
  UNIQUE (source_collection, external_id)
);

CREATE TABLE IF NOT EXISTS fatwa_categories (
  id uuid PRIMARY KEY,
  external_id bigint,
  name_ar text NOT NULL,
  slug text NOT NULL,
  taxonomy text NOT NULL,
  parent_id uuid REFERENCES fatwa_categories(id),
  source_url text NOT NULL,
  UNIQUE (taxonomy, slug)
);

CREATE TABLE IF NOT EXISTS fatwa_category_links (
  fatwa_id uuid NOT NULL REFERENCES fatwas(id) ON DELETE CASCADE,
  category_id uuid NOT NULL REFERENCES fatwa_categories(id) ON DELETE CASCADE,
  PRIMARY KEY (fatwa_id, category_id)
);

CREATE TABLE IF NOT EXISTS fatwa_chunks (
  id uuid PRIMARY KEY,
  fatwa_id uuid NOT NULL REFERENCES fatwas(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  content text NOT NULL,
  title text NOT NULL,
  category_path jsonb NOT NULL DEFAULT '[]',
  source_url text NOT NULL,
  source_collection text NOT NULL,
  source_author text,
  source_authority text,
  token_count integer,
  topic text,
  tags jsonb NOT NULL DEFAULT '[]',
  hierarchy jsonb NOT NULL DEFAULT '{}',
  section_type text NOT NULL DEFAULT 'issue',
  ruling text,
  evidence jsonb NOT NULL DEFAULT '[]',
  evidence_types jsonb NOT NULL DEFAULT '[]',
  wajh_al_dalala jsonb NOT NULL DEFAULT '[]',
  qa_pairs jsonb NOT NULL DEFAULT '[]',
  original_text text,
  retrieval_text text,
  UNIQUE (fatwa_id, chunk_index)
);

ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS topic text;
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS tags jsonb NOT NULL DEFAULT '[]';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS hierarchy jsonb NOT NULL DEFAULT '{}';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS section_type text NOT NULL DEFAULT 'issue';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS ruling text;
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '[]';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS evidence_types jsonb NOT NULL DEFAULT '[]';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS wajh_al_dalala jsonb NOT NULL DEFAULT '[]';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS qa_pairs jsonb NOT NULL DEFAULT '[]';
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS original_text text;
ALTER TABLE fatwa_chunks ADD COLUMN IF NOT EXISTS retrieval_text text;

CREATE TABLE IF NOT EXISTS embeddings (
  chunk_id uuid PRIMARY KEY REFERENCES fatwa_chunks(id) ON DELETE CASCADE,
  provider text NOT NULL,
  model text NOT NULL,
  dimensions integer NOT NULL,
  embedding vector(384) NOT NULL,
  embedded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY,
  locale text NOT NULL DEFAULT 'ar',
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','awaiting_clarification','completed')),
  original_question text,
  clarification_question text,
  relevant_context jsonb NOT NULL DEFAULT '{}',
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS original_question text;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS clarification_question text;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS relevant_context jsonb NOT NULL DEFAULT '{}';
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS completed_at timestamptz;

CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user','assistant','system')),
  content text NOT NULL,
  state text,
  citations jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_fatwas (
  id uuid PRIMARY KEY,
  user_key text NOT NULL,
  fatwa_id uuid NOT NULL REFERENCES fatwas(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_key, fatwa_id)
);

CREATE TABLE IF NOT EXISTS authority_contacts (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  phone text,
  website text,
  country text NOT NULL,
  is_verified boolean NOT NULL DEFAULT false,
  verified_at timestamptz,
  CHECK (NOT is_verified OR verified_at IS NOT NULL),
  CHECK (phone IS NOT NULL OR website IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id uuid PRIMARY KEY,
  stage text NOT NULL,
  status text NOT NULL,
  metrics jsonb NOT NULL DEFAULT '{}',
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);

CREATE TABLE IF NOT EXISTS ingestion_errors (
  id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
  url text,
  external_id bigint,
  stage text NOT NULL,
  error_type text NOT NULL,
  message text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fatwas_retrieval_fts_idx ON fatwas USING gin (to_tsvector('simple', retrieval_text));
CREATE INDEX IF NOT EXISTS fatwa_chunks_retrieval_fts_idx ON fatwa_chunks USING gin (to_tsvector('simple', retrieval_text));
CREATE INDEX IF NOT EXISTS fatwas_title_trgm_idx ON fatwas USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx ON embeddings USING hnsw (embedding vector_cosine_ops);
