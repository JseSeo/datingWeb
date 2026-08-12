# 라운드 관리 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자가 `/admin`에서 매칭 라운드를 생성·수정·삭제할 수 있게 한다.

**Architecture:** 기존 `rounds.py`에 `require_admin`으로 보호되는 `admin_router`를 추가해 `/admin/match-rounds` CRUD를 제공한다(`reports.py`의 `router` + `admin_router` 구성과 동일). 프론트는 `/admin`에 "라운드" 탭을 추가하고, KST 입력을 UTC ISO로 바꿔 보낸다. 타임존 변환 지식은 프론트에만 두고, 백엔드는 들어온 값을 UTC-naive로 정규화해 저장한다.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Pydantic v2 · pytest / React 19 · Vite · Vitest · Testing Library

**스펙:** `docs/superpowers/specs/2026-08-12-round-management-design.md`

## Global Constraints

- `match_rounds.scheduled_at`은 **항상 UTC-naive**로 저장한다. aware datetime을 그대로 넣으면 SQLite에 offset 문자열이 박혀 `datetime.utcnow()` 비교가 조용히 깨진다
- `status` / `executed_at`은 **읽기 전용**이다. 생성 시 `status`는 모델 default(`pending`), `executed_at`은 어느 경로에서도 읽지도 쓰지도 않는다
- 라운드 **실행**(Match 생성)은 이 계획의 범위 밖이다 — `CLAUDE.md` 금지 항목
- 기존 `MatchRoundOut`(`id`, `scheduled_at`)과 `backend/tests/test_rounds.py`는 **수정하지 않는다**. 유저 응답 경계 고정 테스트다
- 모델 변경·alembic 마이그레이션 없음
- 검증은 백엔드에만 둔다. 프론트는 서버 `detail`을 그대로 표시한다
- 에러 문구는 아래 값을 **글자 그대로** 쓴다:
  - `예정 시각은 현재보다 미래여야 합니다` (400)
  - `같은 시각의 라운드가 이미 있습니다` (409)
  - `존재하지 않는 라운드입니다` (404)
  - `완료된 라운드는 수정할 수 없습니다` / `완료된 라운드는 삭제할 수 없습니다` (409)
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- PowerShell 5.1에서 한국어 여러 줄 커밋 메시지는 `git commit -m`에 직접 넣지 말고 파일에 써서 `git commit -F <파일>`로 넣는다

## File Structure

| 파일 | 책임 | 상태 |
|------|------|------|
| `backend/app/schemas/round.py` | 라운드 입출력 스키마 3종 | 수정 (기존 `MatchRoundOut` 유지) |
| `backend/app/api/rounds.py` | 공개 조회 + 관리자 CRUD 엔드포인트 | 수정 (29줄 → 약 120줄) |
| `backend/app/api/router.py` | 라우터 등록 | 수정 (1줄 추가) |
| `backend/tests/test_admin_rounds.py` | 관리자 CRUD 테스트 | 신규 |
| `frontend/vite.config.ts` | 테스트 타임존 고정 | 수정 (1줄 추가) |
| `frontend/src/lib/datetime.ts` | KST ↔ UTC 변환 | 수정 (함수 2개 추가) |
| `frontend/src/lib/datetime.test.ts` | 변환 단위 테스트 | 수정 |
| `frontend/src/lib/types.ts` | `AdminMatchRoundOut` | 수정 |
| `frontend/src/lib/api.ts` | 라운드 CRUD 클라이언트 4함수 | 수정 |
| `frontend/src/pages/Admin/RoundTab.tsx` | 라운드 탭 화면 | 신규 |
| `frontend/src/pages/Admin/RoundTab.test.tsx` | 라운드 탭 테스트 | 신규 |
| `frontend/src/pages/Admin/Admin.module.css` | 생성 폼 스타일 | 수정 (클래스 2개 추가) |
| `frontend/src/pages/Admin/Admin.tsx` | 탭 3개 구성 | 수정 |
| `frontend/src/pages/Admin/Admin.test.tsx` | 탭 통합 테스트 | 수정 |

---

### Task 1: 백엔드 — 스키마 · 목록 · 생성

**Files:**
- Modify: `backend/app/schemas/round.py`
- Modify: `backend/app/api/rounds.py`
- Modify: `backend/app/api/router.py:11`
- Test: `backend/tests/test_admin_rounds.py` (신규)

