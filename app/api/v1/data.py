from fastapi import APIRouter, Depends

from app.api.dependencies.api_key_access import api_key_access
from app.models.api_key import APIKey

router = APIRouter(prefix="/api/v1", tags=["data"])


@router.get("/data")
async def get_data(api_key: APIKey = Depends(api_key_access)):
    return {
        "message": "ok",
        "api_key_id": api_key.id,
    }
