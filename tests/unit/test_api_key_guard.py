import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.dependencies.api_key_guard import (
    _get_api_key,
    _get_active_plan,
    _enforce_usage_limit,
)
from app.models.api_key import APIKey
from app.models.plan import Plan


@pytest.mark.asyncio
async def test_get_api_key_missing_header_raises_401():
    session = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await _get_api_key(session=session, raw_key=None)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_api_key_invalid_key_raises_401():
    session = MagicMock()
    session.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    with pytest.raises(HTTPException) as exc:
        await _get_api_key(session=session, raw_key="invalid")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_api_key_valid_returns_api_key():
    session = MagicMock()
    session.execute = AsyncMock()

    api_key = APIKey(user_id=1)
    api_key.id = 10
    api_key.is_active = True

    result = MagicMock()
    result.scalar_one_or_none.return_value = api_key
    session.execute.return_value = result

    returned = await _get_api_key(session=session, raw_key="valid-key")

    assert returned is api_key


@pytest.mark.asyncio
async def test_get_active_plan_missing_raises_403(monkeypatch):
    session = MagicMock()

    async def fake_get_active_plan(*_, **__):
        return None

    monkeypatch.setattr(
        "app.api.dependencies.api_key_guard.get_active_plan_for_user",
        fake_get_active_plan,
    )

    with pytest.raises(HTTPException) as exc:
        await _get_active_plan(session=session, user_id=1)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_active_plan_returns_plan(monkeypatch):
    session = MagicMock()

    plan = Plan(name="FREE", request_limit=100)
    plan.id = 1

    async def fake_get_active_plan(*_, **__):
        return plan

    monkeypatch.setattr(
        "app.api.dependencies.api_key_guard.get_active_plan_for_user",
        fake_get_active_plan,
    )

    returned = await _get_active_plan(session=session, user_id=1)

    assert returned is plan


@pytest.mark.asyncio
async def test_enforce_usage_within_limit_passes(monkeypatch):
    session = MagicMock()

    async def fake_increment(*_, **__):
        return 2

    monkeypatch.setattr(
        "app.api.dependencies.api_key_guard.increment_usage",
        fake_increment,
    )

    await _enforce_usage_limit(
        session=session,
        api_key_id=1,
        request_limit=3,
    )


@pytest.mark.asyncio
async def test_enforce_usage_exceeded_raises_429(monkeypatch):
    session = MagicMock()

    async def fake_increment(*_, **__):
        return 5

    monkeypatch.setattr(
        "app.api.dependencies.api_key_guard.increment_usage",
        fake_increment,
    )

    with pytest.raises(HTTPException) as exc:
        await _enforce_usage_limit(
            session=session,
            api_key_id=1,
            request_limit=3,
        )

    assert exc.value.status_code == 429