**Interfaces:**
- Consumes: `require_admin` (`app.core.deps`), `get_db` (`app.database`), `MatchRound` / `RoundStatus` (`app.models.match`), `admin_client` fixture (`tests/conftest.py:41`)
- Produces:
  - `MatchRoundIn(scheduled_at: datetime)` — 생성·수정 공용 입력 스키마
  - `AdminMatchRoundOut(id: int, scheduled_at: datetime, status: RoundStatus)`
  - `_to_naive_utc(dt: datetime) -> datetime`
  - `_reject_past(scheduled_at: datetime) -> None`
  - `_reject_duplicate(db: Session, scheduled_at: datetime, exclude_id: int | None = None) -> None`
  - `admin_router` — prefix `/admin/match-rounds`, `GET ""` / `POST ""`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_admin_rounds.py` 신규:

```python
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from tests.conftest import TestingSessionLocal


def _add_rounds(*rounds: MatchRound) -> list[int]:
    db = TestingSessionLocal()
    db.add_all(rounds)
    db.commit()
    ids = [r.id for r in rounds]
    db.close()
    return ids


def _hours(n: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=n)


def _iso(n: int) -> str:
    """n시간 뒤를 타임존 없는 ISO 문자열로. 마이크로초는 버린다."""
    return _hours(n).replace(microsecond=0).isoformat()


