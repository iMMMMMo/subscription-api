import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "api-user@example.com",
            "password": "pass123",
            "full_name": "API User",
        },
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "api-user@example.com",
            "password": "pass123",
        },
    )
    return resp.json()


async def _create_api_key(client: AsyncClient, access_token: str) -> str:
    resp = await client.post(
        "/api/v1/api-keys",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    return resp.json()["key"]


async def _get_data(client: AsyncClient, *, api_key: str):
    return await client.get(
        "/api/v1/data",
        headers={"X-API-Key": api_key},
    )


@pytest.mark.asyncio
async def test_api_access_without_key_returns_401(client: AsyncClient):
    resp = await _get_data(client, api_key="")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_access_with_invalid_key_returns_401(client: AsyncClient):
    resp = await _get_data(
        client,
        api_key="invalid-key",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_access_with_valid_key_within_limit(client: AsyncClient):
    tokens = await _register_and_login(client)
    api_key = await _create_api_key(client, tokens["access_token"])

    resp = await _get_data(client, api_key=api_key)
    assert resp.status_code == 200
    assert resp.json()["message"] == "ok"
    assert resp.json()["usage"] == 1


@pytest.mark.asyncio
async def test_api_access_exceeding_limit_returns_429(client: AsyncClient):
    tokens = await _register_and_login(client)
    api_key = await _create_api_key(client, tokens["access_token"])

    resp1 = await _get_data(client, api_key=api_key)
    assert resp1.status_code == 200
    assert resp1.json()["usage"] == 1

    resp2 = await _get_data(client, api_key=api_key)
    assert resp2.status_code == 200
    assert resp2.json()["usage"] == 2

    resp3 = await _get_data(client, api_key=api_key)
    assert resp3.status_code == 429
    assert "limit" in resp3.json()["detail"].lower()
