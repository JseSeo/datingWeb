from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.match import MatchingUniversityWeight
from app.models.user import User
from app.schemas.university_weight import UniversityWeightIn, UniversityWeightOut
from app.services.matching import university_pair_key

admin_router = APIRouter(
    prefix="/admin/university-weights", tags=["university-weights"]
)


def _normalized(payload: UniversityWeightIn) -> tuple[str, str]:
    """저장 직전 정규화. 쌍은 사전순으로 눕혀야 유니크가 순서 바뀐 중복을 잡는다 (설계 §4.2)."""
    a = payload.university_a.strip()
    b = payload.university_b.strip()
    if not a:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="대학명을 입력하세요"
        )
    if b == "":
        return a, ""
    return university_pair_key(a, b)


def _get_weight(db: Session, weight_id: int) -> MatchingUniversityWeight:
    weight = db.get(MatchingUniversityWeight, weight_id)
    if weight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 규칙입니다"
        )
    return weight


def _commit_or_conflict(db: Session) -> None:
    """유니크 위반을 409로 바꾼다 — 같은 대학·같은 쌍의 규칙은 하나뿐이다."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 규칙입니다"
        )


@admin_router.get("", response_model=list[UniversityWeightOut])
def list_weights(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """끈 규칙도 함께 준다 — 관리자가 다시 켤 수 있어야 한다."""
    return (
        db.query(MatchingUniversityWeight)
        .order_by(MatchingUniversityWeight.id.asc())
        .all()
    )


@admin_router.post("", response_model=UniversityWeightOut, status_code=status.HTTP_201_CREATED)
def create_weight(
    payload: UniversityWeightIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university_a, university_b = _normalized(payload)
    weight = MatchingUniversityWeight(
        university_a=university_a,
        university_b=university_b,
        bonus=payload.bonus,
        active=payload.active,
        note=payload.note,
    )
    db.add(weight)
    _commit_or_conflict(db)
    db.refresh(weight)
    return weight


@admin_router.put("/{weight_id}", response_model=UniversityWeightOut)
def update_weight(
    weight_id: int,
    payload: UniversityWeightIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    weight = _get_weight(db, weight_id)
    weight.university_a, weight.university_b = _normalized(payload)
    weight.bonus = payload.bonus
    weight.active = payload.active
    weight.note = payload.note
    _commit_or_conflict(db)
    db.refresh(weight)
    return weight


@admin_router.delete("/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    weight = _get_weight(db, weight_id)
    db.delete(weight)
    db.commit()
