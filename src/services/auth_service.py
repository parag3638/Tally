"""Authentication business logic: registration, login, token issuance.

Opens its own transaction via ``get_cursor``; routes call these methods and never
touch the DB directly.
"""

from __future__ import annotations

from src.core.exceptions import AuthError
from src.core.security import create_access_token, hash_password, verify_password
from src.db.repositories.users_repo import UsersRepository
from src.db.session import get_cursor


def register(email: str, password: str) -> dict:
    with get_cursor() as cur:
        repo = UsersRepository(cur)
        return repo.create(email=email, password_hash=hash_password(password))


def login(email: str, password: str) -> dict:
    with get_cursor() as cur:
        user = UsersRepository(cur).get_by_email(email)

    if not user or not verify_password(password, user["password_hash"]):
        raise AuthError("Invalid email or password")
    if not user["is_active"]:
        raise AuthError("Account is disabled")

    token = create_access_token(user["user_id"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "email": user["email"],
    }
