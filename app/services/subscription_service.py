from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.plan import Plan


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
            Subscription.is_active == True,
            Plan.is_active == True,
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
            Subscription.is_active == True,
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription:
        return subscription

    result = await session.execute(
        select(Plan).where(
            Plan.name == "FREE",
            Plan.is_active == True,
        )
    )
    plan = result.scalar_one()

    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    return subscription