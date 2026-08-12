from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.match import MatchRound, RoundStatus
from app.models.user import User
from app.schemas.round import AdminMatchRoundOut, MatchRoundIn, MatchRoundOut

router = APIRouter(prefix="/match-rounds", tags=["rounds"])
admin_router = APIRouter(prefix="/admin/match-rounds", tags=["rounds"])


@router.get("/next", response_model=MatchRoundOut | None)
def get_next_round(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """다음에 실행될 매칭 라운드. 예정된 것이 없으면 null."""
    return (
        db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.pending,
            MatchRound.scheduled_at >= datetime.utcnow(),
        )
        .order_by(MatchRound.scheduled_at.asc())
        .first()
    )


def _to_naive_utc(dt: datetime) -> datetime:
    """저장 직전 정규화. 컬럼이 naive라 aware 값을 그대로 넣으면 안 된다."""
    if dt.tzinfo is None:
        return dt  # 타임존 없으면 UTC로 간주 — 프론트 규칙과 동일
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _reject_past(scheduled_at: datetime) -> None:
    if scheduled_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="예정 시각은 현재보다 미래여야 합니다",
        )


def _reject_duplicate(
    db: Session, scheduled_at: datetime, exclude_id: int | None = None
) -> None:
    query = db.query(MatchRound).filter(MatchRound.scheduled_at == scheduled_at)
    if exclude_id is not None:
        query = query.filter(MatchRound.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 시각의 라운드가 이미 있습니다",
        )


@admin_router.get("", response_model=list[AdminMatchRoundOut])
def list_rounds(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """과거·done 포함 전부. 주 1회 서비스라 필터·페이지네이션 없이 전량이다."""
    return db.query(MatchRound).order_by(MatchRound.scheduled_at.desc()).all()


@admin_router.post("", response_model=AdminMatchRoundOut, status_code=201)
def create_round(
    payload: MatchRoundIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    scheduled_at = _to_naive_utc(payload.scheduled_at)
    _reject_past(scheduled_at)
    _reject_duplicate(db, scheduled_at)
    # status는 모델 default(pending). 클라이언트 입력은 스키마에 없으므로 버려진다
    round_ = MatchRound(scheduled_at=scheduled_at)
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_
