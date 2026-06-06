-- rollback 0003
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS fk_expenses_receipt;
DROP INDEX IF EXISTS idx_jobs_user;
DROP TABLE IF EXISTS jobs;
DROP INDEX IF EXISTS idx_receipts_user;
DROP TABLE IF EXISTS receipts;
