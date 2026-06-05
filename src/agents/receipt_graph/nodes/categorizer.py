"""Node: choose a category for the extracted receipt and resolve name -> id."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agents.models import structured_model
from src.agents.receipt_graph.state import CategoryChoice, ReceiptState

_PROMPT = (
    "Here is an extracted invoice:\n"
    "Date: {date}\nDescription: {description}\nAmount: {amount}\nVAT: {vat}\n"
    "Business or Personal: {business_personal}\nPayment Method: {payment_method}\n\n"
    "Select the single most appropriate category from this list:\n{categories}"
)


def _resolve_ids(state: ReceiptState, category: str | None) -> dict:
    out: dict = {"category": category}
    categories = state.get("categories") or {}
    payment_methods = state.get("payment_methods") or {}

    for cid, name in categories.items():
        if name == category:
            out["category_id"] = cid
            break
    pm_name = state.get("payment_method")
    for pid, name in payment_methods.items():
        if name == pm_name:
            out["payment_method_id"] = pid
            break
    return out


def categorizer_node(state: ReceiptState) -> dict:
    categories = list((state.get("categories") or {}).values())
    prompt = _PROMPT.format(
        date=state.get("date"),
        description=state.get("description"),
        amount=state.get("amount"),
        vat=state.get("vat"),
        business_personal=state.get("business_personal"),
        payment_method=state.get("payment_method"),
        categories=", ".join(categories),
    )
    model = structured_model(
        "categorizer", CategoryChoice, model_override=state.get("categorizer_model_override")
    )
    result: CategoryChoice = model.invoke([HumanMessage(content=prompt)])
    return _resolve_ids(state, result.category)
