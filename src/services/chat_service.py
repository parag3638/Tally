"""Chat orchestration over the text-to-SQL agent.

Provides a one-shot answer and a token stream. Conversation state persists in the
Postgres checkpointer, so a follow-up question with the same ``conversation_id``
remembers the prior turns.
"""

from __future__ import annotations

from collections.abc import Iterator

from langchain_core.messages import HumanMessage

from src.agents.sql_agent.graph import build_sql_agent, thread_id_for
from src.db.checkpoint_pool import get_checkpointer


def _agent(user_id: int):
    return build_sql_agent(user_id, checkpointer=get_checkpointer())


def ask(user_id: int, message: str, conversation_id: str) -> str:
    agent = _agent(user_id)
    config = {"configurable": {"thread_id": thread_id_for(user_id, conversation_id)}}
    result = agent.invoke({"messages": [HumanMessage(content=message)]}, config)
    return result["messages"][-1].content


def stream(user_id: int, message: str, conversation_id: str) -> Iterator[str]:
    """Yield assistant tokens as they are produced (for SSE)."""
    agent = _agent(user_id)
    config = {"configurable": {"thread_id": thread_id_for(user_id, conversation_id)}}
    for chunk, _meta in agent.stream(
        {"messages": [HumanMessage(content=message)]}, config, stream_mode="messages"
    ):
        # Only stream assistant text tokens (skip tool messages).
        if getattr(chunk, "content", None) and chunk.type == "AIMessageChunk":
            yield chunk.content
