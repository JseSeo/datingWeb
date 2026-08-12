from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime

    model_config = ConfigDict(from_attributes=True)
