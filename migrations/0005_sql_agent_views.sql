-- 0005 user-scoped views for the text-to-SQL agent
-- The agent is ONLY allowed to query these views. `my_expenses` is filtered by a
-- per-session GUC (app.current_user_id) set inside the read-only transaction, so
-- even an adversarial query can never read another tenant's rows.

CREATE OR REPLACE VIEW my_expenses AS
SELECT
    e.transaction_id,
    e.date,
    e.description,
    e.amount,
    e.vat,
    e.business_personal,
    e.status,
    e.confidence,
    c.category_name,
    p.payment_method_name
FROM expenses e
LEFT JOIN categories c ON e.category_id = c.category_id
LEFT JOIN payment_methods p ON e.payment_method_id = p.payment_method_id
WHERE e.user_id = current_setting('app.current_user_id')::int;
