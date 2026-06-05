"""Node: vision-model extraction of structured fields from the receipt image.

Uses the multi-model fallback runnable (OpenAI primary, Anthropic fallback). The
"retry with a different model" review path sets ``vision_model_override`` so a
fresh attempt uses the other provider.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agents.models import structured_model
from src.agents.receipt_graph.state import ReceiptData, ReceiptState
from src.core.logging import get_logger

log = get_logger(__name__)

_PROMPT = (
    "Extract the details of this receipt. ALWAYS reply by calling the ReceiptData "
    "function — never ask for more information; if unsure, make a well-reasoned guess "
    "but always return all fields. Set 'confidence' to your honest overall confidence "
    "(0-1) that the extracted values are correct.\n"
    "Choose the 'payment_method' from exactly one of: {payment_methods}"
)


def extractor_node(state: ReceiptState) -> dict:
    payment_methods = list((state.get("payment_methods") or {}).values())
    prompt = _PROMPT.format(payment_methods=", ".join(payment_methods))
    image_b64 = state.get("image_base64") or ""

    model = structured_model(
        "vision", ReceiptData, model_override=state.get("vision_model_override")
    )
    message = HumanMessage(
        content=[
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": prompt},
        ]
    )
    result: ReceiptData = model.invoke([message])
    log.info("receipt.extracted", confidence=result.confidence)

    return {
        "date": result.date,
        "description": result.description,
        "amount": result.amount,
        "vat": result.vat,
        "business_personal": result.business_personal,
        "payment_method": result.payment_method,
        "confidence": float(result.confidence),
        "model_attempts": (state.get("model_attempts") or 0) + 1,
    }
