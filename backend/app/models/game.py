from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ojakgyo(Base):
    """오작교: 지목자(recommender)가 제3자로서 두 사람(이름+학교)을 지목 → 중매. 지목자 익명."""
    __tablename__ = "ojakgyo"
    __table_args__ = (
        UniqueConstraint(
            "recommender_id",
            "person_a_name", "person_a_university", "person_a_admission_year",
            "person_b_name", "person_b_university", "person_b_admission_year",
            name="uq_ojakgyo_recommender_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    person_a_name: Mapped[str] = mapped_column(String(100), nullable=False)
    person_a_university: Mapped[str] = mapped_column(String(100), nullable=False)
    person_b_name: Mapped[str] = mapped_column(String(100), nullable=False)
    person_b_university: Mapped[str] = mapped_column(String(100), nullable=False)
    # 0 = 미입력. nullable로 두면 유니크 인덱스가 NULL을 서로 다른 값으로 봐서
    # 같은 사람을 학번 없이 몇 번이고 중복 지목할 수 있게 된다 (설계 §4.2)
    person_a_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    person_b_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class RedThread(Base):
    """붉은 실: 유저가 최대 2명까지 이름+학교 입력. 양쪽 상호 입력 시 100% 매칭 (확률 적용은 매칭 알고리즘 영역)"""
    __tablename__ = "red_threads"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_name", "target_university", "target_admission_year",
            name="uq_red_thread_user_target",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_university: Mapped[str] = mapped_column(String(100), nullable=False)
    # 0 = 미입력 (설계 §4.2)
    target_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
