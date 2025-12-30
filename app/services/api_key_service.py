from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.services.subscription_service import ensure_active_subscription


async def create_api_key(
    session: AsyncSession,
    *,
    user_id: int,
) -> APIKey:
    await ensure_active_subscription(
        session,
        user_id=user_id,
    )

    api_key = APIKey(user_id=user_id)
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key


async def list_api_keys(
    session: AsyncSession,
    *,
    user_id: int,
) -> list[APIKey]:
    result = await session.execute(
        select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.is_active.is_(True),
        )
    )
    return list(result.scalars())


async def revoke_api_key(
    session: AsyncSession,
    *,
    key_id: int,
    user_id: int,
) -> APIKey | None:
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user_id,
            APIKey.is_active.is_(True),
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return None

    api_key.is_active = False
    await session.commit()
    return api_key
