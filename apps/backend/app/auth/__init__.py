"""Authentication and authorization helpers for the IntelliPDF backend."""

from .dependencies import (
    get_current_user,
    require_authenticated_user,
    require_roles,
)
from .routes import router as auth_router

__all__ = [
    "auth_router",
    "get_current_user",
    "require_authenticated_user",
    "require_roles",
]
