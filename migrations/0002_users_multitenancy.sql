-- 0002 users + multitenancy
-- Adds the users table and ties expenses to an owner. Also adds the
-- lifecycle columns (status / confidence / timestamps) used by the agentic
-- pipeline. receipt_id is added as a plain UUID here; its FK to the receipts
-- table is created in 0003.

CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS users (
    user_id       SERIAL PRIMARY KEY,
    email         CITEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS user_id    INTEGER REFERENCES users(user_id);
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS receipt_id UUID;
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS status     VARCHAR(32) NOT NULL DEFAULT 'confirmed';
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS confidence NUMERIC(4, 3);
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_user_category ON expenses (user_id, category_id);
