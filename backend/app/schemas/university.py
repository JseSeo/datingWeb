from pydantic import BaseModel, ConfigDict, Field, field_validator


class UniversityIn(BaseModel):
    """추가 전용. 이름 변경은 지원하지 않는다 (설계 §4.1)."""

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("대학명을 입력하세요")
        return stripped


class UniversityActiveUpdate(BaseModel):
    active: bool


class UniversityOut(BaseModel):
    id: int
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)
