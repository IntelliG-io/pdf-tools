"""Core authentication and authorisation logic."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

import bcrypt
import jwt
from fastapi import HTTPException, status

from .models import (
    AuthenticatedUser,
    LoginRequest,
    RefreshRequest,
    RefreshTokenRecord,
    TokenPair,
    TokenPayload,
    User,
    UserPublic,
)
from .store import UserStore

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_IN_SECONDS = 15 * 60
REFRESH_TOKEN_EXPIRES_IN_SECONDS = 7 * 24 * 60 * 60
def _load_secret_key() -> str:
    """Load the JWT signing key from the environment."""

    secret = os.getenv("INTELLIPDF_AUTH_SECRET")
    if not secret:
        raise RuntimeError(
            "INTELLIPDF_AUTH_SECRET must be set to a non-empty value before starting the service."
        )

    if secret == "intellipdf-development-secret":
        raise RuntimeError(
            "INTELLIPDF_AUTH_SECRET is using an insecure default value; please provide a unique secret."
        )

    return secret


SECRET_KEY = _load_secret_key()


class AuthService:
    """Service responsible for issuing and validating authentication tokens."""

    def __init__(self, user_store: UserStore):
        self._user_store = user_store

    def login(self, credentials: LoginRequest) -> TokenPair:
        """Validate ``credentials`` and return a new access/refresh token pair."""

        user = self._user_store.get_by_username(credentials.username)
        if not user or not self._verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        return self._issue_tokens(user)

    def refresh(self, payload: RefreshRequest) -> TokenPair:
        """Exchange a refresh token for a new token pair."""

        record = self._user_store.pop_refresh_token(payload.refresh_token)
        if not record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

        if record.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")

        user = self._user_store.get_by_id(record.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

        return self._issue_tokens(user)

    def validate_access_token(self, token: str) -> AuthenticatedUser:
        """Decode and validate a JWT access token, returning the associated user."""

        try:
            payload_dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            payload = TokenPayload(**payload_dict)
        except jwt.PyJWTError as exc:  # pragma: no cover - library raised errors
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

        if payload.type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.")

        user = self._user_store.get_by_id(int(payload.sub))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

        return AuthenticatedUser(**user.model_dump())

    def _issue_tokens(self, user: User) -> TokenPair:
        """Create and persist a new token pair for ``user``."""

        access_token, access_expiry = self._create_access_token(user)
        refresh_token, refresh_expiry = self._create_refresh_token(user)

        self._user_store.clear_refresh_tokens(user.id)
        self._user_store.add_refresh_token(
            RefreshTokenRecord(
                token=refresh_token,
                user_id=user.id,
                expires_at=refresh_expiry,
            )
        )

        return TokenPair(
            accessToken=access_token,
            refreshToken=refresh_token,
            accessTokenExpiresIn=ACCESS_TOKEN_EXPIRES_IN_SECONDS,
            refreshTokenExpiresIn=REFRESH_TOKEN_EXPIRES_IN_SECONDS,
            user=UserPublic(**user.model_dump(exclude={"password_hash"})),
        )

    def _create_access_token(self, user: User) -> Tuple[str, datetime]:
        issued_at = datetime.now(timezone.utc)
        expiry = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRES_IN_SECONDS)
        payload = {
            "sub": str(user.id),
            "role": user.role,
            "type": "access",
            "exp": expiry,
            "iat": issued_at,
            "jti": secrets.token_hex(8),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token, expiry

    def _create_refresh_token(self, user: User) -> Tuple[str, datetime]:
        issued_at = datetime.now(timezone.utc)
        expiry = issued_at + timedelta(seconds=REFRESH_TOKEN_EXPIRES_IN_SECONDS)
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": expiry,
            "iat": issued_at,
            "jti": secrets.token_hex(8),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token, expiry

    @staticmethod
    def _verify_password(plain_password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode(), password_hash.encode())
        except ValueError:  # pragma: no cover - bcrypt raised due to invalid hash
            return False


def build_default_auth_service() -> AuthService:
    """Create an :class:`AuthService` with a small in-memory user store."""

    users = [
        User(
            id=1,
            username="admin",
            full_name="IntelliPDF Admin",
            role="admin",
            password_hash="$2b$12$qQOOv4CVqHkVjCW8dCsGder1bkOYvURjRXNstqHYH1wq4JLc3PxsK",
        ),
        User(
            id=2,
            username="analyst",
            full_name="Operations Analyst",
            role="analyst",
            password_hash="$2b$12$OPugyOgScd78jz2GOzKaoOcaxpFAmI7RCS3oWqG5wOY4Vy7A4EMTS",
        ),
    ]

    return AuthService(UserStore(users))


auth_service = build_default_auth_service()

__all__ = ["AuthService", "auth_service", "build_default_auth_service"]
