"""API routes for authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .dependencies import require_authenticated_user
from .models import AuthenticatedUser, LoginRequest, RefreshRequest, TokenPair
from .service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair, response_model_by_alias=True)
async def login(credentials: LoginRequest) -> TokenPair:
    """Authenticate a user and return a token pair."""

    return auth_service.login(credentials)


@router.post("/refresh", response_model=TokenPair, response_model_by_alias=True)
async def refresh(payload: RefreshRequest) -> TokenPair:
    """Exchange a refresh token for a new set of credentials."""

    return auth_service.refresh(payload)


@router.get("/me", response_model=AuthenticatedUser)
async def me(current_user: AuthenticatedUser = Depends(require_authenticated_user)) -> AuthenticatedUser:
    """Return the currently authenticated user."""

    return current_user


__all__ = ["router"]
