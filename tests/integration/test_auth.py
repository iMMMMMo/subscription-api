import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, *, email: str, password: str = "pass123"):
    return await client.post(
            "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )


async def _login(client: AsyncClient, *, email: str, password: str = "pass123"):
    return await client.post(
            "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    email = "pytest-user@example.com"

    resp = await _register(client, email=email)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert "id" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(client: AsyncClient):
    email = "pytest-user@example.com"

    first = await _register(client, email=email)
    assert first.status_code == 201

    second = await _register(client, email=email)
    assert second.status_code == 400
    detail = (second.json().get("detail") or "").lower()
    assert "already" in detail


@pytest.mark.asyncio
async def test_login_success_returns_tokens(client: AsyncClient):
    email = "pytest-user@example.com"
    await _register(client, email=email)

    resp = await _login(client, email=email)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("token_type") == "bearer"
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    email = "pytest-user@example.com"
    await _register(client, email=email, password="correct-pass")

    resp = await _login(client, email=email, password="wrong-pass")
    assert resp.status_code == 401
    detail = (resp.json().get("detail") or "").lower()
    assert "credential" in detail


@pytest.mark.asyncio
async def test_me_requires_bearer_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_success(client: AsyncClient):
    email = "pytest-user@example.com"
    await _register(client, email=email)
    login_resp = await _login(client, email=email)
    tokens = login_resp.json()

    resp = await client.get(
    "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == email


@pytest.mark.asyncio
async def test_refresh_success_returns_new_tokens(client: AsyncClient):
    email = "pytest-user@example.com"
    await _register(client, email=email)
    login_resp = await _login(client, email=email)
    tokens = login_resp.json()

    resp = await client.post(
    "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    refreshed = resp.json()
    assert refreshed.get("token_type") == "bearer"
    assert "access_token" in refreshed
    assert "refresh_token" in refreshed


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(client: AsyncClient):
    email = "pytest-user@example.com"
    await _register(client, email=email)
    login_resp = await _login(client, email=email)
    tokens = login_resp.json()

    resp = await client.post(
    "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert resp.status_code == 401
