"""Pydantic models and dataclasses used by the authentication layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Internal representation of an application user."""

    id: int
    username: str
    full_name: str
    role: str
    password_hash: str

    model_config = ConfigDict(frozen=True)


class UserPublic(BaseModel):
    """Public view of a user returned to API clients."""

    id: int
    username: str
    full_name: str
    role: str


class AuthenticatedUser(UserPublic):
    """User record returned by authentication dependencies."""


class LoginRequest(BaseModel):
    """Credentials supplied by a user attempting to log in."""

    username: str
    password: str


class RefreshRequest(BaseModel):
    """Payload used to exchange a refresh token for new credentials."""

    refresh_token: str = Field(..., alias="refreshToken")

    model_config = ConfigDict(populate_by_name=True)


class TokenPair(BaseModel):
    """A bundle of access and refresh tokens returned to a client."""

    access_token: str = Field(..., alias="accessToken")
    refresh_token: str = Field(..., alias="refreshToken")
    token_type: str = Field("bearer", alias="tokenType")
    access_token_expires_in: int = Field(..., alias="accessTokenExpiresIn")
    refresh_token_expires_in: int = Field(..., alias="refreshTokenExpiresIn")
    user: UserPublic

    model_config = ConfigDict(populate_by_name=True)


@dataclass(frozen=True)
class RefreshTokenRecord:
    """Internal storage entry for an issued refresh token."""

    token: str
    user_id: int
    expires_at: datetime


class TokenPayload(BaseModel):
    """Decoded structure for JWT validation."""

    sub: str
    role: str
    type: str
    exp: int
    iat: int | None = None
    jti: str | None = None

    model_config = ConfigDict(from_attributes=True)
