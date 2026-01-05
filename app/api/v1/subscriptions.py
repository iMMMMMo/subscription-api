from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_subject
from app.db.session import get_session
from app.models.plan import Plan
from app.schemas.subscription import SubscriptionRead, SubscriptionSwitchRequest
from app.services.subscription_service import switch_subscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/switch", response_model=SubscriptionRead)
async def switch(
    data: SubscriptionSwitchRequest,
    subject: str = Depends(get_current_subject),
    session: AsyncSession = Depends(get_session),
):
    subscription = await switch_subscription(
        session,
        user_id=int(subject),
        plan_name=data.plan_name,
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    result = await session.execute(select(Plan).where(Plan.id == subscription.plan_id))
    plan = result.scalar_one()

    return {
        "id": subscription.id,
        "is_active": subscription.is_active,
        "started_at": subscription.started_at,
        "plan": {
            "name": plan.name,
            "request_limit": plan.request_limit,
        },
    }
