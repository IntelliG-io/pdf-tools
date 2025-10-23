"""FastAPI dependencies for authentication and authorisation."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .models import AuthenticatedUser
from .service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    """Resolve the current user from a bearer token."""

    return auth_service.validate_access_token(token)


def require_authenticated_user(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    """Guard that ensures a valid user is present."""

    return user


def require_roles(*roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Create a dependency that enforces the user has one of ``roles``."""

    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user

    return dependency


__all__ = [
    "get_current_user",
    "oauth2_scheme",
    "require_authenticated_user",
    "require_roles",
]
