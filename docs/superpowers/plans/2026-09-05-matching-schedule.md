# 매칭 예약 자동 실행 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 라운드의 `scheduled_at`이 되면 서버가 스스로 `run_matching`을 호출한다.

**Architecture:** FastAPI 앱 안에서 백그라운드 asyncio 태스크 하나가 60초마다 깨어, 실행할 때가 된 `pending` 라운드를 찾아 기존 `run_matching`을 호출한다. 판정 로직은 `now`를 인자로 받는 순수 함수 `run_due_once`에 모아 시간을 기다리지 않고 테스트한다. 실패·놓침 사유는 `match_rounds.last_error`에 남아 관리자 화면에 뜬다.

**Tech Stack:** Python 3.13 / FastAPI / SQLAlchemy 2.0 (sync) / Alembic / pytest — 백엔드. React + TypeScript + Vite + Vitest — 프론트. **새 의존성 없음** (APScheduler·celery 안 씀).

**Spec:** `docs/superpowers/specs/2026-09-05-matching-schedule-design.md`

## Global Constraints

- `POLL_INTERVAL = 60` (초), `CATCHUP_GRACE = timedelta(hours=1)` — 스펙 "상수" 표
- 놓침 문구 정확히: `예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요`
- `last_error` 컬럼: `String(500)`, nullable. 넘치면 잘라 넣는다
- **재시도 없음** — `last_error`가 채워진 라운드는 다시 실행하지 않는다 (조회 필터에 박는다)
- `RoundStatus`에 새 값을 추가하지 않는다. 실패한 라운드는 계속 `pending`이다
- `app/services/matching.py`·`pairing.py`·`scoring.py` 변경은 **Task 1의 한 줄뿐** (성공 시 `last_error` 초기화)
- 유저용 `MatchRoundOut`(`id`, `scheduled_at`)은 손대지 않는다. `last_error`는 관리자 응답에만
- 새 HTTP 엔드포인트 없음
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By` 트레일러
- 브랜치: `feat/matching-schedule` (다파일 + TDD 다중 커밋 → PR 대상)
- 시각은 전부 **naive UTC** (`datetime.utcnow()`). KST 변환은 프론트에만 있다

## File Structure

| 파일 | 책임 | 상태 |
|------|------|------|
| `backend/app/services/scheduler.py` | 폴링 루프 + 실행 판정. DB는 알지만 매칭 내부는 모른다 | 신규 |
| `backend/tests/test_scheduler.py` | 판정 로직 전 경계 | 신규 |
| `backend/alembic/versions/<new>_match_rounds_last_error.py` | `last_error` 컬럼 추가 | 신규 |
| `backend/app/models/match.py` | `MatchRound.last_error` 필드 | 수정 |
| `backend/app/schemas/round.py` | `AdminMatchRoundOut.last_error` | 수정 |
| `backend/app/services/matching.py` | 성공 시 `last_error` 초기화 (1줄) | 수정 |
| `backend/app/config.py` | `scheduler_enabled` 플래그 | 수정 |
| `backend/app/main.py` | lifespan에서 루프 태스크 생성·취소 | 수정 |
| `backend/tests/conftest.py` | 테스트에서 루프 끄기 | 수정 |
| `frontend/src/lib/types.ts` | `AdminMatchRoundOut.last_error` | 수정 |
| `frontend/src/pages/Admin/RoundTab.tsx` | 실패 사유 표시 1줄 | 수정 |

---

### Task 1: `last_error` 컬럼 — 저장·노출·초기화

라운드가 "왜 자동 실행이 안 됐는지"를 담을 자리를 만든다. 스케줄러는 아직 없지만, 이 컬럼과 초기화 규칙이 먼저 서야 Task 2가 기록할 곳이 생긴다.

**Files:**
- Modify: `backend/app/models/match.py` (`MatchRound`, 25~31행 근처)
- Create: `backend/alembic/versions/<생성된id>_match_rounds_last_error.py`
- Modify: `backend/app/schemas/round.py` (`AdminMatchRoundOut`)
- Modify: `backend/app/services/matching.py` (`_execute` 끝, `round_.status = RoundStatus.done` 줄 근처)
- Test: `backend/tests/test_admin_rounds.py`, `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `MatchRound.last_error: str | None` — 마지막 자동 실행 실패·놓침 사유
  - `AdminMatchRoundOut.last_error: str | None` — 관리자 응답 필드
  - 불변식: `run_matching`이 성공하면 `last_error`는 `None`이 된다

