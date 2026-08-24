from pydantic import BaseModel, ConfigDict


class MatchingRunOut(BaseModel):
    """매칭 실행 결과 요약 (설계 §7)."""

    matched: int      # 만들어진 짝 수
    unmatched: int    # 풀에 있었지만 못 붙은 인원 수
    guaranteed: int   # 보장으로 먼저 확정된 짝 수

    model_config = ConfigDict(from_attributes=True)
