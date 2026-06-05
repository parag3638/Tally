"""Assembly of the receipt-extraction graph.

Flow:

    image_encoder -> extractor -> categorizer -> confidence_router
                                                      |
                              (auto-accept) ----------+---------- (needs review)
                                   |                                    |
                                persist <--- accept --- human_review <--+
                                   |                    |     |
                                  END        retry_model|     |correct
                                              (-> extractor)   (-> corrector -> human_review)

Compiled with the Postgres checkpointer so ``interrupt()`` in human_review can
pause/resume across HTTP requests and process restarts.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agents.receipt_graph.nodes.categorizer import categorizer_node
from src.agents.receipt_graph.nodes.confidence_router import confidence_router_node
from src.agents.receipt_graph.nodes.corrector import corrector_node
from src.agents.receipt_graph.nodes.extractor import extractor_node
from src.agents.receipt_graph.nodes.human_review import human_review_node
from src.agents.receipt_graph.nodes.image_encoder import image_encoder_node
from src.agents.receipt_graph.nodes.persist import persist_node
from src.agents.receipt_graph.state import ReceiptState

_compiled = None


def _route_after_encode(state: ReceiptState) -> str:
    return END if state.get("status") == "failed" else "extractor"


def _route_after_confidence(state: ReceiptState) -> str:
    return "human_review" if state.get("needs_review_reason") else "persist"


def _route_after_review(state: ReceiptState) -> str:
    decision = state.get("review_decision")
    if decision == "correct":
        return "corrector"
    if decision == "retry_model":
        return "extractor"
    return "persist"


def build_graph() -> StateGraph:
    g = StateGraph(ReceiptState)

    g.add_node("image_encoder", image_encoder_node)
    g.add_node("extractor", extractor_node)
    g.add_node("categorizer", categorizer_node)
    g.add_node("confidence_router", confidence_router_node)
    g.add_node("human_review", human_review_node)
    g.add_node("corrector", corrector_node)
    g.add_node("persist", persist_node)

    g.add_edge(START, "image_encoder")
    g.add_conditional_edges("image_encoder", _route_after_encode, {"extractor": "extractor", END: END})
    g.add_edge("extractor", "categorizer")
    g.add_edge("categorizer", "confidence_router")
    g.add_conditional_edges(
        "confidence_router",
        _route_after_confidence,
        {"human_review": "human_review", "persist": "persist"},
    )
    g.add_conditional_edges(
        "human_review",
        _route_after_review,
        {"corrector": "corrector", "extractor": "extractor", "persist": "persist"},
    )
    g.add_edge("corrector", "human_review")
    g.add_edge("persist", END)
    return g


def get_receipt_graph(checkpointer=None):
    """Return a compiled receipt graph.

    Pass a checkpointer for the production (interrupt/resume) path. In tests an
    in-memory checkpointer can be supplied.
    """
    global _compiled
    if checkpointer is not None:
        return build_graph().compile(checkpointer=checkpointer)
    if _compiled is None:
        from src.db.checkpoint_pool import get_checkpointer

        _compiled = build_graph().compile(checkpointer=get_checkpointer())
    return _compiled
