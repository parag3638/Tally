"""Model registry + multi-model fallback.

A single place that maps a *role* (vision, categorizer, chat, insights) to a
primary model and an ordered list of fallbacks across providers. Nodes call
``structured_model(role, Schema)`` and get a runnable that:

  * forces structured (function-call) output validated against ``Schema``, and
  * transparently fails over to the next provider on error (``.with_fallbacks``).

This replaces the old ad-hoc ``if "claude" in name`` branching scattered through
the node files, and makes the whole agent layer trivially mockable in tests
(monkeypatch ``structured_model``).
"""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from src.core.config import settings

# role -> (primary, [fallbacks...])
_ROLE_MODELS: dict[str, tuple[str, list[str]]] = {
    "vision": (settings.vision_model, [m for m in [settings.vision_fallback_model] if m]),
    "categorizer": (
        settings.categorizer_model,
        [m for m in [settings.categorizer_fallback_model] if m],
    ),
    "chat": (settings.chat_model, []),
    "insights": (settings.insights_model, []),
}


def make_chat_model(name: str, **kwargs: Any) -> BaseChatModel:
    """Construct a chat model from a name, picking the provider by prefix."""
    kwargs.setdefault("temperature", 0)
    if "claude" in name.lower():
        return ChatAnthropic(model=name, **kwargs)
    return ChatOpenAI(model=name, **kwargs)


def model_names_for_role(role: str) -> list[str]:
    primary, fallbacks = _ROLE_MODELS.get(role, (settings.chat_model, []))
    return [primary, *fallbacks]


def structured_model(role: str, schema: type, *, model_override: str | None = None) -> Runnable:
    """Return a structured-output runnable for ``role`` with provider fallbacks.

    ``model_override`` forces a specific primary model (used by the human review
    "retry with a different model" path).
    """
    names = model_names_for_role(role)
    if model_override:
        # Put the override first, keep the rest as fallbacks (deduped).
        names = [model_override, *[n for n in names if n != model_override]]

    runnables = [make_chat_model(n).with_structured_output(schema) for n in names]
    primary, *fallbacks = runnables
    return primary.with_fallbacks(fallbacks) if fallbacks else primary


def plain_model(role: str) -> BaseChatModel:
    """Non-structured chat model for the role's primary (used by chat streaming)."""
    return make_chat_model(model_names_for_role(role)[0])
