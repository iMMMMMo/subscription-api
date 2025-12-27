from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.services import usage_service


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
async def test_usage_resets_on_new_day(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    tokens = await _register_and_login(client)
    api_key = await _create_api_key(client, tokens["access_token"])

    today = date.today()
    tomorrow = today + timedelta(days=1)

    monkeypatch.setattr(usage_service, "utc_today", lambda: today)

    # day 1: use up the daily limit (FREE plan in tests is 2 per day)
    day1_req1 = await _get_data(client, api_key=api_key)
    assert day1_req1.status_code == 200
    day1_req2 = await _get_data(client, api_key=api_key)
    assert day1_req2.status_code == 200

    # day 2: usage should reset, so a new request should be allowed again
    monkeypatch.setattr(usage_service, "utc_today", lambda: tomorrow)

    day2_req1 = await _get_data(client, api_key=api_key)
    assert day2_req1.status_code == 200
