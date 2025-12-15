from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.api_key import APIKeyRead
from app.services.api_key_service import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)
from app.core.security import get_current_subject

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=APIKeyRead, status_code=status.HTTP_201_CREATED)
async def create_key(
    subject: str = Depends(get_current_subject),
    session: AsyncSession = Depends(get_session),
):
    api_key = await create_api_key(
        session,
        user_id=int(subject),
    )
    return api_key


@router.get("", response_model=list[APIKeyRead])
async def list_keys(
    subject: str = Depends(get_current_subject),
    session: AsyncSession = Depends(get_session),
):
    return await list_api_keys(
        session,
        user_id=int(subject),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: int,
    subject: str = Depends(get_current_subject),
    session: AsyncSession = Depends(get_session),
):
    await revoke_api_key(
        session,
        key_id=key_id,
        user_id=int(subject),
    )
