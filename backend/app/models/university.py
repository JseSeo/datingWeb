from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class University(Base):
    """가입·지목·가중치 규칙에서 고를 수 있는 대학 목록 (설계 §4.1).

    이름 변경 기능은 없다. 대학명은 users·ojakgyo·red_threads·
    matching_university_weights에 문자열로 복사 저장되므로, 여기서 이름을 고치면
    그 행들이 전부 고아가 된다 — 지금 고치려는 그 버그가 그대로 재발한다.
    """

    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    # 삭제 대신 끈다 — 이미 그 대학으로 가입한 유저는 그대로 매칭된다 (설계 §5.3)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
