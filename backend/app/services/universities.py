from sqlalchemy.orm import Session

from app.models.university import University


class UnknownUniversity(Exception):
    """목록에 없는 대학명. API 계층이 422로 바꾼다 (설계 §5.1).

    서비스는 HTTP를 모른다 (매칭 설계 §2.1).
    """

    def __init__(self, name: str):
        self.name = name
        super().__init__(name)


def known_names(db: Session) -> set[str]:
    """신규 입력에 쓸 수 있는 활성 대학명 (설계 §5.3)."""
    rows = db.query(University.name).filter(University.active.is_(True)).all()
    return {name for (name,) in rows}


def require_known(db: Session, *names: str) -> None:
    """하나라도 목록 밖이면 UnknownUniversity.

    호출자가 strip한 값을 넘긴다 — 여기서 정규화하지 않는다. 저장되는 값과
    검증되는 값이 반드시 같아야 하기 때문이다.
    """
    allowed = known_names(db)
    for name in names:
        if name not in allowed:
            raise UnknownUniversity(name)
