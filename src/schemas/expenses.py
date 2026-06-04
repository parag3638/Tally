from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)


class CategoryOut(BaseModel):
    category_id: int
    category_name: str


class PaymentMethodCreate(BaseModel):
    payment_method_name: str = Field(min_length=1, max_length=50)


class PaymentMethodOut(BaseModel):
    payment_method_id: int
    payment_method_name: str


class ExpenseCreate(BaseModel):
    date: date_type
    category_id: int
    description: str
    amount: Decimal
    vat: Decimal = Decimal("0")
    payment_method_id: int
    business_personal: str = "personal"


class ExpenseOut(BaseModel):
    transaction_id: int
    date: date_type | None = None
    category_id: int | None = None
    description: str | None = None
    amount: Decimal | None = None
    vat: Decimal | None = None
    payment_method_id: int | None = None
    business_personal: str | None = None
    status: str | None = None
    confidence: float | None = None
    created_at: datetime | None = None
