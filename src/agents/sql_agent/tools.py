"""Tools exposed to the text-to-SQL agent.

Each tool is bound to a specific ``user_id`` via a closure so the model never
chooses (or even sees) which tenant it operates on — tenancy is fixed by the
caller, enforced again by the read-only view + GUC.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from src.core.logging import get_logger
from src.db.readonly import run_readonly

log = get_logger(__name__)

SCHEMA_DOC = """
You can query ONLY these read-only views/tables (Postgres dialect):

my_expenses(transaction_id, date, description, amount, vat, business_personal,
            status, confidence, category_name, payment_method_name)
    -- the current user's expenses, already filtered to them.
categories(category_id, category_name)
payment_methods(payment_method_id, payment_method_name)

Rules:
- Write a single read-only SELECT. Never INSERT/UPDATE/DELETE/DDL.
- Always read expenses from `my_expenses` (never a table called `expenses`).
- Use aggregates (SUM, COUNT, AVG) and GROUP BY for summaries.
- `amount` and `vat` are numeric. `date` is a DATE.
""".strip()


def build_tools(user_id: int) -> list:
    def get_schema() -> str:
        """Return the database schema the agent is allowed to query."""
        return SCHEMA_DOC

    def run_sql(query: str) -> str:
        """Execute a single read-only SELECT against the allowed views and return rows."""
        try:
            rows = run_readonly(query, user_id)
        except Exception as exc:  # noqa: BLE001 — surface guard/db errors to the model
            log.info("sql_agent.query_rejected", error=str(exc))
            return f"ERROR: {exc}. Revise the query and try again."
        if not rows:
            return "No rows."
        # Compact, model-friendly rendering.
        return "\n".join(str(dict(r)) for r in rows[:100])

    def semantic_search(text: str) -> str:
        """Find expenses semantically similar to a free-text description."""
        from src.services import embedding_service

        try:
            hits = embedding_service.search(user_id, text, limit=10)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: semantic search unavailable ({exc})"
        return "\n".join(
            f"#{h['transaction_id']} {h.get('description')} amount={h.get('amount')}"
            for h in hits
        ) or "No matches."

    return [
        StructuredTool.from_function(get_schema),
        StructuredTool.from_function(run_sql),
        StructuredTool.from_function(semantic_search),
    ]
