import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.subscription_service import switch_subscription


@pytest.mark.asyncio
async def test_switch_subscription_creates_active_subscription_when_missing(
    session: AsyncSession,
):
    session.add(Plan(name="PRO", request_limit=10, is_active=True))
    user = User(email="switch-1@example.com", hashed_password="pass123")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    sub = await switch_subscription(session, user_id=user.id, plan_name="PRO")
    assert sub is not None
    assert sub.user_id == user.id

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.is_active.is_(True),
        )
    )
    active = result.scalar_one_or_none()
    assert active is not None
    assert active.plan_id == sub.plan_id


@pytest.mark.asyncio
async def test_switch_subscription_deactivates_old_and_creates_new(
    session: AsyncSession,
):
    result = await session.execute(select(Plan).where(Plan.name == "FREE"))
    free = result.scalar_one()
    free_id = free.id

    pro = Plan(name="PRO2", request_limit=10, is_active=True)
    user = User(email="switch-2@example.com", hashed_password="pass123")
    session.add_all([pro, user])
    await session.commit()
    await session.refresh(user)
    await session.refresh(pro)
    pro_id = pro.id

    first = await switch_subscription(session, user_id=user.id, plan_name="FREE")
    assert first is not None
    assert first.plan_id == free_id

    second = await switch_subscription(session, user_id=user.id, plan_name="PRO2")
    assert second is not None
    assert second.plan_id == pro_id

    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subs = list(result.scalars())
    assert len(subs) == 2
    assert sum(1 for s in subs if s.is_active) == 1


@pytest.mark.asyncio
async def test_switch_subscription_returns_existing_when_same_plan(
    session: AsyncSession,
):
    user = User(email="switch-3@example.com", hashed_password="pass123")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    first = await switch_subscription(session, user_id=user.id, plan_name="FREE")
    second = await switch_subscription(session, user_id=user.id, plan_name="FREE")

    assert first is not None
    assert second is not None
    assert second.id == first.id
