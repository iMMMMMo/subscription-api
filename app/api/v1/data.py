from fastapi import APIRouter, Depends

from app.api.dependencies.api_key_guard import api_key_guard
from app.models.api_key import APIKey

router = APIRouter(tags=["data"])


@router.get("/data")
async def get_data(api_key: APIKey = Depends(api_key_guard)):
    return {
        "message": "ok",
        "api_key_id": api_key.id,
    }
