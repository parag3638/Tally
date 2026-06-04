"""Auth endpoints: register + OAuth2 password login."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import CurrentUser, get_current_user
from src.schemas.auth import RegisterRequest, TokenResponse, UserOut
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest) -> UserOut:
    user = auth_service.register(body.email, body.password)
    return UserOut(user_id=user["user_id"], email=user["email"])


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    # OAuth2 password flow uses 'username' for the email field.
    result = auth_service.login(form.username, form.password)
    return TokenResponse(**result)


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(user_id=current_user.user_id, email=current_user.email)
