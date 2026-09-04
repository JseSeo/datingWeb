from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.game import Ojakgyo, RedThread
from app.models.match import MatchingUniversityWeight
from app.models.university import University
from app.models.user import User
from app.schemas.university import (
    UniversityActiveUpdate,
    UniversityIn,
    UniversityOut,
)
from app.services.universities import UnknownUniversity, require_known

router = APIRouter(prefix="/universities", tags=["universities"])
admin_router = APIRouter(prefix="/admin/universities", tags=["universities"])


def validate_universities(db: Session, *names: str) -> None:
    """쓰기 경로 공용 — 도메인 예외를 HTTP 422로 바꾼다 (설계 §5.1).

    서비스가 HTTP를 모르므로 변환은 API 계층인 여기서 한 번만 한다.
    """
    try:
        require_known(db, *names)
    except UnknownUniversity as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"목록에 없는 대학입니다: {exc.name}",
        )


# 삭제 전에 훑을 참조 지점. 하나라도 걸리면 끄기만 허용한다 (설계 §4.1)
_REFERENCES = (
    User.university,
    Ojakgyo.person_a_university,
    Ojakgyo.person_b_university,
    RedThread.target_university,
    MatchingUniversityWeight.university_a,
    MatchingUniversityWeight.university_b,
)


def _is_referenced(db: Session, name: str) -> bool:
    return any(
        db.query(column).filter(column == name).first() is not None
        for column in _REFERENCES
    )


def _get(db: Session, university_id: int) -> University:
    university = db.get(University, university_id)
    if university is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 대학입니다"
        )
    return university


@router.get("", response_model=list[UniversityOut])
def list_active(db: Session = Depends(get_db)):
    """비인증 공개 — 가입 폼이 로그인 전에 호출한다 (설계 §8)."""
    return (
        db.query(University)
        .filter(University.active.is_(True))
        .order_by(University.name.asc())
        .all()
    )


@admin_router.get("", response_model=list[UniversityOut])
def list_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """끈 대학도 함께 준다 — 관리자가 다시 켤 수 있어야 한다."""
    return db.query(University).order_by(University.name.asc()).all()


@admin_router.post("", response_model=UniversityOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: UniversityIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university = University(name=payload.name)
    db.add(university)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 대학입니다"
        )
    db.refresh(university)
    return university


@admin_router.patch("/{university_id}", response_model=UniversityOut)
def set_active(
    university_id: int,
    payload: UniversityActiveUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """활성 토글만. 이름은 바꿀 수 없다 (설계 §4.1)."""
    university = _get(db, university_id)
    university.active = payload.active
    db.commit()
    db.refresh(university)
    return university


@admin_router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    university_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university = _get(db, university_id)
    if _is_referenced(db, university.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 대학입니다. 삭제 대신 비활성으로 끄세요",
        )
    db.delete(university)
    db.commit()
