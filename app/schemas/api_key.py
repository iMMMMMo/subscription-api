from datetime import datetime

from pydantic import BaseModel, ConfigDict


class APIKeyRead(BaseModel):
    id: int
    key: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