- [ ] **Step 1: 브랜치 생성**

```bash
cd /c/workSpace/datingWeb
git checkout -b feat/matching-schedule
```

- [ ] **Step 2: 실패하는 테스트 2개를 쓴다**

`backend/tests/test_admin_rounds.py` 맨 아래에 추가:

```python
def test_admin_list_exposes_last_error(admin_client: TestClient):
    _add_rounds(
        MatchRound(
            scheduled_at=_hours(-3),
            status=RoundStatus.pending,
            last_error="ValueError: 뭔가 터짐",
        ),
    )
    res = admin_client.get("/admin/match-rounds")
    assert res.status_code == 200
    assert res.json()[0]["last_error"] == "ValueError: 뭔가 터짐"


def test_admin_list_last_error_is_null_by_default(admin_client: TestClient):
    _add_rounds(MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending))
    res = admin_client.get("/admin/match-rounds")
    assert res.json()[0]["last_error"] is None
```

`backend/tests/test_matching.py` 맨 아래에 추가 (`run_matching`·`MatchRound`·`RoundStatus`·`TestingSessionLocal`은 이 파일에 이미 import 돼 있다 — 없으면 파일 상단 import를 따라 맞춘다):

```python
def test_successful_run_clears_last_error():
    """수동으로 되살린 라운드의 done 카드에 옛 실패 문구가 남으면 안 된다."""
    db = TestingSessionLocal()
    round_ = MatchRound(
        scheduled_at=datetime.utcnow(),
        status=RoundStatus.pending,
        last_error="이전 실행 실패",
    )
    db.add(round_)
    db.commit()
    round_id = round_.id

    # 유저 풀이 비어 있어도 매칭은 정상 종료한다 (0쌍) — optimal_pairs가 빈 입력을 걸러낸다
    run_matching(db, round_id)

    db.expire_all()
    saved = db.get(MatchRound, round_id)
    assert saved.status == RoundStatus.done
    assert saved.last_error is None
    db.close()
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest tests/test_admin_rounds.py::test_admin_list_exposes_last_error tests/test_matching.py::test_successful_run_clears_last_error -v
```

Expected: FAIL — `TypeError: 'last_error' is an invalid keyword argument for MatchRound`

- [ ] **Step 4: 모델에 컬럼 추가**

`backend/app/models/match.py`의 `MatchRound`에서 `status` 필드 **아래**에 추가:

