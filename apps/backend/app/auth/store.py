"""In-memory persistence for users and refresh tokens."""

from __future__ import annotations

from threading import Lock
from typing import Dict, Iterable, Optional

from .models import RefreshTokenRecord, User


class UserStore:
    """A very small in-memory user repository used for demo purposes."""

    def __init__(self, users: Iterable[User]):
        self._users_by_username: Dict[str, User] = {user.username: user for user in users}
        self._users_by_id: Dict[int, User] = {user.id: user for user in users}
        self._refresh_tokens: Dict[str, RefreshTokenRecord] = {}
        self._user_refresh_index: Dict[int, set[str]] = {}
        self._lock = Lock()

    def get_by_username(self, username: str) -> Optional[User]:
        return self._users_by_username.get(username)

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._users_by_id.get(user_id)

    def clear_refresh_tokens(self, user_id: int) -> None:
        """Remove all refresh tokens currently associated with ``user_id``."""

        with self._lock:
            tokens = self._user_refresh_index.pop(user_id, set())
            for token in tokens:
                self._refresh_tokens.pop(token, None)

    def add_refresh_token(self, record: RefreshTokenRecord) -> None:
        """Persist ``record`` so refresh flows can validate incoming tokens."""

        with self._lock:
            self._refresh_tokens[record.token] = record
            tokens = self._user_refresh_index.setdefault(record.user_id, set())
            tokens.add(record.token)

    def pop_refresh_token(self, token: str) -> Optional[RefreshTokenRecord]:
        """Remove and return the refresh token ``token`` if it exists."""

        with self._lock:
            record = self._refresh_tokens.pop(token, None)
            if not record:
                return None

            tokens = self._user_refresh_index.get(record.user_id)
            if tokens is not None:
                tokens.discard(token)
                if not tokens:
                    self._user_refresh_index.pop(record.user_id, None)
            return record


__all__ = ["UserStore"]
