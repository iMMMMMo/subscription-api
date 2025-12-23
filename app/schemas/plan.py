from pydantic import BaseModel, ConfigDict


class PlanCreate(BaseModel):
    name: str
    request_limit: int
    is_active: bool = True


class PlanUpdate(BaseModel):
    request_limit: int | None = None
    is_active: bool | None = None


class PlanRead(BaseModel):
    id: int
    name: str
    request_limit: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
