from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.schemas.admission import check_admission_year


class OjakgyoCreate(BaseModel):
    person_a_name: str = Field(min_length=1, max_length=100)
    person_a_university: str = Field(min_length=1, max_length=100)
    person_a_admission_year: int | None = None
    person_b_name: str = Field(min_length=1, max_length=100)
    person_b_university: str = Field(min_length=1, max_length=100)
    person_b_admission_year: int | None = None

    @field_validator("person_a_admission_year", "person_b_admission_year")
    @classmethod
    def valid_admission_year(cls, v: int | None) -> int | None:
        return check_admission_year(v)


class OjakgyoOut(BaseModel):
    id: int
    recommender_id: int
    person_a_name: str
    person_a_university: str
    person_a_admission_year: int | None
    person_b_name: str
    person_b_university: str
    person_b_admission_year: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("person_a_admission_year", "person_b_admission_year")
    @classmethod
    def sentinel_to_none(cls, v: int | None) -> int | None:
        """저장은 0 센티넬이지만 API는 0을 요구한 적이 없다 — 응답에서도 미입력은 None (설계 §4.2)."""
        return None if v == 0 else v


class RedThreadTarget(BaseModel):
    target_name: str = Field(min_length=1, max_length=100)
    target_university: str = Field(min_length=1, max_length=100)
    target_admission_year: int | None = None

    @field_validator("target_admission_year")
    @classmethod
    def valid_admission_year(cls, v: int | None) -> int | None:
        return check_admission_year(v)


class RedThreadSubmit(BaseModel):
    targets: list[RedThreadTarget] = Field(min_length=1, max_length=2)


class RedThreadTargetOut(BaseModel):
    target_name: str
    target_university: str
    target_admission_year: int | None

    model_config = {"from_attributes": True}

    @field_validator("target_admission_year")
    @classmethod
    def sentinel_to_none(cls, v: int | None) -> int | None:
        """저장은 0 센티넬이지만 API는 0을 요구한 적이 없다 — 응답에서도 미입력은 None (설계 §4.2)."""
        return None if v == 0 else v


class RedThreadOut(BaseModel):
    targets: list[RedThreadTargetOut]


class RedThreadReceivedOut(BaseModel):
    count: int
