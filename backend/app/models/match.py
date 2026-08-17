import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RoundStatus(str, enum.Enum):
    pending = "pending"
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
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, name="round_status"), default=RoundStatus.pending, nullable=False
    )

    matches: Mapped[list["Match"]] = relationship("Match", back_populates="round")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    match_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("match_rounds.id"), nullable=False
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    round: Mapped["MatchRound"] = relationship("MatchRound", back_populates="matches")
