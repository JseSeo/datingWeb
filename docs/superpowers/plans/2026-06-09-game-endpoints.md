# Game Endpoints (오작교/붉은실) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 오작교(제3자 중매 지목)·붉은실(상호 지목) 게임의 저장·집계·조회 엔드포인트 구현. 확률/매칭 반영은 보류(매칭 알고리즘 영역).

**Architecture:** 기존 reports/survey 라우터 패턴 그대로 따름 — `APIRouter` + `get_current_user`/`get_db` 의존성 + Pydantic 입출력 스키마. `Ojakgyo` 모델 필드를 referral 구조에서 중매 구조로 전면 교체. 새 `app/api/game.py` 라우터 1개에 4개 엔드포인트. 매칭 확률/상호매칭 로직은 **구현 안 함** — 지목 저장·중복방지·인원 집계까지만.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (Mapped/mapped_column), Pydantic v2, pytest + TestClient (SQLite).

---

## File Structure

| 파일 | 책임 | 작업 |
|------|------|------|
| `backend/app/models/game.py` | `Ojakgyo` 필드 교체(referral→중매) + unique 제약. `RedThread` 변경 없음 | Modify |
| `backend/app/schemas/game.py` | 게임 입출력 Pydantic 스키마 5종 | Create |
| `backend/app/api/game.py` | `/game` 라우터 + 4개 엔드포인트 | Create |
| `backend/app/api/router.py` | game 라우터 등록 | Modify |
| `backend/tests/test_game.py` | 게임 엔드포인트 테스트 | Create |

`app/models/__init__.py` 는 **변경 없음** — 클래스명(`Ojakgyo`, `RedThread`) 유지되므로 re-export 그대로 유효.

**검증 규칙 요약 (스펙 §6):**
- 오작교: 본인 ∈ {person_a, person_b} → 400 / person_a == person_b → 400 / 같은 지목자·같은 쌍(순서무관) 중복 → 409. 가입 여부 검증 안 함.
- 붉은실: 1명 입력·덮어쓰기. 본인 지목 → 400. 받은 인원수는 익명 집계(count만).

**테스트 명령:** `cd backend; uv run pytest -q`

---

### Task 1: Ojakgyo 모델 교체 + 스키마 + POST /game/ojakgyo (정상 경로)

**Files:**
- Modify: `backend/app/models/game.py` (Ojakgyo 클래스 전체 교체)
- Create: `backend/app/schemas/game.py`
- Create: `backend/app/api/game.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_game.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/test_game.py` 생성

