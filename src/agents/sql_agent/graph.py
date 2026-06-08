"""The conversational text-to-SQL agent.

A ReAct-style tool-calling agent (LangGraph prebuilt) that answers natural-language
questions about the user's expenses by calling the guarded SQL + semantic-search
tools. Conversation memory is provided by the shared Postgres checkpointer keyed
by ``thread_id`` = ``{user_id}:{conversation_id}``.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from src.agents.models import plain_model
from src.agents.sql_agent.tools import build_tools

SYSTEM_PROMPT = (
    "You are a helpful financial assistant for a personal expense tracker. "
    "Answer questions about the user's spending by querying their data with the "
    "tools. Prefer SQL aggregates for totals and breakdowns; use semantic_search "
    "when the user describes a purchase in fuzzy terms. Always ground every number "
    "in a tool result — never invent figures. Be concise and report amounts with "
    "their currency context when known."
)


def build_sql_agent(user_id: int, checkpointer=None):
    model = plain_model("chat")
    tools = build_tools(user_id)
    return create_react_agent(
        model,
        tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def thread_id_for(user_id: int, conversation_id: str) -> str:
    return f"{user_id}:{conversation_id}"
