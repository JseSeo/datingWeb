from pydantic import BaseModel, ConfigDict, Field


class UniversityWeightIn(BaseModel):
    """생성·수정 공용 (설계 §7).

    university_b는 빈 문자열이 기본이다 — 단일 대학 규칙을 뜻한다.
    """

    university_a: str = Field(min_length=1, max_length=100)
    university_b: str = Field(default="", max_length=100)
    bonus: int  # 음수 허용 = 페널티
    active: bool = True
    note: str | None = Field(default=None, max_length=200)


class UniversityWeightOut(BaseModel):
    id: int
    university_a: str
    university_b: str
    bonus: int
    active: bool
    note: str | None

    model_config = ConfigDict(from_attributes=True)
