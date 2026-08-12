from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import RoundStatus


class MatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchRoundIn(BaseModel):
    """생성·수정 공용. 편집 가능한 필드는 scheduled_at 하나뿐이다."""

    scheduled_at: datetime


class AdminMatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime
    status: RoundStatus

    model_config = ConfigDict(from_attributes=True)
