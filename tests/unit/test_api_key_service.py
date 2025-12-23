from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.services.api_key_service import (
    create_api_key, 
    list_api_keys, 
    revoke_api_key,
)


@pytest.mark.asyncio
async def test_create_api_key_adds_and_persists_key():
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    existing_subscription = Subscription(user_id=42, plan_id=1)
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_subscription
    session.execute.return_value = result

    async def _refresh(obj: APIKey):
        obj.id = 123
        obj.is_active = True

    session.refresh.side_effect = _refresh

    key = await create_api_key(session, user_id=42)

    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert isinstance(added, APIKey)
    assert added.user_id == 42

    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(added)
    assert key is added
    assert key.id == 123
    assert key.is_active is True


@pytest.mark.asyncio
async def test_list_api_keys_returns_scalar_results():
    session = MagicMock()
    session.execute = AsyncMock()

    key1 = APIKey(user_id=7)
    key1.id = 1
    key1.is_active = True
    key2 = APIKey(user_id=7)
    key2.id = 2
    key2.is_active = True

    result = MagicMock()
    result.scalars.return_value = [key1, key2]
    session.execute.return_value = result

    keys = await list_api_keys(session, user_id=7)

    session.execute.assert_awaited_once()
    assert keys == [key1, key2]


@pytest.mark.asyncio
async def test_revoke_api_key_sets_inactive_and_commits_when_found():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    key = APIKey(user_id=9)
    key.id = 55
    key.is_active = True

    result = MagicMock()
    result.scalar_one_or_none.return_value = key
    session.execute.return_value = result

    await revoke_api_key(session, key_id=55, user_id=9)

    assert key.is_active is False
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_api_key_noops_when_not_found():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    await revoke_api_key(session, key_id=999, user_id=9)

    session.execute.assert_awaited_once()
    session.commit.assert_not_awaited()
