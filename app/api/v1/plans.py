from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.plan import PlanPublicRead
from app.services.plan_service import list_public_plans as list_public_plans_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanPublicRead])
async def list_public_plans(
    session: AsyncSession = Depends(get_session),
):
    return await list_public_plans_service(session)
