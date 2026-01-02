from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin import require_superuser
from app.db.session import get_session
from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from app.services.plan_service import (
    create_plan,
    update_plan,
)
from app.services.plan_service import (
    list_admin_plans as list_plans,
)

router = APIRouter(prefix="/admin/plans", tags=["admin"])


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
async def create(
    data: PlanCreate,
    _: Depends = Depends(require_superuser),
    session: AsyncSession = Depends(get_session),
):
    return await create_plan(
        session,
        name=data.name,
        request_limit=data.request_limit,
        is_active=data.is_active,
    )


@router.get("", response_model=list[PlanRead])
async def list_all(
    _: Depends = Depends(require_superuser),
    session: AsyncSession = Depends(get_session),
):
    return await list_plans(session, include_inactive=True)


@router.patch("/{plan_id}", response_model=PlanRead)
async def update(
    plan_id: int,
    data: PlanUpdate,
    _: Depends = Depends(require_superuser),
    session: AsyncSession = Depends(get_session),
):
    plan = await update_plan(
        session,
        plan_id=plan_id,
        request_limit=data.request_limit,
        is_active=data.is_active,
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )
    return plan
