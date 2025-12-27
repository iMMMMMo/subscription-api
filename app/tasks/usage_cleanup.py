import asyncio
from datetime import timedelta

from sqlalchemy import delete

from app.core.time import utc_today
from app.db.session import AsyncSessionLocal
from app.models.usage import Usage


async def cleanup_old_usage(days_to_keep: int = 30):
    cutoff = utc_today() - timedelta(days=days_to_keep)

    async with AsyncSessionLocal() as session:
        await session.execute(delete(Usage).where(Usage.day < cutoff))
        await session.commit()


async def start_usage_cleanup_loop():
    try:
        while True:
            await cleanup_old_usage()
            await asyncio.sleep(24 * 60 * 60)
    except asyncio.CancelledError:
        raise
