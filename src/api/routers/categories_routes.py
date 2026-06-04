"""Category endpoints (global reference data; auth required)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.deps import CurrentUser, get_current_user
from src.schemas.expenses import CategoryCreate, CategoryOut
from src.services import expense_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(_: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return expense_service.list_categories()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate, _: CurrentUser = Depends(get_current_user)
) -> dict:
    return expense_service.create_category(body.category_name)


@router.delete("/{category_id}")
def delete_category(
    category_id: int, _: CurrentUser = Depends(get_current_user)
) -> dict:
    expense_service.delete_category(category_id)
    return {"message": "Category deleted successfully"}
