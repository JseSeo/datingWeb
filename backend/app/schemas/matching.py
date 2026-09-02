from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchingRunOut(BaseModel):
    """매칭 실행 결과 요약 (설계 §7)."""

    matched: int      # 만들어진 짝 수
    unmatched: int    # 풀에 있었지만 못 붙은 인원 수
    guaranteed: int   # 보장으로 먼저 확정된 짝 수

    model_config = ConfigDict(from_attributes=True)


class MatchResultOut(BaseModel):
    """내 매칭 결과 (설계 §7.1).

    프로필 사진·자기소개·score는 담지 않는다 — 노출 최소화(§8)와
    score 비공개(§7.1) 때문이다.
    """

    name: str
    university: str
    instagram: str | None
    kakao_id: str | None
    phone: str | None
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)