```python
from fastapi.testclient import TestClient


def _auth(client: TestClient, email="user@test.com", name="홍길동", university="서울대학교") -> dict:
    client.post("/auth/register", json={
        "email": email, "password": "password123",
        "name": name, "university": university,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_ojakgyo_create(client: TestClient):
    headers = _auth(client)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "연세대학교",
        "person_b_name": "이영희", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "created_at" in data
    # 정규화로 a/b 순서가 바뀔 수 있으므로 집합으로 검증
    assert {data["person_a_name"], data["person_b_name"]} == {"김철수", "이영희"}


def test_ojakgyo_empty_field(client: TestClient):
    headers = _auth(client, "empty@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_ojakgyo_unauthorized(client: TestClient):
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    })
    assert res.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: FAIL — `/game/ojakgyo` 라우트 없음 → 404 (201 기대 불일치)

- [ ] **Step 3: Ojakgyo 모델 필드 교체** — `backend/app/models/game.py` 전체를 아래로 교체

```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ojakgyo(Base):
    """오작교: 지목자(recommender)가 제3자로서 두 사람(이름+학교)을 지목 → 중매. 지목자 익명."""
    __tablename__ = "ojakgyo"
    __table_args__ = (
        UniqueConstraint(
            "recommender_id",
            "person_a_name", "person_a_university",
            "person_b_name", "person_b_university",
            name="uq_ojakgyo_recommender_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    person_a_name: Mapped[str] = mapped_column(String(100), nullable=False)
    person_a_university: Mapped[str] = mapped_column(String(100), nullable=False)
    person_b_name: Mapped[str] = mapped_column(String(100), nullable=False)
    person_b_university: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class RedThread(Base):
    """붉은 실: 양쪽이 서로 이름+학교 입력 시 100% 매칭 (확률 적용은 매칭 알고리즘 영역)"""
    __tablename__ = "red_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_university: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 4: 스키마 생성** — `backend/app/schemas/game.py` 생성 (5종 전부)

```python
from datetime import datetime
from pydantic import BaseModel, Field


class OjakgyoCreate(BaseModel):
    person_a_name: str = Field(min_length=1)
    person_a_university: str = Field(min_length=1)
    person_b_name: str = Field(min_length=1)
    person_b_university: str = Field(min_length=1)


class OjakgyoOut(BaseModel):
    id: int
    recommender_id: int
    person_a_name: str
    person_a_university: str
    person_b_name: str
    person_b_university: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RedThreadSubmit(BaseModel):
    target_name: str = Field(min_length=1)
    target_university: str = Field(min_length=1)


class RedThreadOut(BaseModel):
    target_name: str | None = None
    target_university: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class RedThreadReceivedOut(BaseModel):
    count: int
```

- [ ] **Step 5: 라우터 생성 (ojakgyo 정상 경로만)** — `backend/app/api/game.py` 생성

이 단계에서는 정규화 + 저장만. 가드(self/same/duplicate)는 Task 2에서 추가.

```python
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
```

- [ ] **Step 6: 라우터 등록** — `backend/app/api/router.py` 수정

```python
from fastapi import APIRouter
from app.api import auth, game, me, reports, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
router.include_router(reports.router)
router.include_router(game.router)
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: PASS (3 passed)

- [ ] **Step 8: 커밋**

```bash
git add backend/app/models/game.py backend/app/schemas/game.py backend/app/api/game.py backend/app/api/router.py backend/tests/test_game.py
git commit -m "feat(backend): 오작교 모델 중매 구조로 교체 + POST /game/ojakgyo

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 오작교 검증 가드 (self 400 / same 400 / duplicate 409)

**Files:**
- Modify: `backend/app/api/game.py:create_ojakgyo` (가드 추가)
- Test: `backend/tests/test_game.py`

- [ ] **Step 1: 실패하는 테스트 추가** — `backend/tests/test_game.py` 끝에 추가

```python
def test_ojakgyo_self_forbidden(client: TestClient):
    headers = _auth(client, "self@test.com", "나본인", "서울대학교")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "나본인", "person_a_university": "서울대학교",
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_same_pair_forbidden(client: TestClient):
    headers = _auth(client, "same@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동일", "person_a_university": "연세대학교",
        "person_b_name": "동일", "person_b_university": "연세대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_duplicate_pair_conflict(client: TestClient):
    headers = _auth(client, "dup@test.com")
    body1 = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body1, headers=headers).status_code == 201
    # 순서를 바꿔 같은 쌍 재지목 → 409
    body2 = {
        "person_a_name": "나", "person_a_university": "B대",
        "person_b_name": "가", "person_b_university": "A대",
    }
    assert client.post("/game/ojakgyo", json=body2, headers=headers).status_code == 409


def test_ojakgyo_different_recommender_same_pair_ok(client: TestClient):
    h1 = _auth(client, "rec1@test.com")
    h2 = _auth(client, "rec2@test.com")
    body = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body, headers=h1).status_code == 201
    assert client.post("/game/ojakgyo", json=body, headers=h2).status_code == 201
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: FAIL — `test_ojakgyo_self_forbidden`(201≠400), `test_ojakgyo_same_pair_forbidden`(201≠400), `test_ojakgyo_duplicate_pair_conflict`(중복이 500/IntegrityError 또는 201)

- [ ] **Step 3: 가드 추가** — `backend/app/api/game.py` 의 `create_ojakgyo` 를 아래로 교체

```python
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
        raise HTTPException(status_code=400, detail="본인은 지목 대상에 포함될 수 없습니다")
    if a == b:
        raise HTTPException(status_code=400, detail="서로 다른 두 사람을 지목해야 합니다")

    pa, pb = _normalize_pair(*a, *b)
    existing = db.query(Ojakgyo).filter(
        Ojakgyo.recommender_id == current_user.id,
        Ojakgyo.person_a_name == pa[0],
        Ojakgyo.person_a_university == pa[1],
        Ojakgyo.person_b_name == pb[0],
        Ojakgyo.person_b_university == pb[1],
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 지목한 쌍입니다")

    ojakgyo = Ojakgyo(
        recommender_id=current_user.id,
        person_a_name=pa[0], person_a_university=pa[1],
        person_b_name=pb[0], person_b_university=pb[1],
    )
    db.add(ojakgyo)
    db.commit()
    db.refresh(ojakgyo)
    return ojakgyo
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/game.py backend/tests/test_game.py
git commit -m "feat(backend): 오작교 지목 검증 가드 (본인/동일쌍 400, 중복 409)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 붉은실 입력/조회 (POST + GET /game/red-thread)

**Files:**
- Modify: `backend/app/api/game.py` (엔드포인트 2개 추가)
- Test: `backend/tests/test_game.py`

- [ ] **Step 1: 실패하는 테스트 추가** — `backend/tests/test_game.py` 끝에 추가

```python
def test_red_thread_create(client: TestClient):
    headers = _auth(client, "rt@test.com")
    res = client.post("/game/red-thread", json={
        "target_name": "상대", "target_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["target_name"] == "상대"


def test_red_thread_overwrite(client: TestClient):
    headers = _auth(client, "rt2@test.com")
    client.post("/game/red-thread", json={
        "target_name": "첫", "target_university": "A대",
    }, headers=headers)
    res = client.post("/game/red-thread", json={
        "target_name": "둘째", "target_university": "B대",
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["target_name"] == "둘째"
    got = client.get("/game/red-thread", headers=headers)
    assert got.json()["target_name"] == "둘째"
    assert got.json()["target_university"] == "B대"


def test_red_thread_self_forbidden(client: TestClient):
    headers = _auth(client, "rtself@test.com", "본인", "서울대학교")
    res = client.post("/game/red-thread", json={
        "target_name": "본인", "target_university": "서울대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_red_thread_get_empty(client: TestClient):
    headers = _auth(client, "rtempty@test.com")
    res = client.get("/game/red-thread", headers=headers)
    assert res.status_code == 200
    assert res.json()["target_name"] is None


def test_red_thread_unauthorized(client: TestClient):
    res = client.post("/game/red-thread", json={
        "target_name": "x", "target_university": "y",
    })
    assert res.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: FAIL — `/game/red-thread` 라우트 없음 → 404/405

- [ ] **Step 3: 엔드포인트 2개 추가** — `backend/app/api/game.py` 끝(파일 마지막)에 추가

```python
@router.post("/red-thread", response_model=RedThreadOut)
def submit_red_thread(
    payload: RedThreadSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = (payload.target_name, payload.target_university)
    if target == (current_user.name, current_user.university):
        raise HTTPException(status_code=400, detail="본인을 지목할 수 없습니다")

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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/game.py backend/tests/test_game.py
git commit -m "feat(backend): 붉은실 입력/조회 (POST·GET /game/red-thread, 덮어쓰기·본인지목 400)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 붉은실 받은 인원수 집계 (GET /game/red-thread/received)

**Files:**
- Modify: `backend/app/api/game.py` (엔드포인트 1개 추가)
- Test: `backend/tests/test_game.py`

- [ ] **Step 1: 실패하는 테스트 추가** — `backend/tests/test_game.py` 끝에 추가

```python
def test_red_thread_received_count(client: TestClient):
    # 대상 유저(타깃) — 이름+학교로 지목당함
    hb = _auth(client, "target@test.com", "타깃", "성균관대학교")
    # 두 명이 타깃을 붉은실로 지목
    h1 = _auth(client, "p1@test.com")
    h2 = _auth(client, "p2@test.com")
    body = {"target_name": "타깃", "target_university": "성균관대학교"}
    client.post("/game/red-thread", json=body, headers=h1)
    client.post("/game/red-thread", json=body, headers=h2)

    res = client.get("/game/red-thread/received", headers=hb)
    assert res.status_code == 200
    assert res.json()["count"] == 2


def test_red_thread_received_zero(client: TestClient):
    headers = _auth(client, "nobody@test.com")
    res = client.get("/game/red-thread/received", headers=headers)
    assert res.status_code == 200
    assert res.json()["count"] == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: FAIL — `/game/red-thread/received` 라우트 없음 → 404

- [ ] **Step 3: 엔드포인트 추가** — `backend/app/api/game.py` 끝에 추가

```python
@router.get("/red-thread/received", response_model=RedThreadReceivedOut)
def get_red_thread_received(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(RedThread).filter(
        RedThread.target_name == current_user.name,
        RedThread.target_university == current_user.university,
    ).count()
    return RedThreadReceivedOut(count=count)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_game.py -q`
Expected: PASS (14 passed)

- [ ] **Step 5: 전체 회귀 테스트**

Run: `cd backend; uv run pytest -q`
Expected: PASS — 기존 33개 + 신규 14개 = 47 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/game.py backend/tests/test_game.py
git commit -m "feat(backend): 붉은실 받은 인원수 집계 (GET /game/red-thread/received, 익명)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 보류/제외 (이 plan 밖)

- 매칭 확률 반영(+33%, 3명 100%), 상호매칭 100% 보장 → 매칭 알고리즘 영역. CLAUDE.md 금지.
- 카카오 알림톡 푸시 → 사업자등록 전 금지. "받은 인원수"는 인앱 조회(count)로만 제공.
- Alembic 마이그레이션 → PostgreSQL 환경 보류 상태(PROGRESS.md). 테스트는 SQLite `create_all`로 신규 스키마 자동 반영.
- 지목 대상 가입 여부 검증 안 함 (스펙 §6.1 — 이름+학교 텍스트로만 저장).

## 완료 후

- PROGRESS.md 의 game 항목 ✅ 갱신, 미구현 엔드포인트 목록에서 4개 제거.
- `finishing-a-development-branch` 로 마무리 옵션 검토.
