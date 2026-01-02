from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan


async def create_plan(
    session: AsyncSession,
    *,
    name: str,
    request_limit: int,
    is_active: bool,
) -> Plan:
    plan = Plan(
        name=name,
        request_limit=request_limit,
        is_active=is_active,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def list_public_plans(session: AsyncSession) -> list[Plan]:
    stmt = (
        select(Plan)
        .where(Plan.is_active.is_(True))
        .order_by(Plan.request_limit, Plan.name, Plan.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars())


async def list_admin_plans(
    session: AsyncSession,
    *,
    include_inactive: bool = True,
) -> list[Plan]:
    stmt = select(Plan)
    if not include_inactive:
        stmt = stmt.where(Plan.is_active.is_(True))

    result = await session.execute(stmt)
    return list(result.scalars())


async def update_plan(
    session: AsyncSession,
    *,
    plan_id: int,
    request_limit: int | None = None,
    is_active: bool | None = None,
) -> Plan | None:
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return None

    if request_limit is not None:
        plan.request_limit = request_limit
    if is_active is not None:
        plan.is_active = is_active

    await session.commit()
    await session.refresh(plan)
    return plan
