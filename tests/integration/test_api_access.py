import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> dict:
    await client.post(
        "/auth/register",
        json={
            "email": "api-user@example.com",
            "password": "pass123",
            "full_name": "API User",
        },
    )

    resp = await client.post(
        "/auth/login",
        json={
            "email": "api-user@example.com",
            "password": "pass123",
        },
    )
    return resp.json()


async def _create_api_key(client: AsyncClient, access_token: str) -> str:
    resp = await client.post(
        "/api-keys",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return resp.json()["key"]


@pytest.mark.asyncio
async def test_api_access_without_key_returns_401(client: AsyncClient):
    resp = await client.get("/api/v1/data")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_access_with_invalid_key_returns_401(client: AsyncClient):
    resp = await client.get(
        "/api/v1/data",
        headers={"X-API-Key": "invalid-key"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_access_with_valid_key_within_limit(client: AsyncClient):
    tokens = await _register_and_login(client)
    api_key = await _create_api_key(client, tokens["access_token"])

    resp = await client.get(
        "/api/v1/data",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "ok"


@pytest.mark.asyncio
async def test_api_access_exceeding_limit_returns_429(client: AsyncClient):
    tokens = await _register_and_login(client)
    api_key = await _create_api_key(client, tokens["access_token"])

    resp1 = await client.get(
        "/api/v1/data",
        headers={"X-API-Key": api_key},
    )
    assert resp1.status_code == 200

    resp2 = await client.get(
        "/api/v1/data",
        headers={"X-API-Key": api_key},
    )
    assert resp2.status_code == 200

    resp3 = await client.get(
        "/api/v1/data",
        headers={"X-API-Key": api_key},
    )
    assert resp3.status_code == 429
    assert "limit" in resp3.json()["detail"].lower()
