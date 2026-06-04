"""Expense + reference-data business logic.

Each method runs inside one transaction (``get_cursor``) and is scoped to a
``user_id``. This is the layer the API routers, the receipt graph's ``persist``
node, and the MCP server all call — so tenancy and side effects live in one place.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.db.repositories.categories_repo import CategoriesRepository
from src.db.repositories.expenses_repo import ExpensesRepository
from src.db.repositories.payment_methods_repo import PaymentMethodsRepository
from src.db.session import get_cursor

# ---- Categories (global reference table) ----


def list_categories() -> list[dict]:
    with get_cursor() as cur:
        return CategoriesRepository(cur).list()


def create_category(name: str) -> dict:
    with get_cursor() as cur:
        return CategoriesRepository(cur).create(name)


def delete_category(category_id: int) -> None:
    with get_cursor() as cur:
        CategoriesRepository(cur).delete(category_id)


# ---- Payment methods (global reference table) ----


def list_payment_methods() -> list[dict]:
    with get_cursor() as cur:
        return PaymentMethodsRepository(cur).list()


def create_payment_method(name: str) -> dict:
    with get_cursor() as cur:
        return PaymentMethodsRepository(cur).create(name)


def delete_payment_method(payment_method_id: int) -> None:
    with get_cursor() as cur:
        PaymentMethodsRepository(cur).delete(payment_method_id)


# ---- Expenses (tenant-scoped) ----


def list_expenses(
    user_id: int,
    *,
    category_id: int | None = None,
    payment_method_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with get_cursor() as cur:
        return ExpensesRepository(cur, user_id).list(
            category_id=category_id,
            payment_method_id=payment_method_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )


def get_expense(user_id: int, transaction_id: int) -> dict | None:
    with get_cursor() as cur:
        return ExpensesRepository(cur, user_id).get(transaction_id)


def create_expense(
    user_id: int,
    *,
    date: date | None,
    category_id: int | None,
    description: str | None,
    amount: Decimal | None,
    vat: Decimal | None,
    payment_method_id: int | None,
    business_personal: str | None,
    receipt_id: str | None = None,
    status: str = "confirmed",
    confidence: float | None = None,
) -> dict:
    with get_cursor() as cur:
        return ExpensesRepository(cur, user_id).create(
            date=date,
            category_id=category_id,
            description=description,
            amount=amount,
            vat=vat,
            payment_method_id=payment_method_id,
            business_personal=business_personal,
            receipt_id=receipt_id,
            status=status,
            confidence=confidence,
        )


def delete_expense(user_id: int, transaction_id: int) -> None:
    with get_cursor() as cur:
        ExpensesRepository(cur, user_id).delete(transaction_id)
