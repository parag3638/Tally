-- 0003 receipts + async jobs
-- Durable tracking for uploaded receipt files and background processing jobs.

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id  UUID PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    file_path   TEXT NOT NULL,
    mime_type   VARCHAR(100),
    sha256      VARCHAR(64),
    status      VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_receipts_user ON receipts (user_id, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS jobs (
    job_id     UUID PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id),
    receipt_id UUID REFERENCES receipts(receipt_id),
    type       VARCHAR(50) NOT NULL,
    status     VARCHAR(32) NOT NULL DEFAULT 'pending',
    result     JSONB,
    error      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs (user_id, created_at DESC);

-- Now that receipts exists, tie expenses.receipt_id to it.
ALTER TABLE expenses
    ADD CONSTRAINT fk_expenses_receipt
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id);
