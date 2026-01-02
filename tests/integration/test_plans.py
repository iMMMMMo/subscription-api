import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_public_plans_list_returns_active_plans(client: AsyncClient):
    resp = await client.get("/api/v1/plans")
    assert resp.status_code == 200

    plans = resp.json()
    assert isinstance(plans, list)
    assert any(p["name"] == "FREE" and p["request_limit"] == 2 for p in plans)

    first = plans[0]
    assert set(first.keys()) == {"name", "request_limit"}
