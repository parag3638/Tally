"""SQL safety guard for the text-to-SQL agent.

Defense in depth — an LLM-generated query must pass ALL of these before it ever
touches the database:

  1. Parses as exactly ONE statement (no stacked ``;`` queries).
  2. Is a read-only ``SELECT`` / ``WITH ... SELECT`` (no DML/DDL keywords).
  3. References ONLY allow-listed user-scoped views/tables — never raw
     ``expenses`` or ``users``, so it can't bypass the per-user filter.
  4. Has a ``LIMIT`` (injected if absent) to bound result size.

At execution time the query also runs in a READ ONLY transaction with a
``statement_timeout`` and a per-session ``app.current_user_id`` GUC that scopes
``my_expenses`` to the caller (see migration 0005). Belt and suspenders.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from src.core.exceptions import GuardrailError

# The ONLY relations the agent may read.
ALLOWED_TABLES = {"my_expenses", "categories", "payment_methods"}
MAX_LIMIT = 1000

# Functions that can exfiltrate data, touch the filesystem, or stall the server.
FORBIDDEN_FUNCTIONS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "lo_import",
    "lo_export", "dblink", "copy", "pg_stat_file", "set_config", "current_setting",
}

# Statement types that are never allowed.
_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Grant, exp.Merge,
)


def sanitize(query: str) -> str:
    """Validate + normalize an LLM query. Returns safe SQL or raises GuardrailError."""
    query = (query or "").strip().rstrip(";").strip()
    if not query:
        raise GuardrailError("Empty query")

    try:
        statements = sqlglot.parse(query, read="postgres")
    except Exception as exc:  # noqa: BLE001
        raise GuardrailError(f"Could not parse SQL: {exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise GuardrailError("Only a single statement is allowed")

    stmt = statements[0]

    # Must be a SELECT (optionally wrapped in a WITH).
    if not isinstance(stmt, (exp.Select, exp.Subquery, exp.With)):
        raise GuardrailError("Only SELECT queries are allowed")

    # No write/DDL nodes anywhere in the tree.
    for node_type in _FORBIDDEN:
        if list(stmt.find_all(node_type)):
            raise GuardrailError("Only read-only SELECT queries are allowed")

    # Names introduced by CTEs are legitimate references, not real tables.
    cte_names = {cte.alias_or_name.lower() for cte in stmt.find_all(exp.CTE)}
    allowed = ALLOWED_TABLES | cte_names

    referenced = {t.name.lower() for t in stmt.find_all(exp.Table)}
    for name in referenced:
        if name not in allowed:
            raise GuardrailError(
                f"Table '{name}' is not allowed. "
                f"Query only: {', '.join(sorted(ALLOWED_TABLES))}"
            )

    # Must read at least one real allow-listed relation (blocks e.g. SELECT pg_sleep(10)).
    if not (referenced - cte_names) & ALLOWED_TABLES:
        raise GuardrailError("Query must read from an allowed table")

    # Block dangerous function calls by name.
    for func in stmt.find_all(exp.Anonymous, exp.Func):
        fname = (func.name or "").lower()
        if fname in FORBIDDEN_FUNCTIONS:
            raise GuardrailError(f"Function '{fname}' is not allowed")

    # Enforce a LIMIT on the outermost SELECT.
    select = stmt if isinstance(stmt, exp.Select) else stmt.find(exp.Select)
    if select is not None:
        limit = select.args.get("limit")
        if limit is None:
            select.limit(MAX_LIMIT, copy=False)
        else:
            try:
                if int(limit.expression.name) > MAX_LIMIT:
                    select.limit(MAX_LIMIT, copy=False)
            except (AttributeError, ValueError):
                select.limit(MAX_LIMIT, copy=False)

    return stmt.sql(dialect="postgres")
