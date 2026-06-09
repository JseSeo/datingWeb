from datetime import datetime
from pydantic import BaseModel, Field


class OjakgyoCreate(BaseModel):
    person_a_name: str = Field(min_length=1)
    person_a_university: str = Field(min_length=1)
    person_b_name: str = Field(min_length=1)
    person_b_university: str = Field(min_length=1)


class OjakgyoOut(BaseModel):
    id: int
    recommender_id: int
    person_a_name: str
    person_a_university: str
    person_b_name: str
    person_b_university: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RedThreadTarget(BaseModel):
    target_name: str = Field(min_length=1)
    target_university: str = Field(min_length=1)


class RedThreadSubmit(BaseModel):
    targets: list[RedThreadTarget] = Field(min_length=1, max_length=2)


class RedThreadTargetOut(BaseModel):
    target_name: str
    target_university: str

    model_config = {"from_attributes": True}


class RedThreadOut(BaseModel):
    targets: list[RedThreadTargetOut]


class RedThreadReceivedOut(BaseModel):
    count: int
