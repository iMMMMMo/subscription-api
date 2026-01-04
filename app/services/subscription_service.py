from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.plan import Plan
from app.models.subscription import Subscription


async def get_active_plan_for_user(
    session: AsyncSession,
    *,
    user_id: int,
) -> Plan | None:
    result = await session.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
            Plan.is_active.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def ensure_active_subscription(
    session: AsyncSession,
    *,
    user_id: int,
) -> Subscription:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription:
        return subscription

    result = await session.execute(
        select(Plan).where(
            Plan.name == settings.default_plan_name,
            Plan.is_active.is_(True),
        )
    )
    plan = result.scalar_one()

    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
    )
    session.add(subscription)
    try:
        await session.commit()
        await session.refresh(subscription)
        return subscription
    except IntegrityError:
        await session.rollback()

        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
            )
        )
        existing = result.scalar_one()
        return existing


async def switch_subscription(
    session: AsyncSession,
    *,
    user_id: int,
    plan_name: str,
) -> Subscription | None:
    result = await session.execute(
        select(Plan).where(
            Plan.name == plan_name,
            Plan.is_active.is_(True),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        return None

    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
        )
    )
    current = result.scalar_one_or_none()

    if current and current.plan_id == plan.id:
        return current

    if current:
        current.is_active = False

    new_subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        is_active=True,
    )
    session.add(new_subscription)

    try:
        await session.commit()
        await session.refresh(new_subscription)
        return new_subscription
    except IntegrityError:
        await session.rollback()

        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