```python
    # 마지막 자동 실행이 실패했거나 유예를 넘겨 건너뛴 사유. 성공하면 지워진다.
    # 값이 차 있으면 스케줄러가 그 라운드를 다시 잡지 않는다 = 재시도 금지의 구현
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

`String`은 이미 import 돼 있다. 추가 import 없음.

- [ ] **Step 5: 마이그레이션 생성**

```bash
cd /c/workSpace/datingWeb/backend
uv run alembic revision -m "match_rounds last_error"
```

생성된 파일을 열어 `upgrade`/`downgrade`를 아래로 채운다 (`revision` 값은 자동 생성된 것을 그대로 두고, `down_revision`이 `'663fa9cf7ce5'`인지 확인한다 — 아니면 `uv run alembic heads`로 확인해 맞춘다):

```python
def upgrade() -> None:
    """Upgrade schema."""
    # nullable — 기존 행은 NULL(= 실패 이력 없음)로 남는다
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.add_column(sa.Column("last_error", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.drop_column("last_error")
```

- [ ] **Step 6: 마이그레이션 적용 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run alembic upgrade head && uv run alembic current
```

Expected: 방금 만든 revision이 current로 찍힌다. (테스트는 `Base.metadata.create_all`을 쓰므로 마이그레이션과 무관하게 통과한다 — 그래서 이 단계를 눈으로 확인해야 한다.)

- [ ] **Step 7: 관리자 응답 스키마에 필드 추가**

`backend/app/schemas/round.py`의 `AdminMatchRoundOut`:

```python
class AdminMatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime
    status: RoundStatus
    # 마지막 자동 실행 실패·놓침 사유. 유저용 MatchRoundOut에는 넣지 않는다 (관리자 정보)
    last_error: str | None = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 8: 성공 시 초기화 한 줄**

`backend/app/services/matching.py`의 `_execute` 끝부분, `round_.status = RoundStatus.done` 바로 아래:

```python
    round_.status = RoundStatus.done
    round_.executed_at = datetime.utcnow()
    round_.last_error = None  # 성공했으니 옛 실패 사유를 지운다 (자동·수동 공통)
```

- [ ] **Step 9: 테스트 통과 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest -q
```

Expected: 전부 PASS (새 3건 포함)

- [ ] **Step 10: 커밋**

```bash
cd /c/workSpace/datingWeb
git add backend/app/models/match.py backend/app/schemas/round.py backend/app/services/matching.py backend/alembic/versions backend/tests/test_admin_rounds.py backend/tests/test_matching.py
git commit -F - <<'EOF'
feat(backend): match_rounds.last_error 컬럼 — 자동 실행 실패 사유 기록

관리자 응답에만 노출하고, run_matching 성공 시 초기화한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: `run_due_once` — 실행 판정

스케줄러의 두뇌. `now`를 인자로 받으므로 시간을 기다리는 테스트가 없다. 루프는 아직 없다 — 이 태스크는 함수만 만든다.

**Files:**
- Create: `backend/app/services/scheduler.py`
- Test: `backend/tests/test_scheduler.py` (신규)

**Interfaces:**
- Consumes: `MatchRound.last_error` (Task 1), 기존 `run_matching(db, round_id)`, 기존 예외 `RoundNotPending`
- Produces:
  - `run_due_once(db: Session, now: datetime) -> None` — 한 번의 점검
  - `POLL_INTERVAL: int = 60`, `CATCHUP_GRACE: timedelta = timedelta(hours=1)`, `MISSED_MESSAGE: str`
  - Task 3이 `run_due_once`와 `POLL_INTERVAL`을 쓴다

- [ ] **Step 1: 실패하는 테스트 파일을 쓴다**

`backend/tests/test_scheduler.py` 전체:

```python
"""예약 실행 판정 (설계 2026-09-05). now를 주입하므로 실제 시간을 기다리지 않는다."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.match import MatchRound, RoundStatus
from app.services import scheduler
from app.services.matching import RoundNotPending
from app.services.scheduler import CATCHUP_GRACE, MISSED_MESSAGE, run_due_once
from tests.conftest import TestingSessionLocal

BASE = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


def _round(db, scheduled_at: datetime, **kwargs) -> int:
    round_ = MatchRound(scheduled_at=scheduled_at, **kwargs)
    db.add(round_)
    db.commit()
    return round_.id


def _status(db, round_id: int) -> RoundStatus:
    db.expire_all()
    return db.get(MatchRound, round_id).status


def _error(db, round_id: int) -> str | None:
    db.expire_all()
    return db.get(MatchRound, round_id).last_error


# 유저 풀이 비어 있으면 매칭은 0쌍으로 정상 종료한다. 이 테스트들이 보는 것은
# "언제 도느냐"이지 "누가 짝이 되느냐"가 아니다 (그건 test_matching.py 담당)


def test_runs_exactly_at_scheduled_time(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE)
    assert _status(db, round_id) == RoundStatus.done


def test_runs_within_grace(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=59))
    assert _status(db, round_id) == RoundStatus.done


def test_does_not_run_before_scheduled_time(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE - timedelta(seconds=1))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) is None


def test_marks_missed_after_grace(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=61))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == MISSED_MESSAGE


def test_grace_boundary_is_exclusive(db):
    """정확히 유예 경계면 실행하지 않는다 — 표의 부등호를 고정한다."""
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + CATCHUP_GRACE)
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == MISSED_MESSAGE


def test_missed_round_is_marked_only_once(db):
    round_id = _round(db, BASE, status=RoundStatus.pending)
    run_due_once(db, BASE + timedelta(minutes=61))
    run_due_once(db, BASE + timedelta(minutes=62))
    assert _error(db, round_id) == MISSED_MESSAGE
    assert _status(db, round_id) == RoundStatus.pending


def test_round_with_error_is_not_retried_within_grace(db):
    round_id = _round(
        db, BASE, status=RoundStatus.pending, last_error="이전 실패"
    )
    run_due_once(db, BASE + timedelta(minutes=5))
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == "이전 실패"


def test_running_and_done_rounds_are_ignored(db):
    running_id = _round(db, BASE, status=RoundStatus.running)
    done_id = _round(db, BASE - timedelta(days=7), status=RoundStatus.done)
    run_due_once(db, BASE + timedelta(minutes=5))
    assert _status(db, running_id) == RoundStatus.running
    assert _status(db, done_id) == RoundStatus.done


def test_failure_records_error_and_keeps_pending(db, monkeypatch):
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def boom(_db, _round_id):
        raise ValueError("점수 계산 폭발")

    monkeypatch.setattr(scheduler, "run_matching", boom)
    run_due_once(db, BASE)
    assert _status(db, round_id) == RoundStatus.pending
    assert _error(db, round_id) == "ValueError: 점수 계산 폭발"


def test_long_error_is_truncated(db, monkeypatch):
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def boom(_db, _round_id):
        raise ValueError("x" * 1000)

    monkeypatch.setattr(scheduler, "run_matching", boom)
    run_due_once(db, BASE)
    assert len(_error(db, round_id)) == 500


def test_round_not_pending_is_silent(db, monkeypatch):
    """다른 워커가 먼저 선점한 경우. 그쪽은 정상 실행 중이므로 에러를 남기면 안 된다."""
    round_id = _round(db, BASE, status=RoundStatus.pending)

    def taken(_db, _round_id):
        raise RoundNotPending

    monkeypatch.setattr(scheduler, "run_matching", taken)
    run_due_once(db, BASE)
    assert _error(db, round_id) is None


def test_processes_multiple_due_rounds(db):
    first = _round(db, BASE - timedelta(minutes=30), status=RoundStatus.pending)
    second = _round(db, BASE - timedelta(minutes=10), status=RoundStatus.pending)
    run_due_once(db, BASE)
    assert _status(db, first) == RoundStatus.done
    assert _status(db, second) == RoundStatus.done
```

- [ ] **Step 2: 실패 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest tests/test_scheduler.py -v
```

Expected: 수집 단계에서 FAIL — `ModuleNotFoundError: No module named 'app.services.scheduler'`

- [ ] **Step 3: `run_due_once` 구현 (루프는 아직 안 만든다)**

`backend/app/services/scheduler.py` 신규:

```python
"""예약된 라운드를 제 시간에 실행한다 (설계 2026-09-05).

판정은 run_due_once에 모아 now를 주입받는다 — 루프에는 테스트할 것이 남지 않는다.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.match import MatchRound, RoundStatus
from app.services.matching import RoundNotPending, run_matching

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # 초. 최대 이만큼 늦게 실행된다
CATCHUP_GRACE = timedelta(hours=1)  # 예정 시각 + 이 시간까지는 늦어도 실행한다
MISSED_MESSAGE = "예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요"
_ERROR_MAX = 500  # last_error 컬럼 길이


def run_due_once(db: Session, now: datetime) -> None:
    """실행할 때가 된 라운드를 처리한다. 한 번의 폴링이 하는 일 전부."""
    # last_error가 찬 라운드를 애초에 뽑지 않는 것이 '재시도 없음'의 구현이다.
    # 이 필터가 없으면 실패한 라운드가 유예 1시간 동안 60초마다 다시 터진다.
    # (id, scheduled_at)으로 먼저 굳힌다 — run_matching이 커밋하면 ORM 객체가 만료된다
    due = [
        (round_.id, round_.scheduled_at)
        for round_ in db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.pending,
            MatchRound.scheduled_at <= now,
            MatchRound.last_error.is_(None),
        )
        .order_by(MatchRound.scheduled_at.asc())
        .all()
    ]

    for round_id, scheduled_at in due:
        if now - scheduled_at >= CATCHUP_GRACE:
            # 너무 늦었다. 유저가 모르는 사이 도는 것보다 관리자 판단에 맡긴다
            _record_error(db, round_id, MISSED_MESSAGE)
            continue
        try:
            run_matching(db, round_id)
        except RoundNotPending:
            # 다른 워커가 먼저 선점했다. 그쪽이 정상 실행 중이므로 에러가 아니다
            logger.info("라운드 %s는 이미 다른 실행이 선점했다", round_id)
        except Exception as exc:
            logger.exception("라운드 %s 자동 실행 실패", round_id)
            _record_error(db, round_id, f"{type(exc).__name__}: {exc}")


def _record_error(db: Session, round_id: int, message: str) -> None:
    """실패 사유를 별도 트랜잭션으로 기록한다.

    run_matching이 실패하며 세션을 rollback 해둔 상태라, 그 위에 얹지 않고
    UPDATE 하나로 새로 쓴다. status는 건드리지 않는다 — 실패한 라운드는 여전히 pending이다.
    """
    db.rollback()
    db.query(MatchRound).filter(MatchRound.id == round_id).update(
        {MatchRound.last_error: message[:_ERROR_MAX]},
        synchronize_session=False,
    )
    db.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest tests/test_scheduler.py -v
```

Expected: 12건 전부 PASS

- [ ] **Step 5: 전체 테스트로 회귀 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest -q
```

Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
cd /c/workSpace/datingWeb
git add backend/app/services/scheduler.py backend/tests/test_scheduler.py
git commit -F - <<'EOF'
feat(backend): 예약 실행 판정 run_due_once — 유예 1시간, 재시도 없음

now를 주입받는 순수 판정 함수. 유예 내면 실행, 넘기면 놓침 기록,
실패하면 사유만 남기고 재시도하지 않는다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: 루프와 앱 수명주기

`run_due_once`를 실제로 60초마다 부른다. 여기서부터 서버가 스스로 매칭을 돌린다.

**Files:**
- Modify: `backend/app/services/scheduler.py` (파일 끝에 추가)
- Modify: `backend/app/config.py` (`Settings`)
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py` (import 직후)
- Test: `backend/tests/test_scheduler.py` (`_tick` 케이스 추가)

**Interfaces:**
- Consumes: `run_due_once(db, now)`, `POLL_INTERVAL` (Task 2)
- Produces:
  - `scheduler_loop() -> None` (async) — 무한 루프
  - `_tick() -> None` — 세션 하나 열고 `run_due_once` 호출 후 닫기
  - `settings.scheduler_enabled: bool` — 기본 `True`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_scheduler.py` 맨 아래에 추가:

```python
def test_tick_opens_a_session_and_calls_run_due_once(monkeypatch):
    """루프가 판정 함수에 세션과 현재 시각을 넘기는 이음매만 확인한다.
    루프 자체(asyncio.sleep)는 타이밍 테스트가 flaky해지므로 테스트하지 않는다."""
    calls = []

    def spy(db, now):
        calls.append((db, now))

    monkeypatch.setattr(scheduler, "run_due_once", spy)
    monkeypatch.setattr(scheduler, "SessionLocal", TestingSessionLocal)

    scheduler._tick()

    assert len(calls) == 1
    db, now = calls[0]
    assert isinstance(db, Session)
    assert isinstance(now, datetime)
```

`backend/tests/conftest.py`의 import 블록 아래(그리고 `from app.main import app` **다음**)에 추가:

```python
from app.config import settings

# 테스트에서 백그라운드 루프를 띄우지 않는다. TestClient가 lifespan을 실행하므로
# 이 줄이 없으면 모든 테스트가 60초 타이머 태스크를 하나씩 남긴다
settings.scheduler_enabled = False
```

- [ ] **Step 2: 실패 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest tests/test_scheduler.py::test_tick_opens_a_session_and_calls_run_due_once -v
```

Expected: FAIL — `AttributeError: module 'app.services.scheduler' has no attribute '_tick'` (그리고 conftest의 `settings.scheduler_enabled` 대입은 pydantic-settings 모델이라 통과한다. `ValidationError`가 나면 Step 4에서 필드를 먼저 추가한 뒤 다시 돌린다)

- [ ] **Step 3: 루프 구현**

`backend/app/services/scheduler.py` 상단 import에 추가:

```python
import asyncio
```

그리고 `from app.models.match import ...` 위에:

```python
from app.database import SessionLocal
```

파일 맨 아래에 추가:

```python
def _tick() -> None:
    """폴링 한 번. 세션을 매번 새로 연다 — 하나를 몇 주씩 붙들면 끊긴 채로 남는다."""
    db = SessionLocal()
    try:
        run_due_once(db, datetime.utcnow())
    finally:
        db.close()


async def scheduler_loop() -> None:
    """앱이 사는 동안 도는 루프. 예외가 나도 죽지 않는다 —
    한 번의 실패로 루프가 끝나면 그 뒤 모든 예약이 조용히 사라진다."""
    while True:
        # 먼저 자고 나중에 일한다. 부팅 직후(마이그레이션 전일 수 있다) 매칭을 돌리지 않는다
        await asyncio.sleep(POLL_INTERVAL)
        try:
            # run_matching은 동기 함수고 최장 131초다. 직접 await 하면 그동안 API가 멈춘다
            await asyncio.to_thread(_tick)
        except Exception:
            logger.exception("스케줄러 점검 실패 — 다음 주기에 다시 시도한다")
```

- [ ] **Step 4: 설정 플래그 추가**

`backend/app/config.py`의 `Settings`에 추가 (`verification_dir` 아래):

```python
    # 기본 True — Railway에서 환경변수를 빠뜨렸을 때 기능이 조용히 죽는 쪽이 더 나쁘다.
    # 테스트는 conftest.py에서 False로 내린다
    scheduler_enabled: bool = True
```

- [ ] **Step 5: lifespan 연결**

`backend/app/main.py`를 아래처럼 바꾼다 (기존 CORS·라우터·static·health는 그대로 둔다):

```python
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import router
from app.config import settings
from app.services.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """예약 매칭 루프를 앱 수명에 묶는다 (설계 2026-09-05)."""
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task is not None:
        task.cancel()


app = FastAPI(title="DateDrop Korea API", version="0.1.0", lifespan=lifespan)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest -q
```

Expected: 전부 PASS. 경고에 `Task was destroyed but it is pending` 이 뜨면 conftest의 `scheduler_enabled = False`가 적용되지 않은 것이다 — 대입이 `from app.main import app` 뒤에 있는지 확인한다.

- [ ] **Step 7: 육안 검증**

```bash
cd /c/workSpace/datingWeb/backend
uv run uvicorn app.main:app --reload
```

다른 터미널에서 프론트를 띄우고 `/admin` 라운드 탭에서 **2분 뒤** 시각으로 라운드를 만든다. 아무것도 누르지 않고 3분 기다린 뒤 새로고침 → 카드가 `완료`로 바뀌어 있어야 한다.

- [ ] **Step 8: 커밋**

```bash
cd /c/workSpace/datingWeb
git add backend/app/services/scheduler.py backend/app/main.py backend/app/config.py backend/tests/conftest.py backend/tests/test_scheduler.py
git commit -F - <<'EOF'
feat(backend): 예약 매칭 폴링 루프 — lifespan에 60초 스케줄러 연결

run_matching이 동기 함수라 asyncio.to_thread로 돌린다.
SCHEDULER_ENABLED로 끌 수 있고 테스트에서는 꺼진다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: 관리자 화면에 실패 사유 표시

자동 실행이 실패하거나 유예를 넘겼을 때 관리자가 그 사실을 알고 수동 버튼을 누를 수 있게 한다.

**Files:**
- Modify: `frontend/src/lib/types.ts` (`AdminMatchRoundOut`)
- Modify: `frontend/src/pages/Admin/RoundTab.tsx`
- Test: `frontend/src/pages/Admin/RoundTab.test.tsx`

**Interfaces:**
- Consumes: `AdminMatchRoundOut.last_error` (Task 1의 API 응답)
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/pages/Admin/RoundTab.test.tsx` — 파일 상단의 기존 픽스처 두 개에 `last_error: null`을 더하고, 아래 픽스처와 테스트를 추가한다:

```tsx
const pending: AdminMatchRoundOut = {
  id: 1,
  scheduled_at: "2026-08-20T12:00:00",  // KST 21:00
  status: "pending",
  last_error: null,
};

const done: AdminMatchRoundOut = {
  id: 2,
  scheduled_at: "2026-08-06T12:00:00",
  status: "done",
  last_error: null,
};

const failed: AdminMatchRoundOut = {
  id: 3,
  scheduled_at: "2026-08-13T12:00:00",
  status: "pending",
  last_error: "예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요",
};
```

`describe("RoundTab", ...)` 안에 테스트 2건 추가:

```tsx
  it("자동 실행 실패 사유를 카드에 표시한다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([failed]);
    render(<RoundTab />);
    await waitFor(() =>
      expect(
        screen.getByText(
          "예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요",
        ),
      ).toBeInTheDocument(),
    );
    // 폴백 수단이 남아 있어야 한다
    expect(screen.getByRole("button", { name: "매칭 실행" })).toBeInTheDocument();
  });

  it("last_error가 없으면 아무 문구도 뜨지 않는다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));
    expect(screen.queryByText(/자동 실행되지 않았습니다/)).not.toBeInTheDocument();
  });
