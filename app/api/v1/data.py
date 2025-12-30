from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.api_key_guard import api_key_guard
from app.db.session import get_session
from app.models.api_key import APIKey
from app.services.usage_service import get_usage

router = APIRouter(tags=["data"])


@router.get("/data")
async def get_data(
    api_key: APIKey = Depends(api_key_guard),
    session: AsyncSession = Depends(get_session),
):
    usage = await get_usage(session, api_key_id=api_key.id)
    return {
        "message": "ok",
        "api_key_id": api_key.id,
        "usage": usage,
    }
