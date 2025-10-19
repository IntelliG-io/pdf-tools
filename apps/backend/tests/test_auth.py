"""Integration tests for the authentication endpoints."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app

client = TestClient(app)


def test_login_returns_token_pair() -> None:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tokenType"] == "bearer"
    assert "accessToken" in payload
    assert "refreshToken" in payload
    assert payload["user"]["username"] == "admin"


def test_protected_endpoint_requires_authentication() -> None:
    response = client.get("/api/admin/overview")
    assert response.status_code == 401


def test_role_guard_blocks_non_admin_users() -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": "analyst", "password": "userpass"},
    )
    tokens = login_response.json()
    response = client.get(
        "/api/admin/overview",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
    )
    assert response.status_code == 403


def test_refresh_issues_new_tokens() -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )
    tokens = login_response.json()

    refresh_response = client.post(
        "/auth/refresh",
        json={"refreshToken": tokens["refreshToken"]},
    )

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["accessToken"] != tokens["accessToken"]
    assert refreshed["refreshToken"] != tokens["refreshToken"]


def test_admin_route_allows_admin_user() -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "adminpass"},
    )
    tokens = login_response.json()

    response = client.get(
        "/api/admin/overview",
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
