"""FastAPI dependencies — current-user resolution from a JWT.

``get_current_user`` decodes the bearer token, loads the user, and returns a
lightweight ``CurrentUser``. Routers depend on it and pass ``current_user.user_id``
into the service layer, which enforces tenancy at the repository.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.core.exceptions import AuthError
from src.core.security import decode_access_token
from src.db.repositories.users_repo import UsersRepository
from src.db.session import get_cursor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class CurrentUser:
    user_id: int
    email: str


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthError("Could not validate credentials") from exc

    with get_cursor() as cur:
        user = UsersRepository(cur).get_by_id(user_id)

    if user is None or not user["is_active"]:
        raise AuthError("User not found or inactive")

    return CurrentUser(user_id=user["user_id"], email=user["email"])
