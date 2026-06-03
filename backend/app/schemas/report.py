from datetime import datetime
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    target_id: int
    reason: str = Field(min_length=1)


class ReportOut(BaseModel):
    id: int
    reporter_id: int
    target_id: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
