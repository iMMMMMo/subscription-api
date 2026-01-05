import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User


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


@pytest.mark.asyncio
async def test_switch_subscription_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/subscriptions/switch",
        json={"plan_name": "FREE"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_switch_subscription_nonexistent_plan_returns_404(client: AsyncClient):
    tokens = await _register_and_login(client)

    resp = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "DOES_NOT_EXIST"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"].lower() == "plan not found"


@pytest.mark.asyncio
async def test_switch_subscription_inactive_plan_returns_404(
    client: AsyncClient,
    session: AsyncSession,
):
    session.add(Plan(name="HIDDEN", request_limit=999, is_active=False))
    await session.commit()

    tokens = await _register_and_login(client)

    resp = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "HIDDEN"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_switch_subscription_same_plan_is_noop(
    client: AsyncClient,
    session: AsyncSession,
):
    tokens = await _register_and_login(client)

    first = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "FREE"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "FREE"},
    )
    assert second.status_code == 200

    assert second.json()["id"] == first.json()["id"]

    result = await session.execute(select(Subscription))
    subs = list(result.scalars())
    assert len(subs) == 1


@pytest.mark.asyncio
async def test_switch_subscription_free_to_pro_creates_history(
    client: AsyncClient,
    session: AsyncSession,
):
    pro = Plan(name="PRO", request_limit=10, is_active=True)
    session.add(pro)
    await session.commit()
    await session.refresh(pro)
    pro_id = pro.id

    tokens = await _register_and_login(client)

    first = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "FREE"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/subscriptions/switch",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"plan_name": "PRO"},
    )
    assert second.status_code == 200
    assert second.json()["plan"]["name"] == "PRO"

    result = await session.execute(
        select(User).where(User.email == "switch-api@example.com")
    )
    user = result.scalar_one()

    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subs = list(result.scalars())

    assert len(subs) == 2
    assert sum(1 for s in subs if s.is_active) == 1
    assert next(s for s in subs if s.is_active).plan_id == pro_id
