from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.match import MatchRound, RoundStatus
from app.models.user import User
from app.schemas.round import MatchRoundOut

router = APIRouter(prefix="/match-rounds", tags=["rounds"])


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
