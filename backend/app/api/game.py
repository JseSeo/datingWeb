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
    RedThreadTargetOut,
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
    a = (payload.person_a_name.strip(), payload.person_a_university.strip())
    b = (payload.person_b_name.strip(), payload.person_b_university.strip())
    if not (a[0] and a[1] and b[0] and b[1]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이름과 학교를 입력해야 합니다",
        )
    me = (current_user.name.strip(), current_user.university.strip())
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
    me = (current_user.name.strip(), current_user.university.strip())
    cleaned: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for t in payload.targets:
        name = t.target_name.strip()
        univ = t.target_university.strip()
        if not name or not univ:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이름과 학교를 입력해야 합니다",
            )
        if (name, univ) == me:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="본인을 지목할 수 없습니다",
            )
        if (name, univ) in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="같은 상대를 두 번 입력할 수 없습니다",
            )
        seen.add((name, univ))
        cleaned.append((name, univ))

    # 목록 통째 교체: 기존 전부 삭제 후 재삽입
    db.query(RedThread).filter(RedThread.user_id == current_user.id).delete()
    db.add_all([
        RedThread(user_id=current_user.id, target_name=n, target_university=u)
        for n, u in cleaned
    ])
    db.commit()
    return RedThreadOut(targets=[
        RedThreadTargetOut(target_name=n, target_university=u) for n, u in cleaned
    ])


@router.get("/red-thread", response_model=RedThreadOut)
def get_red_thread(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(RedThread).filter(RedThread.user_id == current_user.id).all()
    return RedThreadOut(targets=rows)


@router.get("/red-thread/received", response_model=RedThreadReceivedOut)
def get_red_thread_received(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(RedThread).filter(
        RedThread.target_name == current_user.name.strip(),
        RedThread.target_university == current_user.university.strip(),
    ).count()
    return RedThreadReceivedOut(count=count)
