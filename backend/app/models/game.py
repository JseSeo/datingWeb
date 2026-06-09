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
            "person_a_name", "person_a_university",
            "person_b_name", "person_b_university",
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class RedThread(Base):
    """붉은 실: 양쪽이 서로 이름+학교 입력 시 100% 매칭 (확률 적용은 매칭 알고리즘 영역)"""
    __tablename__ = "red_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_university: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
