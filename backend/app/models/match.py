import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RoundStatus(str, enum.Enum):
    pending = "pending"
    running = "running"  # 실행 중. 서버가 죽으면 여기 멈춰 관리자가 인지한다 (설계 §5.5)
    done = "done"


class MatchRound(Base):
    __tablename__ = "match_rounds"
    # 같은 시각 라운드 2건 금지. 앱 검사(_reject_duplicate)의 경쟁 구간을 DB가 막는다
    __table_args__ = (
        Index("uq_match_rounds_scheduled_at", "scheduled_at", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 마지막 실행을 시작한 시각. running 선점 때 기록되고 지워지지 않는다.
    # 되돌리기 유예(RUNNING_GRACE) 판정의 기준값이다
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, name="round_status"), default=RoundStatus.pending, nullable=False
    )

    matches: Mapped[list["Match"]] = relationship("Match", back_populates="round")


class Match(Base):
    __tablename__ = "matches"
    # 한 라운드에서 한 사람이 두 번 매칭되는 사고를 DB가 막는다 (설계 §6.1)
    __table_args__ = (
        UniqueConstraint("match_round_id", "user_a_id", name="uq_matches_round_user_a"),
        UniqueConstraint("match_round_id", "user_b_id", name="uq_matches_round_user_b"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    match_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("match_rounds.id"), nullable=False
    )
    # 보정 전 궁합 점수. 카테고리 가중치를 나중에 조정하려면 이 기록이 필요하다 (설계 §6.1)
    score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    round: Mapped["MatchRound"] = relationship("MatchRound", back_populates="matches")
