"""Payment-method endpoints (global reference data; auth required)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.deps import CurrentUser, get_current_user
from src.schemas.expenses import PaymentMethodCreate, PaymentMethodOut
from src.services import expense_service

router = APIRouter(prefix="/payment_methods", tags=["payment_methods"])


@router.get("", response_model=list[PaymentMethodOut])
def list_payment_methods(_: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return expense_service.list_payment_methods()


@router.post("", response_model=PaymentMethodOut, status_code=201)
def create_payment_method(
    body: PaymentMethodCreate, _: CurrentUser = Depends(get_current_user)
) -> dict:
    return expense_service.create_payment_method(body.payment_method_name)


@router.delete("/{payment_method_id}")
def delete_payment_method(
    payment_method_id: int, _: CurrentUser = Depends(get_current_user)
) -> dict:
    expense_service.delete_payment_method(payment_method_id)
    return {"message": "Payment method deleted successfully"}
