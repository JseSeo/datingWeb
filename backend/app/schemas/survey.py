from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SurveySubmit(BaseModel):
    answers: dict


class SurveyOut(BaseModel):
    answers: dict
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChoiceOut(BaseModel):
    id: str
    label: str

    model_config = ConfigDict(from_attributes=True)


class FaceTypeOut(BaseModel):
    id: str
    label: str
    image: str

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    """카탈로그 응답 전용. `category`는 매칭 내부 전용이라 의도적으로 뺐다."""

    id: str
    section: str
    label: str
    type: str
    choices: list[ChoiceOut] | None = None
    face: bool = False
    rank_items: list[ChoiceOut] | None = None
    scale_labels: tuple[str, str] | None = None
    unit: str | None = None
    male_only: bool = False
    no_pref_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SurveyCatalogOut(BaseModel):
    questions: list[QuestionOut]
    face_types: list[FaceTypeOut]
    face_any_id: str
