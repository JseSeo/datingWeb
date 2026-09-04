from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.universities import validate_universities
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


def _normalize_pair(a_name, a_univ, a_year, b_name, b_univ, b_year):
    """두 사람을 순서무관하게 정규화 — (name, university) 튜플 비교로 항상 같은 순서 보장."""
    a = (a_name, a_univ, a_year)
    b = (b_name, b_univ, b_year)
    return (a, b) if a[:2] <= b[:2] else (b, a)


def _is_same_person(name_univ_a: tuple[str, str], year_a: int,
                     name_univ_b: tuple[str, str], year_b: int) -> bool:
    """이름+학교가 같아도 양쪽 다 학번이 있고 다르면 다른 사람이다 (설계 §6).

    한쪽이라도 학번이 없으면(0) 구분할 수 없으므로 안전한 방향인 동일인으로 취급한다 —
    기존 자기지목·중복지목 방어를 그대로 유지한다.
    """
    if name_univ_a != name_univ_b:
        return False
    if year_a and year_b and year_a != year_b:
        return False
    return True


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
    # 미입력(None)은 0으로 저장한다 — 유니크 제약에 NULL을 넣지 않기 위해서다 (설계 §4.2)
    a_year = payload.person_a_admission_year or 0
    b_year = payload.person_b_admission_year or 0
    me = (current_user.name.strip(), current_user.university.strip())
    me_year = current_user.admission_year or 0
    if _is_same_person(me, me_year, a, a_year) or _is_same_person(me, me_year, b, b_year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="본인은 지목 대상에 포함될 수 없습니다",
        )
    if _is_same_person(a, a_year, b, b_year):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="서로 다른 두 사람을 지목해야 합니다",
        )

    pa, pb = _normalize_pair(*a, a_year, *b, b_year)
    validate_universities(db, pa[1], pb[1])
    existing = db.query(Ojakgyo).filter(
        Ojakgyo.recommender_id == current_user.id,
        Ojakgyo.person_a_name == pa[0],
        Ojakgyo.person_a_university == pa[1],
        Ojakgyo.person_a_admission_year == pa[2],
        Ojakgyo.person_b_name == pb[0],
        Ojakgyo.person_b_university == pb[1],
        Ojakgyo.person_b_admission_year == pb[2],
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 지목한 쌍입니다",
        )

    ojakgyo = Ojakgyo(
        recommender_id=current_user.id,
        person_a_name=pa[0], person_a_university=pa[1], person_a_admission_year=pa[2],
        person_b_name=pb[0], person_b_university=pb[1], person_b_admission_year=pb[2],
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
    validate_universities(db, *[t.target_university.strip() for t in payload.targets])
    me = (current_user.name.strip(), current_user.university.strip())
    cleaned: list[tuple[str, str, int]] = []
    seen: set[tuple[str, str]] = set()
    for t in payload.targets:
        name = t.target_name.strip()
        univ = t.target_university.strip()
        # 미입력(None)은 0으로 저장한다 — 유니크 제약에 NULL을 넣지 않기 위해서다 (설계 §4.2)
        year = t.target_admission_year or 0
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
        cleaned.append((name, univ, year))

    # 목록 통째 교체: 기존 전부 삭제 후 재삽입
    db.query(RedThread).filter(RedThread.user_id == current_user.id).delete()
    db.add_all([
        RedThread(user_id=current_user.id, target_name=n, target_university=u,
                   target_admission_year=y)
        for n, u, y in cleaned
    ])
    db.commit()
    return RedThreadOut(targets=[
        RedThreadTargetOut(target_name=n, target_university=u, target_admission_year=y)
        for n, u, y in cleaned
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
