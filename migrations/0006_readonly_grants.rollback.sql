-- rollback 0006
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'expenses_readonly') THEN
        REVOKE SELECT ON my_expenses FROM expenses_readonly;
        REVOKE SELECT ON categories FROM expenses_readonly;
        REVOKE SELECT ON payment_methods FROM expenses_readonly;
    END IF;
END
$$;
