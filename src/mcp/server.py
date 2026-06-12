"""MCP server exposing the expense tracker to MCP clients (e.g. Claude Desktop).

Tools are thin wrappers over the in-process **service layer** — no HTTP hop. The
server acts as a single configured user (``MCP_USER_ID``) since desktop MCP
clients don't carry a JWT; document this clearly when sharing the config.

Run:  python -m src.mcp.server      (stdio transport)
Add to claude_desktop_config.json — see the README.
"""

from __future__ import annotations

from decimal import Decimal

from mcp.server.fastmcp import FastMCP

from src.core.config import settings
from src.core.logging import configure_logging

mcp = FastMCP("tally")

_UID = settings.mcp_user_id


@mcp.tool()
def list_expenses(limit: int = 20) -> list[dict]:
    """List the most recent expenses for the configured user."""
    from src.services import expense_service

    rows = expense_service.list_expenses(_UID, limit=limit)
    return [dict(r) for r in rows]


@mcp.tool()
def add_expense(
    description: str,
    amount: float,
    category_id: int,
    payment_method_id: int,
    date: str | None = None,
    vat: float = 0.0,
    business_personal: str = "personal",
) -> dict:
    """Create a new expense for the configured user."""
    from datetime import date as date_type

    from src.services import expense_service

    parsed = date_type.fromisoformat(date) if date else None
    row = expense_service.create_expense(
        _UID,
        date=parsed,
        category_id=category_id,
        description=description,
        amount=Decimal(str(amount)),
        vat=Decimal(str(vat)),
        payment_method_id=payment_method_id,
        business_personal=business_personal,
    )
    return dict(row)


@mcp.tool()
def search_expenses_semantic(query: str, limit: int = 10) -> list[dict]:
    """Find expenses semantically similar to a free-text description."""
    from src.services import embedding_service

    return [dict(r) for r in embedding_service.search(_UID, query, limit=limit)]


@mcp.tool()
def get_spend_summary() -> dict:
    """Return monthly totals and a category breakdown for the configured user."""
    from src.services import insights_service

    return insights_service.monthly_summary(_UID)


@mcp.tool()
def detect_anomalies() -> dict:
    """Detect spending anomalies (category spikes, duplicate charges)."""
    from src.services import insights_service

    return insights_service.detect_anomalies(_UID)


@mcp.tool()
def query_expenses_nl(question: str) -> str:
    """Answer a natural-language question about spending via the text-to-SQL agent."""
    from src.services import chat_service

    return chat_service.ask(_UID, question, conversation_id="mcp")


def main() -> None:
    configure_logging()
    from src.db.pool import init_pool

    init_pool()
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