```

- [ ] **Step 2: 실패 확인**

```bash
cd /c/workSpace/datingWeb/frontend
npx tsc --noEmit
```

Expected: FAIL — `Object literal may only specify known properties, and 'last_error' does not exist in type 'AdminMatchRoundOut'`

- [ ] **Step 3: 타입에 필드 추가**

`frontend/src/lib/types.ts`의 `AdminMatchRoundOut`:

```ts
export interface AdminMatchRoundOut {
  id: number;
  scheduled_at: string;
  status: "pending" | "running" | "done";
  /** 마지막 자동 실행 실패·놓침 사유. 성공하면 null로 돌아온다 */
  last_error: string | null;
}
```

- [ ] **Step 4: 테스트가 이제 렌더 실패로 넘어가는지 확인**

```bash
cd /c/workSpace/datingWeb/frontend
npm test -- RoundTab
```

Expected: 새 테스트 1건 FAIL — 문구를 찾지 못한다 (`Unable to find an element with the text`)

- [ ] **Step 5: 카드에 한 줄 추가**

`frontend/src/pages/Admin/RoundTab.tsx`, 비편집 분기의 날짜 `div` **바로 아래**:

```tsx
              <div className={styles.name}>{formatKST(round.scheduled_at)}</div>
              {round.last_error && (
                <p className={styles.error}>{round.last_error}</p>
              )}
