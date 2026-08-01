from datetime import datetime
from pydantic import BaseModel, Field

from app.models.report import ReportType


class ReportCreate(BaseModel):
    type: ReportType
    target_name: str | None = Field(default=None, max_length=100)
    target_university: str | None = Field(default=None, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


class ReportOut(BaseModel):
    id: int
    type: ReportType
    target_name: str | None
    target_university: str | None
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
