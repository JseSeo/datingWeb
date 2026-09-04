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
    person_a_admission_year: int
    person_b_name: str
    person_b_university: str
    person_b_admission_year: int
    created_at: datetime

    model_config = {"from_attributes": True}


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
    target_admission_year: int

    model_config = {"from_attributes": True}


class RedThreadOut(BaseModel):
    targets: list[RedThreadTargetOut]


class RedThreadReceivedOut(BaseModel):
    count: int
