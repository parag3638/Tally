"""Node: apply free-text user feedback to revise the extracted summary."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agents.models import structured_model
from src.agents.receipt_graph.state import CorrectedSummary, ReceiptState

_PROMPT = (
    "Here is the current summary of an invoice:\n"
    "Date: {date}\nCategory: {category}\nDescription: {description}\n"
    "Amount: {amount}\nVAT: {vat}\nBusiness or Personal: {business_personal}\n"
    "Payment Method: {payment_method}\n\n"
    "Revise it based on this user feedback:\n{feedback}\n\n"
    "If changing the category, pick one of: {categories}\n"
    "If changing the payment method, pick one of: {payment_methods}"
)


def corrector_node(state: ReceiptState) -> dict:
    categories = list((state.get("categories") or {}).values())
    payment_methods = list((state.get("payment_methods") or {}).values())

    prompt = _PROMPT.format(
        date=state.get("date"),
        category=state.get("category"),
        description=state.get("description"),
        amount=state.get("amount"),
        vat=state.get("vat"),
        business_personal=state.get("business_personal"),
        payment_method=state.get("payment_method"),
        feedback=state.get("correction_text") or "",
        categories=", ".join(categories),
        payment_methods=", ".join(payment_methods),
    )
    model = structured_model("categorizer", CorrectedSummary)
    result: CorrectedSummary = model.invoke([HumanMessage(content=prompt)])

    updates: dict = {
        "date": result.date,
        "category": result.category,
        "description": result.description,
        "amount": result.amount,
        "vat": result.vat,
        "business_personal": result.business_personal,
        "payment_method": result.payment_method,
    }

    # Re-resolve ids after the correction.
    for cid, name in (state.get("categories") or {}).items():
        if name == result.category:
            updates["category_id"] = cid
            break
    for pid, name in (state.get("payment_methods") or {}).items():
        if name == result.payment_method:
            updates["payment_method_id"] = pid
            break
    return updates
