from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.match import MatchRound, RoundStatus
from app.models.user import User
from app.schemas.round import AdminMatchRoundOut, MatchRoundIn, MatchRoundOut

router = APIRouter(prefix="/match-rounds", tags=["rounds"])
admin_router = APIRouter(prefix="/admin/match-rounds", tags=["rounds"])

# 되돌리기 유예. 엔진이 지원하는 최대 풀(정밀도 한계 약 4,100명)에서 측정한
# run_matching 전 구간 최장 실행이 131초라 2배 이상 여유를 둔다
RUNNING_GRACE = timedelta(minutes=5)


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


def _commit_or_conflict(db: Session) -> None:
    """`scheduled_at` 유니크 제약 위반을 409로. _reject_duplicate가 통과한 뒤
    다른 요청이 먼저 커밋한 경우(TOCTOU)에만 도달한다."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 시각의 라운드가 이미 있습니다",
        ) from None


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
    _commit_or_conflict(db)
    db.refresh(round_)
    return round_


def _get_editable_round(db: Session, round_id: int, action: str) -> MatchRound:
    """404 → 상태 잠금 순으로 판정.

    pending만 손댈 수 있다. done은 실행이 만든 상태라 손대지 않고,
    running은 _execute가 도는 중이라 건드리면 매칭 결과가 없는 라운드를 참조한다.
    """
    round_ = db.get(MatchRound, round_id)
    if round_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 라운드입니다",
        )
    if round_.status == RoundStatus.done:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"완료된 라운드는 {action}할 수 없습니다",
        )
    if round_.status == RoundStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"실행 중인 라운드는 {action}할 수 없습니다",
        )
    return round_


@admin_router.put("/{round_id}", response_model=AdminMatchRoundOut)
def update_round(
    round_id: int,
    payload: MatchRoundIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    round_ = _get_editable_round(db, round_id, "수정")
    scheduled_at = _to_naive_utc(payload.scheduled_at)
    _reject_past(scheduled_at)
    _reject_duplicate(db, scheduled_at, exclude_id=round_id)
    round_.scheduled_at = scheduled_at
    _commit_or_conflict(db)
    db.refresh(round_)
    return round_


@admin_router.delete("/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_round(
    round_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    # 시각 규칙은 적용하지 않는다 — 지나간 pending 라운드도 지울 수 있어야 한다
    round_ = _get_editable_round(db, round_id, "삭제")
    db.delete(round_)
    db.commit()


@admin_router.post("/{round_id}/reset", response_model=AdminMatchRoundOut)
def reset_round(
    round_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """서버가 죽어 running에 멈춘 라운드를 pending으로 되돌린다.

    살아서 도는 라운드를 되돌리면 이중 실행이 난다. 프록시 타임아웃(30~60초)이
    실행(4,000명 실측 131초)보다 짧아 관리자 화면엔 실패로 보이면서 서버는 계속
    도는 경우가 있으므로, 선점 후 RUNNING_GRACE가 지나기 전에는 거부한다.
    """
    round_ = db.get(MatchRound, round_id)
    if round_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 라운드입니다",
        )
    if round_.status != RoundStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="실행 중인 라운드만 되돌릴 수 있습니다",
        )
    # started_at이 없으면 추적 이전에 멈춘 행이다 — 확실히 오래됐으므로 유예를 적용하지 않는다
    if round_.started_at is not None:
        elapsed = datetime.utcnow() - round_.started_at
        if elapsed < RUNNING_GRACE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"실행을 시작한 지 {int(elapsed.total_seconds() // 60)}분밖에 "
                    "지나지 않았습니다. 아직 실행 중일 수 있어요"
                ),
            )
    round_.status = RoundStatus.pending
    db.commit()
    db.refresh(round_)
    return round_
