-- rollback 0004
DROP INDEX IF EXISTS idx_expenses_embedding_hnsw;
ALTER TABLE expenses DROP COLUMN IF EXISTS receipt_text;
ALTER TABLE expenses DROP COLUMN IF EXISTS embedding;
