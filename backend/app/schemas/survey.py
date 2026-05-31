from datetime import datetime
from pydantic import BaseModel


class SurveySubmit(BaseModel):
    answers: dict


class SurveyOut(BaseModel):
    answers: dict
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
