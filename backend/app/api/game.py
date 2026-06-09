from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.game import Ojakgyo, RedThread
from app.models.user import User
from app.schemas.game import (
    OjakgyoCreate,
    OjakgyoOut,
    RedThreadSubmit,
    RedThreadOut,
    RedThreadReceivedOut,
)

router = APIRouter(prefix="/game", tags=["game"])


def _normalize_pair(a_name, a_univ, b_name, b_univ):
    """두 사람을 순서무관하게 정규화 — (name, university) 튜플 비교로 항상 같은 순서 보장."""
    a = (a_name, a_univ)
    b = (b_name, b_univ)
    return (a, b) if a <= b else (b, a)


@router.post("/ojakgyo", response_model=OjakgyoOut, status_code=201)
def create_ojakgyo(
    payload: OjakgyoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pa, pb = _normalize_pair(
        payload.person_a_name, payload.person_a_university,
        payload.person_b_name, payload.person_b_university,
    )
    ojakgyo = Ojakgyo(
        recommender_id=current_user.id,
        person_a_name=pa[0], person_a_university=pa[1],
        person_b_name=pb[0], person_b_university=pb[1],
    )
    db.add(ojakgyo)
    db.commit()
    db.refresh(ojakgyo)
    return ojakgyo
