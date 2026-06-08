"""The SQL guard is the agent's security boundary — these tests are adversarial."""

from __future__ import annotations

import pytest

from src.agents.sql_agent.sql_guard import MAX_LIMIT, sanitize
from src.core.exceptions import GuardrailError

# ---- queries that MUST be rejected ----

@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM my_expenses",
        "DROP TABLE expenses",
        "UPDATE my_expenses SET amount = 0",
        "INSERT INTO categories (category_name) VALUES ('x')",
        "SELECT * FROM my_expenses; DROP TABLE users;",  # stacked
        "SELECT * FROM users",  # not allow-listed
        "SELECT * FROM expenses",  # raw table, bypasses per-user view
        "TRUNCATE my_expenses",
        "SELECT pg_sleep(10)",  # function-only, no allowed table — still must not touch others
        "GRANT SELECT ON my_expenses TO public",
    ],
)
def test_rejects_dangerous_queries(query):
    with pytest.raises(GuardrailError):
        sanitize(query)


def test_rejects_access_to_raw_expenses_even_in_join():
    with pytest.raises(GuardrailError):
        sanitize("SELECT * FROM my_expenses JOIN expenses USING (transaction_id)")


# ---- queries that should pass (and get normalized) ----

def test_allows_simple_select_and_injects_limit():
    out = sanitize("SELECT category_name, SUM(amount) FROM my_expenses GROUP BY category_name")
    assert "LIMIT" in out.upper()
    assert str(MAX_LIMIT) in out


def test_allows_join_of_allowed_tables():
    out = sanitize(
        "SELECT c.category_name FROM my_expenses m "
        "JOIN categories c ON m.category_name = c.category_name LIMIT 5"
    )
    assert "category_name" in out


def test_caps_excessive_limit():
    out = sanitize("SELECT * FROM my_expenses LIMIT 999999")
    assert str(MAX_LIMIT) in out


def test_allows_cte():
    out = sanitize(
        "WITH t AS (SELECT amount FROM my_expenses) SELECT SUM(amount) FROM t"
    )
    assert out  # parsed and returned
