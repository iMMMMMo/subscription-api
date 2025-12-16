from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import Usage


async def increment_usage(
    session: AsyncSession,
    *,
    api_key_id: int,
) -> int:
    today = date.today()

    result = await session.execute(
        select(Usage).where(
            Usage.api_key_id == api_key_id,
            Usage.day == today,
        )
    )
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = Usage(
            api_key_id=api_key_id,
            day=today,
            request_count=1,
        )
        session.add(usage)
    else:
        usage.request_count += 1

    await session.commit()
    return usage.request_count
