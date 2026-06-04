"""Expense CRUD endpoints — all tenant-scoped to the authenticated user."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from src.api.deps import CurrentUser, get_current_user
from src.core.exceptions import NotFoundError
from src.schemas.expenses import ExpenseCreate, ExpenseOut
from src.services import expense_service

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    current_user: CurrentUser = Depends(get_current_user),
    category_id: int | None = Query(None),
    payment_method_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return expense_service.list_expenses(
        current_user.user_id,
        category_id=category_id,
        payment_method_id=payment_method_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/{transaction_id}", response_model=ExpenseOut)
def get_expense(
    transaction_id: int, current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    expense = expense_service.get_expense(current_user.user_id, transaction_id)
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(
    body: ExpenseCreate, current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    return expense_service.create_expense(
        current_user.user_id,
        date=body.date,
        category_id=body.category_id,
        description=body.description,
        amount=body.amount,
        vat=body.vat,
        payment_method_id=body.payment_method_id,
        business_personal=body.business_personal,
    )


@router.delete("/{transaction_id}")
def delete_expense(
    transaction_id: int, current_user: CurrentUser = Depends(get_current_user)
) -> dict:
    expense_service.delete_expense(current_user.user_id, transaction_id)
    return {"message": "Expense deleted successfully"}
