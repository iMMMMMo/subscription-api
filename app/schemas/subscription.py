from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.plan import PlanPublicRead


class SubscriptionSwitchRequest(BaseModel):
    plan_name: str


class SubscriptionRead(BaseModel):
    id: int
    is_active: bool
    started_at: datetime
    plan: PlanPublicRead

    model_config = ConfigDict(from_attributes=True)
