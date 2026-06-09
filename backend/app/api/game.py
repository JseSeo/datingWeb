from fastapi import APIRouter, Depends, HTTPException, status
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
    a = (payload.person_a_name, payload.person_a_university)
    b = (payload.person_b_name, payload.person_b_university)
    me = (current_user.name, current_user.university)
    if me == a or me == b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인은 지목 대상에 포함될 수 없습니다",
        )
    if a == b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="서로 다른 두 사람을 지목해야 합니다",
        )

    pa, pb = _normalize_pair(*a, *b)
    existing = db.query(Ojakgyo).filter(
        Ojakgyo.recommender_id == current_user.id,
        Ojakgyo.person_a_name == pa[0],
        Ojakgyo.person_a_university == pa[1],
        Ojakgyo.person_b_name == pb[0],
        Ojakgyo.person_b_university == pb[1],
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 지목한 쌍입니다",
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


@router.post("/red-thread", response_model=RedThreadOut)
def submit_red_thread(
    payload: RedThreadSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = (payload.target_name, payload.target_university)
    if target == (current_user.name, current_user.university):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인을 지목할 수 없습니다",
        )

    rt = db.query(RedThread).filter(RedThread.user_id == current_user.id).first()
    if rt:
        rt.target_name = payload.target_name
        rt.target_university = payload.target_university
    else:
        rt = RedThread(
            user_id=current_user.id,
            target_name=payload.target_name,
            target_university=payload.target_university,
        )
        db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.get("/red-thread", response_model=RedThreadOut)
def get_red_thread(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rt = db.query(RedThread).filter(RedThread.user_id == current_user.id).first()
    if rt is None:
        return RedThreadOut()
    return rt
