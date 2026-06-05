"""State + structured-output schemas for the receipt extraction graph."""

from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class ReceiptData(BaseModel):
    """Vision-model extraction target. Field-level confidence drives the
    human-review gate."""

    date: str = Field(description="Receipt date, formatted YYYY-MM-DD")
    description: str = Field(description="Brief description / merchant of the purchase")
    amount: str = Field(description="Total amount paid, digits only e.g. '42.50'")
    vat: str = Field(description="Total VAT / tax paid, digits only; '0' if none")
    business_personal: str = Field(description="Either 'business' or 'personal'")
    payment_method: str = Field(description="One of the provided payment methods")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Your overall confidence (0-1) that the extracted fields are correct",
    )


class CategoryChoice(BaseModel):
    category: str = Field(description="The single best category from the provided list")


class CorrectedSummary(BaseModel):
    date: str
    category: str
    description: str
    amount: str
    vat: str
    business_personal: str
    payment_method: str


class ReceiptState(TypedDict, total=False):
    # ---- inputs ----
    user_id: int
    receipt_id: str | None
    image_path: str
    image_base64: str | None

    # reference data (id <-> name) loaded before the run
    categories: dict[int, str]
    payment_methods: dict[int, str]

    # model selection (mutated by the "retry with different model" path)
    vision_model_override: str | None
    categorizer_model_override: str | None
    model_attempts: int

    # ---- extracted fields ----
    date: str | None
    description: str | None
    amount: str | None
    vat: str | None
    business_personal: str | None
    payment_method: str | None
    category: str | None
    category_id: int | None
    payment_method_id: int | None

    # ---- confidence / routing ----
    confidence: float
    needs_review_reason: str | None
    possible_duplicates: list[dict[str, Any]]

    # ---- human review ----
    review_decision: str | None  # accept | correct | retry_model
    correction_text: str | None

    # ---- output ----
    status: str  # processing | needs_review | completed | failed
    created_expense: dict[str, Any] | None
    error: str | None
