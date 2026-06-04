-- rollback 0002
DROP INDEX IF EXISTS idx_expenses_user_category;
DROP INDEX IF EXISTS idx_expenses_user_date;
ALTER TABLE expenses DROP COLUMN IF EXISTS updated_at;
ALTER TABLE expenses DROP COLUMN IF EXISTS created_at;
ALTER TABLE expenses DROP COLUMN IF EXISTS confidence;
ALTER TABLE expenses DROP COLUMN IF EXISTS status;
ALTER TABLE expenses DROP COLUMN IF EXISTS receipt_id;
ALTER TABLE expenses DROP COLUMN IF EXISTS user_id;
DROP TABLE IF EXISTS users;