```

상태 배지(`STATUS_LABEL`)는 손대지 않는다 — 서버 `RoundStatus`와 1:1을 유지한다.

- [ ] **Step 6: 프론트 검증 4종**

```bash
cd /c/workSpace/datingWeb/frontend
npx tsc --noEmit && npm run lint && npm test
```

Expected: 타입 오류 0, lint 경고 0, 테스트 전부 PASS

- [ ] **Step 7: 백엔드 회귀 확인**

```bash
cd /c/workSpace/datingWeb/backend
uv run pytest -q
```

Expected: 전부 PASS

- [ ] **Step 8: 커밋**

```bash
cd /c/workSpace/datingWeb
git add frontend/src/lib/types.ts frontend/src/pages/Admin/RoundTab.tsx frontend/src/pages/Admin/RoundTab.test.tsx
git commit -F - <<'EOF'
feat(frontend): 라운드 카드에 자동 실행 실패 사유 표시

상태 배지는 서버 enum과 1:1을 유지하고, 사유는 별도 줄로 보여준다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

- [ ] **Step 9: PR 생성 전 최종 확인 — 사용자 허락 후에만 push**

```bash
cd /c/workSpace/datingWeb/backend && uv run pytest -q
cd /c/workSpace/datingWeb/frontend && npm run lint && npx tsc --noEmit && npm test
```

전부 통과하면 사용자에게 결과를 보고하고 push·PR 허락을 받는다 (CLAUDE.md: 허락 없이 push 금지).

---

## 전체 검증 기준

| 명령 | 기대 |
|------|------|
| `cd backend && uv run pytest` | 전부 통과 (신규 `test_scheduler.py` 13건 포함) |
| `cd backend && uv run alembic upgrade head` | 오류 없음 |
| `cd frontend && npm run lint` | 경고 0 |
| `cd frontend && npx tsc --noEmit` | 오류 0 |
| `cd frontend && npm test` | 전부 통과 |
| 육안 | 2분 뒤 라운드 생성 → 아무것도 안 누르고 대기 → `완료`로 바뀜 |

## 범위 밖 (스펙과 동일 — 하지 말 것)

- 실패 시 관리자 알림(메일·알림톡)
- 재시도 로직
- `scheduled_at` 필드 분할
- 관리자 화면 자동 갱신 / 프론트 타이머
- 반복 예약(주간 라운드 자동 생성)
- `RoundStatus`에 새 값 추가
