-- 0004 pgvector embeddings for semantic search + duplicate detection
-- Requires the pgvector extension (bundled in the pgvector/pgvector Docker image).

CREATE EXTENSION IF NOT EXISTS vector;

-- text-embedding-3-small => 1536 dimensions.
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS receipt_text TEXT;

-- HNSW index for fast approximate cosine nearest-neighbour search.
CREATE INDEX IF NOT EXISTS idx_expenses_embedding_hnsw
    ON expenses USING hnsw (embedding vector_cosine_ops);
