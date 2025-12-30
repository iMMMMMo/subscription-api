from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_today
from app.models.usage import Usage


async def increment_usage(
    session: AsyncSession,
    *,
    api_key_id: int,
) -> int:
    today = utc_today()

    result = await session.execute(
        update(Usage)
        .where(
            Usage.api_key_id == api_key_id,
            Usage.day == today,
        )
        .values(request_count=Usage.request_count + 1)
    )

    if getattr(result, "rowcount", 0) == 0:
        session.add(
            Usage(
                api_key_id=api_key_id,
                day=today,
                request_count=1,
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await session.execute(
                update(Usage)
                .where(
                    Usage.api_key_id == api_key_id,
                    Usage.day == today,
                )
                .values(request_count=Usage.request_count + 1)
            )
            await session.commit()
    else:
        await session.commit()

    current = await session.execute(
        select(Usage.request_count).where(
            Usage.api_key_id == api_key_id,
            Usage.day == today,
        )
    )
    return int(current.scalar_one())


async def get_usage(
    session: AsyncSession,
    *,
    api_key_id: int,
) -> int:
    today = utc_today()

    result = await session.execute(
        select(Usage.request_count).where(
            Usage.api_key_id == api_key_id,
            Usage.day == today,
        )
    )
    count = result.scalar_one_or_none()
    return int(count or 0)
