from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.matching import MatchingRunOut
from app.services.matching import (
    RoundNotFound,
    RoundNotPending,
    run_matching,
)

admin_router = APIRouter(prefix="/admin/match-rounds", tags=["matching"])


@admin_router.post("/{round_id}/run", response_model=MatchingRunOut)
def run_round(
    round_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """매칭 실행. 로직은 서비스 계층에 있고 여기서는 예외만 HTTP로 옮긴다."""
    try:
        return run_matching(db, round_id)
    except RoundNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 라운드입니다",
        ) from None
    except RoundNotPending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 실행 중이거나 완료된 라운드입니다",
        ) from None
