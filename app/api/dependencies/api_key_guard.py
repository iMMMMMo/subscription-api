from fastapi import Header, HTTPException, status, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.api_key import APIKey
from app.models.plan import Plan
from app.services.subscription_service import get_active_plan_for_user
from app.services.usage_service import increment_usage

import logging


logger =  logging.getLogger("api.access")


async def _get_api_key(
    *,
    session: AsyncSession,
    raw_key: str | None,
) -> APIKey:
    if not raw_key:
        logger.warning(
            "api_key_missing",
            extra={"path": "api_key_guard"},
        )   
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key missing")

    result = await session.execute(
        select(APIKey).where(
            APIKey.key == raw_key,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        logger.warning(
            "api_key_invalid",
            extra={
                "key_prefix": raw_key[:4],
                "path": "api_key_guard",
            },
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return api_key


async def _get_active_plan(
    *,
    session: AsyncSession,
    user_id: int,
) -> Plan:
    plan = await get_active_plan_for_user(
        session,
        user_id=user_id,
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription",
        )
    return plan


async def _enforce_usage_limit(
    *,
    session: AsyncSession,
    api_key_id: int,
    request_limit: int,
) -> None:
    usage_count = await increment_usage(
        session,
        api_key_id=api_key_id,
    )

    if usage_count > request_limit:
        logger.info(
            "rate_limit_exceeded",
            extra={
                "api_key_id": api_key_id,
                "usage": usage_count,
                "limit": request_limit,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request limit exceeded",
        )


async def api_key_guard(
    x_api_key: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> APIKey:
    api_key = await _get_api_key(
        session=session,
        raw_key=x_api_key,
    )

    plan = await _get_active_plan(
        session=session,
        user_id=api_key.user_id,
    )

    await _enforce_usage_limit(
        session=session,
        api_key_id=api_key.id,
        request_limit=plan.request_limit,
    )

    return api_key
