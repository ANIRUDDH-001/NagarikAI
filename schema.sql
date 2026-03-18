-- Enable the pgvector extension to work with HuggingFace embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- 1. SCHEMES TABLE
-- ==========================================
CREATE TABLE schemes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_name TEXT NOT NULL,
    ministry TEXT,
    state TEXT DEFAULT 'national',
    category TEXT[] DEFAULT '{}', -- SC/ST/OBC/General/EWS/All
    gender TEXT DEFAULT 'all',
    age_min INTEGER,
    age_max INTEGER,
    income_limit INTEGER, -- annual in rupees, null means no limit
    occupation TEXT[] DEFAULT '{}', -- farmer/student/laborer/etc
    marital_status TEXT DEFAULT 'any',
    bpl_required BOOLEAN DEFAULT false,
    disability_required BOOLEAN DEFAULT false,
    documents_needed TEXT[] DEFAULT '{}',
    application_url TEXT,
    official_source_url TEXT,
    tier INTEGER CHECK (tier IN (1, 2, 3, 4)),
    data_quality_score FLOAT, -- Set by Groq analysis pipeline
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- 2. SCHEME CHUNKS TABLE
-- ==========================================
CREATE TABLE scheme_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id UUID REFERENCES schemes(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384), -- 384 dimensions for all-MiniLM-L6-v2
    chunk_type TEXT, -- 'description'/'eligibility'/'benefits'/'process'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- 3. USER PROFILES TABLE
-- ==========================================
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    name TEXT,
    age INTEGER,
    gender TEXT,
    state TEXT,
    district TEXT,
    category TEXT,
    annual_income INTEGER,
    occupation TEXT,
    marital_status TEXT,
    is_bpl BOOLEAN DEFAULT false,
    has_disability BOOLEAN DEFAULT false,
    owns_land BOOLEAN DEFAULT false,
    house_type TEXT,
    education_level TEXT,
    has_bank_account BOOLEAN DEFAULT false,
    language_pref TEXT DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- 4. QUERY LOGS TABLE
-- ==========================================
CREATE TABLE query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT REFERENCES user_profiles(session_id) ON DELETE SET NULL,
    state TEXT,
    query_text TEXT,
    schemes_shown TEXT[] DEFAULT '{}',
    response_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- INDEXES
-- ==========================================
/*
  EXPLANATION OF INDEXES:
  1. idx_schemes_state: Most users search within their own state + national schemes. 
     B-Tree index allows extremely fast filtering by state.
  2. idx_schemes_category: GIN index for text array filtering, so we can quickly match users 
     who are 'SC', 'ST', etc. against the scheme's allowed categories.
  3. idx_schemes_income_limit: B-Tree index on income limit because queries will frequently 
     check `income_limit >= user_income OR income_limit IS NULL`.
  4. idx_schemes_tier: Allows quick sorting of flagship/high-tier schemes so they always appear 
     top if matched.
  5. idx_chunks_scheme_id: Standard foreign key index to ensure fast JOINs when fetching 
     the parent scheme for a matching chunk.
  6. idx_chunks_embedding: HNSW index on the vector column enables fast approximate nearest 
     neighbor (ANN) search. Without this, vector searches do a slow exact sequential scan.
*/

CREATE INDEX idx_schemes_state ON schemes USING btree(state);
CREATE INDEX idx_schemes_category ON schemes USING gin(category);
CREATE INDEX idx_schemes_income_limit ON schemes USING btree(income_limit);
CREATE INDEX idx_schemes_tier ON schemes USING btree(tier);
CREATE INDEX idx_chunks_scheme_id ON scheme_chunks USING btree(scheme_id);

-- HNSW Vector Index (using cosine distance <=> for huggingface embeddings)
CREATE INDEX idx_chunks_embedding ON scheme_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ==========================================
-- MATCH SCHEMES FUNCTION
-- ==========================================
/*
  This function performs hybrid search: it filters schemes by exact metadata 
  (state, age, income) and then orders the resulting valid chunks by vector similarity.
*/
CREATE OR REPLACE FUNCTION match_schemes(
  query_embedding VECTOR(384),
  match_threshold FLOAT,
  match_count INT,
  p_state TEXT,
  p_age INT,
  p_income INT
)
RETURNS TABLE (
  scheme_id UUID,
  scheme_name TEXT,
  chunk_text TEXT,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id AS scheme_id,
    s.scheme_name,
    c.chunk_text,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM scheme_chunks c
  JOIN schemes s ON c.scheme_id = s.id
  WHERE 
    1 - (c.embedding <=> query_embedding) > match_threshold
    -- Metadata Filtering logic
    AND (s.state = 'national' OR s.state = p_state OR p_state IS NULL)
    AND (s.age_min IS NULL OR s.age_min <= p_age OR p_age IS NULL)
    AND (s.age_max IS NULL OR s.age_max >= p_age OR p_age IS NULL)
    AND (s.income_limit IS NULL OR s.income_limit >= p_income OR p_income IS NULL)
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ==========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================

ALTER TABLE schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheme_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;

-- 1. Schemes & Chunks are PUBLICLY READABLE by anyone
CREATE POLICY "Public read access to schemes" 
  ON schemes FOR SELECT USING (true);
  
CREATE POLICY "Public read access to scheme chunks" 
  ON scheme_chunks FOR SELECT USING (true);

-- Backend Service Role ONLY for inserts/updates on schemes
-- The Supabase python client will bypass RLS entirely when using the SERVICE_ROLE_KEY, but restricting mutations is a good practice.
CREATE POLICY "Service role full access on schemes" 
  ON schemes USING (auth.role() = 'service_role');
  
CREATE POLICY "Service role full access on chunks" 
  ON scheme_chunks USING (auth.role() = 'service_role');

-- 2. User Profiles & Query Logs: 
-- Anyone can insert session data on a new session.
CREATE POLICY "Anyone can insert user profile" 
  ON user_profiles FOR INSERT WITH CHECK (true);

-- Users can only UPDATE their session if they pass the header, or via backend service_role
CREATE POLICY "Users can update their own session profile" 
  ON user_profiles FOR UPDATE USING (current_setting('request.headers', true)::json->>'x-session-id' = session_id);

CREATE POLICY "Anyone can log queries" 
  ON query_logs FOR INSERT WITH CHECK (true);
