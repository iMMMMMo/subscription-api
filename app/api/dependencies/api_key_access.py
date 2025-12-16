from fastapi import Header, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.api_key import APIKey
from app.services.subscription_service import get_active_plan_for_user
from app.services.usage_service import increment_usage


async def api_key_access(
    x_api_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> APIKey:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key missing")

    result = await session.execute(
        select(APIKey).where(
            APIKey.key == x_api_key,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    plan = await get_active_plan_for_user(
        session,
        user_id=api_key.user_id,
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active subscription")

    usage_count = await increment_usage(
        session,
        api_key_id=api_key.id,
    )

    if usage_count > plan.request_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request limit exceeded",
        )

    return api_key