def _register_normal_user(client: TestClient) -> dict:
    client.post("/auth/register", json={
        "email": "normal@test.com",
        "password": "password123",
        "name": "김일반",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={
        "email": "normal@test.com",
        "password": "password123",
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_list_returns_all_rounds_newest_first(admin_client: TestClient):
    _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(72), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(-48), status=RoundStatus.done),
    )
    res = admin_client.get("/admin/match-rounds")
    assert res.status_code == 200
    data = res.json()
    # 과거·done 포함 전부, scheduled_at 내림차순
    assert len(data) == 3
    assert [r["scheduled_at"] for r in data] == sorted(
        [r["scheduled_at"] for r in data], reverse=True
    )
    assert set(data[0].keys()) == {"id", "scheduled_at", "status"}


def test_create_returns_201_with_pending_status(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": _iso(24)})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert body["id"] > 0


def test_create_ignores_client_supplied_status(admin_client: TestClient):
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": _iso(24), "status": "done"},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_create_stores_aware_input_as_naive_utc(admin_client: TestClient):
    # 프론트가 toISOString()으로 보내는 형태
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": "2030-01-01T12:00:00.000Z"},
    )
    assert res.status_code == 201
    db = TestingSessionLocal()
    row = db.query(MatchRound).first()
    stored = row.scheduled_at
    db.close()
    assert stored.tzinfo is None
    assert stored == datetime(2030, 1, 1, 12, 0)


def test_create_converts_offset_input_to_utc(admin_client: TestClient):
    # KST 21:00 = UTC 12:00
    res = admin_client.post(
        "/admin/match-rounds",
        json={"scheduled_at": "2030-01-01T21:00:00+09:00"},
    )
    assert res.status_code == 201
    db = TestingSessionLocal()
    stored = db.query(MatchRound).first().scheduled_at
    db.close()
    assert stored == datetime(2030, 1, 1, 12, 0)


def test_create_rejects_past(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": _iso(-1)})
    assert res.status_code == 400
    assert res.json()["detail"] == "예정 시각은 현재보다 미래여야 합니다"


def test_create_rejects_duplicate(admin_client: TestClient):
    when = _iso(24)
    assert admin_client.post(
        "/admin/match-rounds", json={"scheduled_at": when}
    ).status_code == 201
    res = admin_client.post("/admin/match-rounds", json={"scheduled_at": when})
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def test_list_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    res = client.get("/admin/match-rounds", headers=headers)
    assert res.status_code == 403


def test_create_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    res = client.post(
        "/admin/match-rounds",
        json={"scheduled_at": _iso(24)},
        headers=headers,
    )
    assert res.status_code == 403


def test_requires_auth(client: TestClient):
    assert client.get("/admin/match-rounds").status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_admin_rounds.py -v`
Expected: FAIL — 전 케이스 404 (엔드포인트 없음)

- [ ] **Step 3: 스키마 추가**

`backend/app/schemas/round.py` 전체를 아래로 교체:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import RoundStatus


class MatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchRoundIn(BaseModel):
    """생성·수정 공용. 편집 가능한 필드는 scheduled_at 하나뿐이다."""

    scheduled_at: datetime


class AdminMatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime
    status: RoundStatus

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: 관리자 라우터 — 목록 · 생성 구현**

`backend/app/api/rounds.py`의 import와 상단을 아래로 교체(기존 `get_next_round`는 그대로 둔다):

```python
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
```

파일 끝에 추가:

```python
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
```

- [ ] **Step 5: 라우터 등록**

`backend/app/api/router.py`의 마지막 줄 아래에 추가:

```python
router.include_router(rounds.admin_router)
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_admin_rounds.py -v`
Expected: PASS — 10 passed

- [ ] **Step 7: 기존 테스트 회귀 확인**

Run: `cd backend && uv run pytest`
Expected: PASS — 기존 113 + 신규 10 = 123 passed. `test_rounds.py`의 경계 테스트가 그대로 통과해야 한다

- [ ] **Step 8: 커밋**

```bash
git add backend/app/schemas/round.py backend/app/api/rounds.py backend/app/api/router.py backend/tests/test_admin_rounds.py
git commit -F <메시지파일>
```

메시지:

```
feat(backend): 관리자 라운드 목록·생성 엔드포인트

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 2: 백엔드 — 수정 · 삭제

**Files:**
- Modify: `backend/app/api/rounds.py`
- Test: `backend/tests/test_admin_rounds.py`

**Interfaces:**
- Consumes: Task 1의 `MatchRoundIn`, `AdminMatchRoundOut`, `_to_naive_utc`, `_reject_past`, `_reject_duplicate`, `admin_router`
- Produces:
  - `_get_editable_round(db: Session, round_id: int, action: str) -> MatchRound` — 404 / done 잠금 판정
  - `PUT /admin/match-rounds/{round_id}` → 200 `AdminMatchRoundOut`
  - `DELETE /admin/match-rounds/{round_id}` → 204

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_admin_rounds.py` 파일 끝에 추가:

```python
def test_update_changes_scheduled_at(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    new_when = _iso(48)
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": new_when}
    )
    assert res.status_code == 200
    assert res.json()["id"] == round_id
    assert res.json()["scheduled_at"].startswith(new_when[:16])


def test_update_allows_moving_a_past_pending_round_to_future(admin_client: TestClient):
    """관리자가 실행하지 못하고 지나간 라운드를 다음 주로 옮기는 정상 경로."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(48)}
    )
    assert res.status_code == 200


def test_update_rejects_past(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(-1)}
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "예정 시각은 현재보다 미래여야 합니다"


def test_update_rejects_duplicate_of_another_round(admin_client: TestClient):
    taken = _hours(72).replace(microsecond=0)
    ids = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending),
        MatchRound(scheduled_at=taken, status=RoundStatus.pending),
    )
    res = admin_client.put(
        f"/admin/match-rounds/{ids[0]}", json={"scheduled_at": taken.isoformat()}
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "같은 시각의 라운드가 이미 있습니다"


def test_update_to_its_own_current_time_is_allowed(admin_client: TestClient):
    """자기 자신은 중복 판정에서 제외한다."""
    when = _hours(24).replace(microsecond=0)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=when, status=RoundStatus.pending)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": when.isoformat()}
    )
    assert res.status_code == 200


def test_update_rejects_done_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.done)
    )
    res = admin_client.put(
        f"/admin/match-rounds/{round_id}", json={"scheduled_at": _iso(48)}
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "완료된 라운드는 수정할 수 없습니다"


def test_update_missing_round_returns_404(admin_client: TestClient):
    res = admin_client.put(
        "/admin/match-rounds/9999", json={"scheduled_at": _iso(24)}
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "존재하지 않는 라운드입니다"


def test_delete_removes_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    assert admin_client.delete(f"/admin/match-rounds/{round_id}").status_code == 204
    assert admin_client.get("/admin/match-rounds").json() == []


def test_delete_allows_past_pending_round(admin_client: TestClient):
    """지나간 pending 라운드도 지울 수 있어야 한다 — 삭제엔 시각 규칙을 걸지 않는다."""
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.pending)
    )
    assert admin_client.delete(f"/admin/match-rounds/{round_id}").status_code == 204


def test_delete_rejects_done_round(admin_client: TestClient):
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(-24), status=RoundStatus.done)
    )
    res = admin_client.delete(f"/admin/match-rounds/{round_id}")
    assert res.status_code == 409
    assert res.json()["detail"] == "완료된 라운드는 삭제할 수 없습니다"


def test_delete_missing_round_returns_404(admin_client: TestClient):
    res = admin_client.delete("/admin/match-rounds/9999")
    assert res.status_code == 404


def test_update_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = client.put(
        f"/admin/match-rounds/{round_id}",
        json={"scheduled_at": _iso(48)},
        headers=headers,
    )
    assert res.status_code == 403


def test_delete_rejects_non_admin(client: TestClient):
    headers = _register_normal_user(client)
    [round_id] = _add_rounds(
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending)
    )
    res = client.delete(f"/admin/match-rounds/{round_id}", headers=headers)
    assert res.status_code == 403
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_admin_rounds.py -v -k "update or delete"`
Expected: FAIL — 405 Method Not Allowed 또는 404

- [ ] **Step 3: 수정 · 삭제 구현**

`backend/app/api/rounds.py` 파일 끝에 추가:

```python
def _get_editable_round(db: Session, round_id: int, action: str) -> MatchRound:
    """404 → done 잠금 순으로 판정. done은 실행이 만든 상태라 손대지 않는다."""
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
    db.commit()
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_admin_rounds.py -v`
Expected: PASS — 23 passed

- [ ] **Step 5: 전체 백엔드 회귀 확인**

Run: `cd backend && uv run pytest`
Expected: PASS — 136 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/rounds.py backend/tests/test_admin_rounds.py
git commit -F <메시지파일>
```

메시지:

```
feat(backend): 관리자 라운드 수정·삭제 엔드포인트

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 3: 프론트 — KST ↔ UTC 변환 유틸

**Files:**
- Modify: `frontend/vite.config.ts:7-11`
- Modify: `frontend/src/lib/datetime.ts`
- Test: `frontend/src/lib/datetime.test.ts`

**Interfaces:**
- Consumes: 기존 `formatKST(iso: string): string` (`datetime.ts:16`)
- Produces:
  - `kstInputToUtcISO(local: string): string | null`
  - `utcISOToKstInput(iso: string): string`

- [ ] **Step 1: 테스트 타임존 고정**

`frontend/vite.config.ts`의 `test` 블록에 `env`를 추가한다:

```ts
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    env: { TZ: "UTC" },
  },
```

이유: `kstInputToUtcISO`의 핵심 버그는 "브라우저 로컬 타임존으로 파싱해버리는 것"인데, 개발 머신이 KST라 로컬 파싱과 KST 파싱이 우연히 같은 값을 낸다. 테스트를 UTC에서 돌려야 그 버그가 드러난다.

- [ ] **Step 2: 실패하는 테스트 작성**

`frontend/src/lib/datetime.test.ts`의 import를 바꾸고 파일 끝에 describe 2개를 추가:

```ts
import { formatKST, daysUntilKST, kstInputToUtcISO, utcISOToKstInput } from "./datetime";
```

```ts
describe("kstInputToUtcISO", () => {
  it("KST 21:00 입력을 UTC 12:00으로 변환", () => {
    // 이 테스트는 TZ=UTC에서 돈다. 로컬 파싱 구현이면 21:00Z가 나와 실패한다
    expect(kstInputToUtcISO("2026-08-20T21:00")).toBe("2026-08-20T12:00:00.000Z");
  });

  it("초가 포함된 형식도 같은 결과", () => {
    expect(kstInputToUtcISO("2026-08-20T21:00:00")).toBe("2026-08-20T12:00:00.000Z");
  });

  it("KST 오전 8시는 전날 UTC 23시", () => {
    expect(kstInputToUtcISO("2026-08-20T08:00")).toBe("2026-08-19T23:00:00.000Z");
  });

  it("빈 문자열은 null", () => {
    expect(kstInputToUtcISO("")).toBeNull();
  });

  it("형식이 다른 입력은 null", () => {
    expect(kstInputToUtcISO("2026-08-20 21:00")).toBeNull();
  });

  it("형식은 맞지만 존재하지 않는 날짜는 null", () => {
    expect(kstInputToUtcISO("2026-13-45T21:00")).toBeNull();
  });
});

describe("utcISOToKstInput", () => {
  it("UTC ISO를 datetime-local 값으로", () => {
    expect(utcISOToKstInput("2026-08-20T12:00:00.000Z")).toBe("2026-08-20T21:00");
  });

  it("타임존 표시 없는 값도 UTC로 간주", () => {
    expect(utcISOToKstInput("2026-08-20T12:00:00")).toBe("2026-08-20T21:00");
  });

  it("분 단위 입력은 왕복해도 같다", () => {
    const input = "2026-08-20T21:00";
    expect(utcISOToKstInput(kstInputToUtcISO(input)!)).toBe(input);
  });
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: FAIL — `kstInputToUtcISO is not a function`

- [ ] **Step 4: 변환 함수 구현**

`frontend/src/lib/datetime.ts` 파일 끝에 추가:

```ts
// KST는 서머타임이 없어 고정 +09:00이다.
const KST_OFFSET = "+09:00";
const MINUTE_FORM = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
const SECOND_FORM = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;

/**
 * datetime-local 값(KST로 해석)을 UTC ISO 문자열로. 잘못된 값이면 null.
 * 오프셋을 명시해 파싱한다 — 접미사 없이 파싱하면 브라우저 로컬 시각이 되어
 * KST가 아닌 환경에서 조용히 틀린다. 브라우저마다 초 유무가 달라 둘 다 받는다.
 */
export function kstInputToUtcISO(local: string): string | null {
  let value: string;
  if (MINUTE_FORM.test(local)) value = `${local}:00`;
  else if (SECOND_FORM.test(local)) value = local;
  else return null;

  const date = new Date(`${value}${KST_OFFSET}`);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

/** UTC ISO를 datetime-local 초기값("YYYY-MM-DDTHH:mm")으로. */
export function utcISOToKstInput(iso: string): string {
  return formatKST(iso).replace(" ", "T");
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: PASS — 19 passed

- [ ] **Step 6: 타임존 변경이 기존 테스트를 깨지 않았는지 확인**

Run: `cd frontend && npm test`
Expected: PASS — 기존 130 + 신규 9 = 139 passed. 하나라도 깨지면 `TZ: "UTC"` 때문인지 먼저 확인한다(기존 코드는 `Intl`에 `timeZone: "Asia/Seoul"`을 명시하므로 영향이 없어야 한다)

- [ ] **Step 7: 커밋**

```bash
git add frontend/vite.config.ts frontend/src/lib/datetime.ts frontend/src/lib/datetime.test.ts
git commit -F <메시지파일>
```

메시지:

```
feat(frontend): KST 입력 ↔ UTC ISO 변환 유틸

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 4: 프론트 — 라운드 탭

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/Admin/RoundTab.tsx`
- Modify: `frontend/src/pages/Admin/Admin.module.css`
- Test: `frontend/src/pages/Admin/RoundTab.test.tsx` (신규)

**Interfaces:**
- Consumes: Task 3의 `kstInputToUtcISO` / `utcISOToKstInput`, 기존 `formatKST`, `ApiError` (`lib/api.ts:23`), `Button` (`components/Button/Button.tsx`), `styles` (`Admin.module.css`)
- Produces:
  - `AdminMatchRoundOut { id: number; scheduled_at: string; status: "pending" | "done" }`
  - `listMatchRounds(): Promise<AdminMatchRoundOut[]>`
  - `createMatchRound(scheduledAtUtcISO: string): Promise<AdminMatchRoundOut>`
  - `updateMatchRound(id: number, scheduledAtUtcISO: string): Promise<AdminMatchRoundOut>`
  - `deleteMatchRound(id: number): Promise<void>`
  - `RoundTab` — default export 컴포넌트

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/pages/Admin/RoundTab.test.tsx` 신규:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RoundTab from "./RoundTab";
import * as api from "../../lib/api";
import { ApiError } from "../../lib/api";
import type { AdminMatchRoundOut } from "../../lib/types";

const pending: AdminMatchRoundOut = {
  id: 1,
  scheduled_at: "2026-08-20T12:00:00",  // KST 21:00
  status: "pending",
};

const done: AdminMatchRoundOut = {
  id: 2,
  scheduled_at: "2026-08-06T12:00:00",
  status: "done",
};

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("RoundTab", () => {
  it("목록을 KST로 표시하고 상태 배지를 붙인다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending, done]);
    render(<RoundTab />);
    await waitFor(() =>
      expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument(),
    );
    expect(screen.getByText("2026-08-06 21:00")).toBeInTheDocument();
    expect(screen.getByText("예정")).toBeInTheDocument();
    expect(screen.getByText("완료")).toBeInTheDocument();
  });

  it("done 라운드에는 수정·삭제 버튼이 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending, done]);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-06 21:00"));
    // pending 한 건에 대해서만 버튼이 있다
    expect(screen.getAllByRole("button", { name: "수정" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "삭제" })).toHaveLength(1);
  });

  it("생성 — KST 입력을 UTC ISO로 바꿔 보내고 목록에 반영", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
    const created: AdminMatchRoundOut = {
      id: 3,
      scheduled_at: "2026-09-01T12:00:00",
      status: "pending",
    };
    const spy = vi.spyOn(api, "createMatchRound").mockResolvedValue(created);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("예정된 라운드 없음"));

    fireEvent.change(screen.getByLabelText("매칭 예정 일시"), {
      target: { value: "2026-09-01T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(screen.getByText("2026-09-01 21:00")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith("2026-09-01T12:00:00.000Z");
  });

  it("생성 실패 시 서버 문구를 그대로 표시하고 목록은 그대로", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
    vi.spyOn(api, "createMatchRound").mockRejectedValue(
      new ApiError(409, "같은 시각의 라운드가 이미 있습니다"),
    );
    render(<RoundTab />);
    await waitFor(() => screen.getByText("예정된 라운드 없음"));

    fireEvent.change(screen.getByLabelText("매칭 예정 일시"), {
      target: { value: "2026-09-01T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(
        screen.getByText("같은 시각의 라운드가 이미 있습니다"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("예정된 라운드 없음")).toBeInTheDocument();
  });

  it("빈 입력으로 추가하면 요청을 보내지 않는다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
    const spy = vi.spyOn(api, "createMatchRound");
    render(<RoundTab />);
    await waitFor(() => screen.getByText("예정된 라운드 없음"));

    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(screen.getByText("올바른 일시를 입력하세요.")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("수정 — 기존 값이 입력칸에 채워지고 저장하면 목록이 갱신된다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "updateMatchRound").mockResolvedValue({
      ...pending,
      scheduled_at: "2026-08-13T12:00:00",
    });
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "수정" }));
    const input = screen.getByLabelText("매칭 예정 일시 수정");
    expect(input).toHaveValue("2026-08-20T21:00");

    fireEvent.change(input, { target: { value: "2026-08-13T21:00" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() =>
      expect(screen.getByText("2026-08-13 21:00")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith(1, "2026-08-13T12:00:00.000Z");
  });

  it("수정 취소 — 값이 원래대로 남고 요청도 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "updateMatchRound");
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "수정" }));
    fireEvent.change(screen.getByLabelText("매칭 예정 일시 수정"), {
      target: { value: "2026-08-13T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "취소" }));

    await waitFor(() =>
      expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("삭제 — confirm 승인 시 목록에서 제거", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "deleteMatchRound").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "삭제" }));

    await waitFor(() =>
      expect(screen.queryByText("2026-08-20 21:00")).toBeNull(),
    );
    expect(spy).toHaveBeenCalledWith(1);
  });

  it("삭제 — confirm 취소 시 아무 일도 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "deleteMatchRound");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "삭제" }));

    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument();
  });

  it("로드 실패 시 에러 문구", async () => {
    vi.spyOn(api, "listMatchRounds").mockRejectedValue(new Error("fail"));
    render(<RoundTab />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/RoundTab.test.tsx`
Expected: FAIL — `Failed to resolve import "./RoundTab"`

- [ ] **Step 3: 타입 추가**

`frontend/src/lib/types.ts` 파일 끝에 추가:

```ts
export interface AdminMatchRoundOut {
  id: number;
  scheduled_at: string;
  status: "pending" | "done";
}
```

- [ ] **Step 4: API 클라이언트 추가**

`frontend/src/lib/api.ts`의 타입 import 목록에 `AdminMatchRoundOut`을 더하고, 파일 끝에 추가:

```ts
export function listMatchRounds(): Promise<AdminMatchRoundOut[]> {
  return apiFetch<AdminMatchRoundOut[]>("/admin/match-rounds", { method: "GET" });
}

export function createMatchRound(
  scheduledAtUtcISO: string,
): Promise<AdminMatchRoundOut> {
  return apiFetch<AdminMatchRoundOut>("/admin/match-rounds", {
    method: "POST",
    body: JSON.stringify({ scheduled_at: scheduledAtUtcISO }),
  });
}

export function updateMatchRound(
  id: number,
  scheduledAtUtcISO: string,
): Promise<AdminMatchRoundOut> {
  return apiFetch<AdminMatchRoundOut>(`/admin/match-rounds/${id}`, {
    method: "PUT",
    body: JSON.stringify({ scheduled_at: scheduledAtUtcISO }),
  });
}

export function deleteMatchRound(id: number): Promise<void> {
  return apiFetch<void>(`/admin/match-rounds/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 5: CSS 클래스 추가**

`frontend/src/pages/Admin/Admin.module.css` 파일 끝에 추가:

```css
.formRow {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.formLabel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  font-size: 14px;
}
```

- [ ] **Step 6: RoundTab 구현**

`frontend/src/pages/Admin/RoundTab.tsx` 신규:

```tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listMatchRounds,
  createMatchRound,
  updateMatchRound,
  deleteMatchRound,
} from "../../lib/api";
import type { AdminMatchRoundOut } from "../../lib/types";
import { formatKST, kstInputToUtcISO, utcISOToKstInput } from "../../lib/datetime";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

const INVALID_INPUT = "올바른 일시를 입력하세요.";
const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

// 서버가 주는 값은 모두 같은 형식의 naive UTC 문자열이라 사전순 = 시간순이다.
function sortDesc(items: AdminMatchRoundOut[]): AdminMatchRoundOut[] {
  return [...items].sort((a, b) => b.scheduled_at.localeCompare(a.scheduled_at));
}

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

export default function RoundTab() {
  const [items, setItems] = useState<AdminMatchRoundOut[]>([]);
  const [form, setForm] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listMatchRounds()
      .then((data) => {
        if (active) setItems(sortDesc(data));
      })
      .catch(() => {
        if (active) setError("목록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const iso = kstInputToUtcISO(form);
    if (iso === null) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      // 낙관적 갱신을 하지 않는다 — 서버 응답을 받은 뒤에만 목록을 바꾼다
      const created = await createMatchRound(iso);
      setItems((prev) => sortDesc([...prev, created]));
      setForm("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function startEdit(round: AdminMatchRoundOut) {
    setError("");
    setEditingId(round.id);
    setEditValue(utcISOToKstInput(round.scheduled_at));
  }

  async function handleSave(id: number) {
    setError("");
    const iso = kstInputToUtcISO(editValue);
    if (iso === null) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      const updated = await updateMatchRound(id, iso);
      setItems((prev) => sortDesc(prev.map((r) => (r.id === id ? updated : r))));
      setEditingId(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("이 라운드를 삭제할까요?")) return;
    setError("");
    try {
      await deleteMatchRound(id);
      setItems((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.formRow} onSubmit={handleCreate}>
        <label className={styles.formLabel} htmlFor="round-new">
          매칭 예정 일시
          <input
            id="round-new"
            type="datetime-local"
            value={form}
            onChange={(e) => setForm(e.target.value)}
          />
        </label>
        <Button type="submit">추가</Button>
      </form>

      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && items.length === 0 && <p>예정된 라운드 없음</p>}

      {items.map((round) => (
        <div key={round.id} className={styles.card}>
          <span className={styles.badge}>
            {round.status === "pending" ? "예정" : "완료"}
          </span>
          {editingId === round.id ? (
            <>
              <label className={styles.formLabel} htmlFor={`round-edit-${round.id}`}>
                매칭 예정 일시 수정
                <input
                  id={`round-edit-${round.id}`}
                  type="datetime-local"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
              </label>
              <div className={styles.actions}>
                <Button onClick={() => handleSave(round.id)}>저장</Button>
                <Button onClick={() => setEditingId(null)}>취소</Button>
              </div>
            </>
          ) : (
            <>
              <div className={styles.name}>{formatKST(round.scheduled_at)}</div>
              {round.status === "pending" && (
                <div className={styles.actions}>
                  <Button onClick={() => startEdit(round)}>수정</Button>
                  <Button onClick={() => handleDelete(round.id)}>삭제</Button>
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/RoundTab.test.tsx`
Expected: PASS — 10 passed

- [ ] **Step 8: 린트 · 타입 확인**

Run: `cd frontend && npm run lint && npx tsc --noEmit`
Expected: 경고 0, 오류 0

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Admin/RoundTab.tsx frontend/src/pages/Admin/RoundTab.test.tsx frontend/src/pages/Admin/Admin.module.css
git commit -F <메시지파일>
```

메시지:

```
feat(frontend): 관리자 라운드 탭 — 목록·생성·수정·삭제

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 5: 프론트 — `/admin` 탭 통합

**Files:**
- Modify: `frontend/src/pages/Admin/Admin.tsx`
- Test: `frontend/src/pages/Admin/Admin.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `RoundTab`, `listMatchRounds`
- Produces: `/admin`의 세 번째 탭 — 버튼 이름 "라운드", `id="tab-round"`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/pages/Admin/Admin.test.tsx`의 `beforeEach`에 라운드 목록 목을 추가:

```tsx
beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
  vi.spyOn(api, "listReports").mockResolvedValue([]);
  vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
});
```

`describe("Admin", ...)` 안에 추가:

```tsx
  it("라운드 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("tab", { name: "라운드" }));
    await waitFor(() => expect(api.listMatchRounds).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
    expect(screen.getByText("예정된 라운드 없음")).toBeInTheDocument();
  });

  it("탭 3개 중 선택된 하나만 aria-selected=true", async () => {
    render(<Admin />);
    const round = screen.getByRole("tab", { name: "라운드" });
    expect(screen.getAllByRole("tab")).toHaveLength(3);
    expect(round).toHaveAttribute("aria-selected", "false");

    fireEvent.click(round);
    await waitFor(() => expect(round).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "학생증 심사" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    expect(screen.getByRole("tabpanel")).toHaveAttribute(
      "aria-labelledby",
      "tab-round",
    );
  });
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/Admin.test.tsx`
Expected: FAIL — `Unable to find an accessible element with the role "tab" and name "라운드"`

- [ ] **Step 3: Admin.tsx 수정**

`frontend/src/pages/Admin/Admin.tsx` 전체를 아래로 교체. 탭이 셋이 되면서 패널 렌더를 중첩 삼항 대신 조건부 렌더 3개로 편다. ARIA 속성과 렌더 결과는 기존과 동일하다.

```tsx
import { useState } from "react";
import VerificationTab from "./VerificationTab";
import ReportTab from "./ReportTab";
import RoundTab from "./RoundTab";
import styles from "./Admin.module.css";

type Tab = "verification" | "report" | "round";

export default function Admin() {
  const [tab, setTab] = useState<Tab>("verification");

  return (
    <div>
      <h1 className={styles.title}>관리자</h1>
      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          id="tab-verification"
          aria-selected={tab === "verification"}
          className={tab === "verification" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("verification")}
        >
          학생증 심사
        </button>
        <button
          type="button"
          role="tab"
          id="tab-report"
          aria-selected={tab === "report"}
          className={tab === "report" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("report")}
        >
          신고 · 건의
        </button>
        <button
          type="button"
          role="tab"
          id="tab-round"
          aria-selected={tab === "round"}
          className={tab === "round" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("round")}
        >
          라운드
        </button>
      </div>
      {tab === "verification" && (
        <div role="tabpanel" aria-labelledby="tab-verification" tabIndex={0}>
          <VerificationTab />
        </div>
      )}
      {tab === "report" && (
        <div role="tabpanel" aria-labelledby="tab-report" tabIndex={0}>
          <ReportTab />
        </div>
      )}
      {tab === "round" && (
        <div role="tabpanel" aria-labelledby="tab-round" tabIndex={0}>
          <RoundTab />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/Admin.test.tsx`
Expected: PASS — 6 passed

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Admin/Admin.tsx frontend/src/pages/Admin/Admin.test.tsx
git commit -F <메시지파일>
```

메시지:

```
feat(frontend): /admin 라운드 탭 추가

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 6: 전체 검증

**Files:** 없음 (검증만)

**Interfaces:**
- Consumes: Task 1~5 전부

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd backend && uv run pytest`
Expected: PASS — 136 passed

- [ ] **Step 2: 프론트 린트 · 타입 · 테스트**

Run: `cd frontend && npm run lint && npx tsc --noEmit && npm test`
Expected: 경고 0 / 오류 0 / 전부 통과 (기존 130 + datetime 9 + RoundTab 10 + Admin 2 = 151)

- [ ] **Step 3: 서버 기동**

```
cd backend && uv run uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

관리자 계정이 필요하다. 없으면 `dev.db`에서 `is_admin=1`인 유저로 로그인한다.

- [ ] **Step 4: 육안 확인 5종**

| # | 확인 |
|---|------|
| 1 | `/admin` → "라운드" 탭이 보이고, 클릭하면 목록이 뜬다 |
| 2 | 3일 뒤 일시를 넣고 [추가] → 목록에 나타나고, `/home`에 `D-3`과 같은 일시가 뜬다 |
| 3 | 그 라운드를 [수정]으로 1일 뒤로 옮김 → `/home`의 D-day가 따라 바뀐다 |
| 4 | 같은 시각으로 하나 더 추가 → "같은 시각의 라운드가 이미 있습니다" 표시, 목록 변화 없음 |
| 5 | [삭제] → confirm 승인 후 목록에서 사라지고 `/home`이 빈 상태로 돌아간다 |

**중요**: 육안 확인 후 만든 라운드를 지워 `dev.db`를 원상복구한다(`delete from match_rounds`). `/home` 작업 때도 같은 정리를 했다.

- [ ] **Step 5: 저장된 값이 UTC-naive인지 직접 확인**

```python
import sqlite3
conn = sqlite3.connect(r"C:\workSpace\datingWeb\backend\dev.db")
print(conn.execute("select id, scheduled_at, status from match_rounds").fetchall())
```

Expected: `scheduled_at`에 `+09:00`이나 `Z` 같은 접미사가 **없고**, KST 입력보다 9시간 이른 값이어야 한다. 접미사가 보이면 `_to_naive_utc`가 안 걸린 것이다.

- [ ] **Step 6: PR 생성 전 사용자 확인**

브랜치 `feat/round-management`를 push하고 PR을 만들기 전에 사용자에게 허락을 받는다(`CLAUDE.md`: git push는 허락 후에만).

## Self-Review 결과

- **스펙 커버리지**: 파일 배치 → Task 1 · 스키마 → Task 1 · 타임존 정규화 → Task 1(Step 4) + 테스트 2건 · 검증 4종 → Task 1·2 · 엔드포인트 4개 → Task 1·2 · 변환 유틸 → Task 3 · 타입/API → Task 4 · RoundTab → Task 4 · Admin 통합 → Task 5 · 에러 처리 표 → Task 4 테스트 · 검증 기준 → Task 6. 누락 없음
- **타입 일관성**: `AdminMatchRoundOut`(백엔드 Pydantic / 프론트 인터페이스) 필드 3개 일치, `kstInputToUtcISO`/`utcISOToKstInput` 이름이 Task 3 정의와 Task 4 사용처에서 동일, `MatchRoundIn`은 Task 1에서 정의해 Task 2에서 재사용
- **범위**: 실행·Match·`executed_at`을 건드리는 단계가 하나도 없다
