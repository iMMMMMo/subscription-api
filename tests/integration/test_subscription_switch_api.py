import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "switch-api@example.com",
            "password": "pass123",
            "full_name": "API User",
        },
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "switch-api@example.com",
            "password": "pass123",
        },
    )
    return resp.json()


@pytest.mark.asyncio
async def test_switch_subscription_endpoint_switches_plan(client: AsyncClient):
    tokens = await _register_and_login(client)

    resp = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "FREE"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["is_active"] is True
    assert data["plan"]["name"] == "FREE"
    assert data["plan"]["request_limit"] == 2
