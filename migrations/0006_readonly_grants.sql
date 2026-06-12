-- 0006 grant the text-to-SQL read-only role access to ONLY the safe relations.
-- No-op if the role doesn't exist (e.g. local dev using the app user as fallback).
-- The role is created by docker/initdb/01-readonly-role.sql before migrations run.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'expenses_readonly') THEN
        GRANT USAGE ON SCHEMA public TO expenses_readonly;
        GRANT SELECT ON my_expenses TO expenses_readonly;
        GRANT SELECT ON categories TO expenses_readonly;
        GRANT SELECT ON payment_methods TO expenses_readonly;
        -- Explicitly DO NOT grant access to raw expenses / users tables.
    END IF;
END
$$;
