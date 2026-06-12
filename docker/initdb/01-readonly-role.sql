-- Runs once on first DB init (Postgres docker-entrypoint-initdb.d).
-- Creates the dedicated read-only role used by the text-to-SQL agent. The actual
-- SELECT grants are applied by migration 0006 after the tables/views exist.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'expenses_readonly') THEN
        CREATE ROLE expenses_readonly LOGIN PASSWORD 'readonly';
    END IF;
END
$$;
