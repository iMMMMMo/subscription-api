import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


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


async def _promote_to_superuser(session: AsyncSession, *, email: str) -> None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_superuser = True
    await session.commit()


async def _register_and_login_admin(client: AsyncClient, session: AsyncSession) -> dict:
    email = "admin@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "admin-pass",
            "full_name": "Admin User",
        },
    )

    await _promote_to_superuser(session, email=email)

    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "admin-pass",
        },
    )
    return resp.json()


async def _create_plan(
    client: AsyncClient,
    *,
    access_token: str,
    name: str,
    request_limit: int,
) -> Response:
    return await client.post(
        "/api/v1/admin/plans",
        headers=_auth_headers(access_token),
        json={"name": name, "request_limit": request_limit},
    )


@pytest.mark.asyncio
async def test_non_admin_cannot_create_plan(client: AsyncClient):
    tokens = await _register_and_login(client)
    token = tokens["access_token"]
    resp = await _create_plan(client, access_token=token, name="PRO", request_limit=100)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_plan(client: AsyncClient, session: AsyncSession):
    tokens = await _register_and_login_admin(client, session)
    token = tokens["access_token"]

    resp = await _create_plan(client, access_token=token, name="PRO", request_limit=100)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "PRO"
    assert body["request_limit"] == 100


@pytest.mark.asyncio
async def test_admin_can_list_all_plans(client: AsyncClient, session: AsyncSession):
    tokens = await _register_and_login_admin(client, session)
    token = tokens["access_token"]

    resp = await client.get(
        "/api/v1/admin/plans",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert "FREE" in names


@pytest.mark.asyncio
async def test_admin_can_update_plan(client: AsyncClient, session: AsyncSession):
    tokens = await _register_and_login_admin(client, session)
    token = tokens["access_token"]

    create = await _create_plan(
        client, access_token=token, name="PRO", request_limit=10
    )
    assert create.status_code == 201
    plan_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/plans/{plan_id}",
        headers=_auth_headers(token),
        json={"request_limit": 50},
    )
    assert resp.status_code == 200
    assert resp.json()["request_limit"] == 50
