# 대학 가중치 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자가 대학·대학쌍에 보너스/페널티를 걸어 매칭 점수를 조정할 수 있게 한다 (설계 §10 4단계).

**Architecture:** 테이블 하나(`matching_university_weights`)가 단일 대학 규칙과 대학쌍 규칙을 둘 다 담는다 — 단일은 `university_b=''`로 저장한다. 매칭 실행은 시작 시점에 `active` 규칙을 한 번만 읽어 조회표 두 개(단일용·쌍용)로 만들고, 페어마다 순수 함수 `university_bonus`로 합산값을 구해 기존 보정 항에 더한다. 관리자 CRUD는 새 라우터 `/admin/university-weights`, 화면은 관리자 페이지의 네 번째 탭.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic (백엔드), React + Vite + Vitest + Testing Library (프론트)

**Spec:** `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§4.2 대학 가중치, §7 API, §8 화면, §10 4단계)

## Global Constraints

- **매칭 로직 동결의 예외는 §4.2뿐이다.** `scoring.py`·`pairing.py`는 손대지 않는다. `matching.py`는 §4.2 보정을 붙이는 부분만 바꾼다 — 자격(§6.2)·짝짓기(§5)·이월(§4.1)·게임 보정(§4.3)은 그대로 둔다.
- **대학명은 자유 텍스트다.** 대학 목록을 코드에 박지 않는다 (CLAUDE.md 금지 항목, 스펙 §4.2).
- 단일 대학 규칙은 `university_b = ''`(빈 문자열)로 저장한다. **nullable 금지** — SQLite·PostgreSQL 모두 유니크 인덱스에서 NULL을 서로 다른 값으로 취급해 중복 규칙이 들어가고, 합산돼 의도치 않게 큰 값이 된다 (스펙 §4.2 경고).
- 대학쌍은 **사전순 정규화 후 저장**한다. `(연세대, 서울대)`와 `(서울대, 연세대)`는 같은 규칙이다.
- 겹치는 규칙은 **합산**하되 총합은 **±50점**으로 자른다. 이 상한은 대학 가중치 합계에만 적용한다 — 이월·게임 보너스와 합친 총합에는 적용하지 않는다.
- **동일 대학 페어에서 그 대학의 단일 규칙은 한 번만 붙는다** (2026-09-03 확정, Task 1에서 스펙에 명문화).
- `active=false` 규칙은 매칭에서 무시한다. 삭제 대신 끄기가 이벤트 종료 방식이다.
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + 본문 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 브랜치: `feat/university-weights` (`main`에서 딴다 — 3단계 PR #24와 독립이다)
- 백엔드 테스트: `cd backend && .venv/Scripts/python.exe -m pytest`
- 프론트 테스트: `cd frontend && npm test -- --run`, 빌드 `npm run build`
- push·PR은 사용자 허락 후에만.

## 용어

| 이름 | 역할 |
|---|---|
| `MatchingUniversityWeight` | 가중치 규칙 테이블 모델. 단일·쌍 규칙을 한 테이블에 담음 |
| `university_pair_key` | 대학 두 개를 사전순 튜플로 정규화하는 순수 함수 |
| `university_weights` | DB에서 `active` 규칙을 읽어 (단일 조회표, 쌍 조회표) 두 개를 만드는 함수 |
| `university_bonus` | 두 대학과 조회표를 받아 합산·상한 적용된 보너스를 내는 순수 함수 |
| `UNIVERSITY_BONUS_CAP` | 대학 가중치 합계 상한 상수. 값 50 |
| `UNIVERSITY_BONUS` | **삭제 대상**. 2단계에서 자리만 잡아둔 상수 0 |
| `UniversityWeightIn` / `UniversityWeightOut` | CRUD 요청·응답 스키마 |
| `UniversityWeightTab` | 관리자 페이지의 대학 가중치 탭 컴포넌트 |

---

### Task 0: 브랜치 생성

- [ ] **Step 1: main에서 브랜치를 판다**

```bash
git checkout main
git pull
git checkout -b feat/university-weights
```

---

### Task 1: 스펙 §4.2에 중복 합산 규칙을 명문화한다

코드보다 스펙이 먼저다 (CLAUDE.md: 스펙이 진실). §4.2의 규칙 표는 남성 대학 X·여성 대학 Y를
전제로 단일 규칙 두 줄을 적어놨는데, **X == Y일 때 한 번인지 두 번인지**를 말하지 않는다.
2026-09-03 확정: **한 번**.

**Files:**
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§4.2)

- [ ] **Step 1: 규칙 표 아래에 문단을 추가한다**

§4.2의 규칙 표(단일/단일/쌍 세 줄짜리) 바로 아래, `여러 규칙이 겹치면 **합산**하되…`로
시작하는 문단 **앞에** 다음을 넣는다:

```markdown
합산은 **규칙 행 기준**이다. X == Y인 페어(둘 다 같은 대학)에서 그 대학의 단일 규칙은
표의 위 두 줄이 같은 행을 가리키므로 **한 번만** 붙는다 — 사람마다 한 번씩 두 번 붙지 않는다.
관리자가 넣은 숫자가 화면에 보이는 그대로 적용되는 쪽이 예측하기 쉽다 (2026-09-03 확정).
```

- [ ] **Step 2: 커밋**

```bash
git add docs/superpowers/specs/2026-08-21-matching-algorithm-design.md
git commit -F- <<'MSG'
docs(spec): §4.2 동일 대학 페어의 단일 규칙은 한 번만 합산

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 2: 모델 + 마이그레이션

**Files:**
- Modify: `backend/app/models/match.py` (import 보강 + 파일 끝에 모델 추가)
- Create: `backend/alembic/versions/c3f5a1d20b47_university_weights.py`
- Test: `backend/tests/test_university_weight_model.py` (신규)

**Interfaces:**
- Produces: `MatchingUniversityWeight` — 테이블 `matching_university_weights`, 컬럼 `id`, `university_a: str`, `university_b: str`(기본 `''`), `bonus: int`, `active: bool`(기본 `True`), `note: str | None`. 유니크 제약 `(university_a, university_b)` 이름 `uq_university_weights_pair`. Task 3·4가 이 이름들을 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_university_weight_model.py` 생성:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.match import MatchingUniversityWeight
from tests.conftest import TestingSessionLocal


def _add(db, a: str, b: str = "", bonus: int = 10) -> MatchingUniversityWeight:
    weight = MatchingUniversityWeight(university_a=a, university_b=b, bonus=bonus)
    db.add(weight)
    db.commit()
    return weight


def test_defaults(setup_db):
    """단일 규칙은 university_b가 빈 문자열, active는 켜진 상태로 저장된다."""
    db = TestingSessionLocal()
    weight = _add(db, "서울대학교")
    assert weight.university_b == ""
    assert weight.active is True
    assert weight.note is None
    db.close()


def test_duplicate_single_rule_is_rejected(setup_db):
    """같은 대학에 단일 규칙이 두 번 들어가면 합산돼 의도치 않게 커진다 (설계 §4.2)."""
    db = TestingSessionLocal()
    _add(db, "서울대학교")
    with pytest.raises(IntegrityError):
        _add(db, "서울대학교")
    db.rollback()
    db.close()


def test_duplicate_pair_rule_is_rejected(setup_db):
    db = TestingSessionLocal()
    _add(db, "서울대학교", "연세대학교")
    with pytest.raises(IntegrityError):
        _add(db, "서울대학교", "연세대학교")
    db.rollback()
    db.close()


def test_single_and_pair_rules_coexist(setup_db):
    """단일 (A, '') 과 쌍 (A, B) 는 서로 다른 규칙이다."""
    db = TestingSessionLocal()
    _add(db, "서울대학교")
    _add(db, "서울대학교", "연세대학교")
    assert db.query(MatchingUniversityWeight).count() == 2
    db.close()


def test_negative_bonus_is_allowed(setup_db):
    """음수는 페널티다 (설계 §4.2)."""
    db = TestingSessionLocal()
    weight = _add(db, "서울대학교", bonus=-20)
    assert weight.bonus == -20
    db.close()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_university_weight_model.py -v`
Expected: FAIL — `ImportError: cannot import name 'MatchingUniversityWeight'`

- [ ] **Step 3: 모델을 추가한다**

`backend/app/models/match.py` — 최상단 sqlalchemy import 줄에 `Boolean`과 `String`을 넣는다:

```python
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
```

파일 끝에 붙인다:

```python
class MatchingUniversityWeight(Base):
    """대학·대학쌍 가중치 규칙 (설계 §4.2).

    단일 대학 규칙은 university_b=''로 저장한다. nullable로 두면 SQLite·PostgreSQL 모두
    유니크 인덱스에서 NULL을 서로 다른 값으로 봐서 같은 대학에 규칙이 여러 번 들어가고,
    그 값들이 합산돼 매칭 전체가 한쪽으로 쏠린다.

    대학명은 자유 텍스트다 — User.university와 같은 취급이다 (대학 목록은 팀 미결).
    """

    __tablename__ = "matching_university_weights"
    __table_args__ = (
        UniqueConstraint(
            "university_a", "university_b", name="uq_university_weights_pair"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    university_a: Mapped[str] = mapped_column(String(100), nullable=False)
    university_b: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    # 음수 허용 = 페널티
    bonus: Mapped[int] = mapped_column(Integer, nullable=False)
    # 이벤트가 끝나면 삭제 대신 끈다 (설계 §4.2)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

- [ ] **Step 4: 마이그레이션을 만든다**

`backend/alembic/versions/c3f5a1d20b47_university_weights.py` 생성. `down_revision`은
현재 head인 `b4e2a71c9d38`이다 (`alembic/versions/`의 어떤 파일도 이 값을 down_revision으로
갖지 않는 것이 head라는 뜻이다 — 만들기 전에 다시 확인하라):

```python
"""matching university weights

Revision ID: c3f5a1d20b47
Revises: b4e2a71c9d38
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f5a1d20b47'
down_revision: Union[str, Sequence[str], None] = 'b4e2a71c9d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # university_b는 nullable이 아니다 — NULL을 허용하면 유니크가 중복 규칙을 못 막는다
    op.create_table(
        "matching_university_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("university_a", sa.String(length=100), nullable=False),
        sa.Column("university_b", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("bonus", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "university_a", "university_b", name="uq_university_weights_pair"
        ),
    )
    op.create_index(
        op.f("ix_matching_university_weights_id"),
        "matching_university_weights",
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_matching_university_weights_id"),
        table_name="matching_university_weights",
    )
    op.drop_table("matching_university_weights")
```

- [ ] **Step 5: 마이그레이션이 실제로 도는지 확인한다**

테스트 스위트는 `Base.metadata.create_all`을 쓰므로 마이그레이션을 검증하지 **않는다**.
직접 돌려야 한다. 임시 sqlite 파일을 대상으로:

```bash
cd backend
DATABASE_URL="sqlite:///./_migcheck.db" .venv/Scripts/python.exe -m alembic upgrade head
DATABASE_URL="sqlite:///./_migcheck.db" .venv/Scripts/python.exe -m alembic downgrade -1
rm -f _migcheck.db
```

(`alembic/env.py`가 `settings.database_url`을 읽는다. 환경변수 이름이 다르면
`backend/app/config.py`를 읽어 맞는 이름을 쓴다.)
Expected: upgrade·downgrade 둘 다 에러 없이 끝난다. **돌릴 수 없으면 통과했다고 쓰지 말고
왜 못 돌렸는지 보고하라.**

- [ ] **Step 6: 테스트를 돌린다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_university_weight_model.py -v`
Expected: PASS — 5 passed

- [ ] **Step 7: 전체 백엔드 회귀 확인**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: 기존 테스트 전부 PASS

- [ ] **Step 8: 커밋**

```bash
git add backend/app/models/match.py backend/alembic/versions/c3f5a1d20b47_university_weights.py backend/tests/test_university_weight_model.py
git commit -F- <<'MSG'
feat(backend): matching_university_weights 테이블 — 단일·쌍 규칙 한 테이블

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 3: 보너스 계산 + 매칭 통합

**Files:**
- Modify: `backend/app/services/matching.py`
- Test: `backend/tests/test_university_bonus.py` (신규)

**Interfaces:**
- Consumes: Task 2의 `MatchingUniversityWeight`
- Produces:
  - `UNIVERSITY_BONUS_CAP: int = 50`
  - `university_pair_key(a: str, b: str) -> tuple[str, str]` — 사전순 정규화 키. Task 4의 API가 저장 전 정규화에 그대로 쓴다
  - `university_weights(db: Session) -> tuple[dict[str, int], dict[tuple[str, str], int]]` — (단일 조회표, 쌍 조회표)
  - `university_bonus(a: str, b: str, singles, pairs) -> int`
  - `UNIVERSITY_BONUS` 상수는 **삭제된다**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_university_bonus.py` 생성:

```python
from app.models.match import MatchingUniversityWeight
from app.services.matching import (
    UNIVERSITY_BONUS_CAP,
    university_bonus,
    university_pair_key,
    university_weights,
)
from tests.conftest import TestingSessionLocal

SNU = "서울대학교"
YONSEI = "연세대학교"
KOREA = "고려대학교"


def test_pair_key_is_order_free():
    assert university_pair_key(YONSEI, SNU) == university_pair_key(SNU, YONSEI)


def test_no_rules_gives_zero():
    assert university_bonus(SNU, YONSEI, {}, {}) == 0


def test_single_rule_on_one_side():
    assert university_bonus(SNU, YONSEI, {SNU: 30}, {}) == 30


def test_single_rules_on_both_sides_are_summed():
    assert university_bonus(SNU, YONSEI, {SNU: 30, YONSEI: 10}, {}) == 40


def test_same_university_counts_the_single_rule_once():
    """규칙 행 기준 합산 — 사람당 두 번이 아니다 (설계 §4.2, 2026-09-03 확정)."""
    assert university_bonus(SNU, SNU, {SNU: 30}, {}) == 30


def test_pair_rule_applies_regardless_of_order():
    pairs = {university_pair_key(SNU, YONSEI): 25}
    assert university_bonus(SNU, YONSEI, {}, pairs) == 25
    assert university_bonus(YONSEI, SNU, {}, pairs) == 25


def test_single_and_pair_rules_under_cap_are_summed():
    pairs = {university_pair_key(SNU, YONSEI): 5}
    assert university_bonus(SNU, YONSEI, {SNU: 10}, pairs) == 15


def test_single_and_pair_rules_are_summed_then_capped():
    """단일 30 + 쌍 25 = 55지만 상한 50에 걸린다."""
    pairs = {university_pair_key(SNU, YONSEI): 25}
    assert university_bonus(SNU, YONSEI, {SNU: 30}, pairs) == UNIVERSITY_BONUS_CAP


def test_sum_is_capped_at_plus_cap():
    """상한이 없으면 관리자 오타 하나가 매칭 전체를 망친다 (설계 §4.2)."""
    assert university_bonus(SNU, YONSEI, {SNU: 900, YONSEI: 900}, {}) == UNIVERSITY_BONUS_CAP


def test_sum_is_capped_at_minus_cap():
    assert university_bonus(SNU, YONSEI, {SNU: -900}, {}) == -UNIVERSITY_BONUS_CAP


def test_unrelated_universities_are_ignored():
    assert university_bonus(SNU, YONSEI, {KOREA: 30}, {}) == 0


def test_weights_lookup_skips_inactive_rows(setup_db):
    """active=false는 삭제 대신 끄기다 — 조회표에 들어오면 안 된다 (설계 §4.2)."""
    db = TestingSessionLocal()
    db.add(MatchingUniversityWeight(university_a=SNU, university_b="", bonus=30, active=False))
    db.add(MatchingUniversityWeight(university_a=YONSEI, university_b="", bonus=10, active=True))
    db.commit()

    singles, pairs = university_weights(db)

    assert singles == {YONSEI: 10}
    assert pairs == {}
    db.close()


def test_weights_lookup_normalizes_pair_keys(setup_db):
    """저장이 뒤집힌 순서로 들어와 있어도 조회 시 정규화된다."""
    db = TestingSessionLocal()
    db.add(MatchingUniversityWeight(university_a=YONSEI, university_b=SNU, bonus=25))
    db.commit()

    singles, pairs = university_weights(db)

    assert singles == {}
    assert pairs == {university_pair_key(SNU, YONSEI): 25}
    db.close()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_university_bonus.py -v`
Expected: FAIL — `ImportError: cannot import name 'university_bonus'`

- [ ] **Step 3: 함수를 구현한다**

`backend/app/services/matching.py` — 모델 import 줄에 `MatchingUniversityWeight`를 넣는다:

```python
from app.models.match import Match, MatchingUniversityWeight, MatchRound, RoundStatus
```

`UNIVERSITY_BONUS = 0` 상수와 그 위 주석 두 줄을 **지우고** 그 자리에 넣는다:

```python
# 설계 §4.2 — 관리자가 실수로 큰 값을 넣어도 매칭 전체가 망가지지 않게 하는 상한
UNIVERSITY_BONUS_CAP = 50


def university_pair_key(a: str, b: str) -> tuple[str, str]:
    """대학쌍을 순서 무관하게 다루기 위한 사전순 정규화 키 (설계 §4.2)."""
    return (a, b) if a <= b else (b, a)


def university_weights(
    db: Session,
) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    """active 규칙을 단일용·쌍용 조회표 두 개로 나눠 한 번에 읽는다.

    라운드가 도는 중에 관리자가 규칙을 바꿔도 결과가 흔들리지 않도록 실행 시작에
    한 번만 읽는다 (설계 §5.2 결정론성).
    """
    singles: dict[str, int] = {}
    pairs: dict[tuple[str, str], int] = {}
    rows = (
        db.query(MatchingUniversityWeight)
        .filter(MatchingUniversityWeight.active.is_(True))
        .all()
    )
    for row in rows:
        if row.university_b == "":
            singles[row.university_a] = row.bonus
        else:
            pairs[university_pair_key(row.university_a, row.university_b)] = row.bonus
    return singles, pairs


def university_bonus(
    a: str,
    b: str,
    singles: dict[str, int],
    pairs: dict[tuple[str, str], int],
) -> int:
    """겹치는 규칙은 합산하되 ±UNIVERSITY_BONUS_CAP으로 자른다 (설계 §4.2).

    합산은 규칙 행 기준이다 — 같은 대학끼리인 페어에서 그 대학의 단일 규칙은
    한 번만 붙는다.
    """
    total = singles.get(a, 0)
    if b != a:
        total += singles.get(b, 0)
    total += pairs.get(university_pair_key(a, b), 0)
    return max(-UNIVERSITY_BONUS_CAP, min(UNIVERSITY_BONUS_CAP, total))
```

- [ ] **Step 4: 매칭 파이프라인에 연결한다**

`backend/app/services/matching.py`의 `_execute` — `red, ojakgyo_counts = game_signals(db, pool)`
바로 아래에 한 줄 추가:

```python
    singles, pairs = university_weights(db)
```

같은 함수 안의 보너스 합산 줄을 바꾼다:

```python
            bonus = (
                carryover_bonus(man)
                + carryover_bonus(woman)
                + university_bonus(man.university, woman.university, singles, pairs)
            )
```

이 두 곳 말고는 `_execute`를 건드리지 마라.

- [ ] **Step 5: 테스트를 돌린다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_university_bonus.py -v`
Expected: PASS

- [ ] **Step 6: 전체 백엔드 회귀 확인**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: 전부 PASS. `UNIVERSITY_BONUS`를 참조하던 코드·테스트가 있으면 여기서 드러난다 —
있으면 고치지 말고 **보고하라** (계획이 놓친 것이다).

- [ ] **Step 7: 커밋**

```bash
git add backend/app/services/matching.py backend/tests/test_university_bonus.py
git commit -F- <<'MSG'
feat(backend): 대학 가중치를 매칭 점수 보정에 반영 — 합산 후 ±50 상한

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 4: 관리자 CRUD API

**Files:**
- Create: `backend/app/schemas/university_weight.py`
- Create: `backend/app/api/university_weights.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_admin_university_weights.py` (신규)

**Interfaces:**
- Consumes: Task 2의 `MatchingUniversityWeight`, Task 3의 `university_pair_key`
- Produces: `GET|POST /admin/university-weights`, `PUT|DELETE /admin/university-weights/{id}`. 응답 스키마 `UniversityWeightOut` — 필드 `id`, `university_a`, `university_b`, `bonus`, `active`, `note`. Task 5의 프론트 타입이 이 필드명을 그대로 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_admin_university_weights.py` 생성:

```python
from fastapi.testclient import TestClient

SNU = "서울대학교"
YONSEI = "연세대학교"

URL = "/admin/university-weights"


def _create(client: TestClient, **kwargs):
    payload = {"university_a": SNU, "university_b": "", "bonus": 30,
               "active": True, "note": None}
    payload.update(kwargs)
    return client.post(URL, json=payload)


def test_create_single_rule(admin_client: TestClient):
    res = _create(admin_client)
    assert res.status_code == 201
    data = res.json()
    assert data["university_a"] == SNU
    assert data["university_b"] == ""
    assert data["bonus"] == 30
    assert data["active"] is True


def test_pair_is_stored_in_sorted_order(admin_client: TestClient):
    """사전순 정규화 — 순서만 바꾼 중복을 유니크가 잡게 한다 (설계 §4.2)."""
    res = _create(admin_client, university_a=YONSEI, university_b=SNU)
    assert res.status_code == 201
    data = res.json()
    assert (data["university_a"], data["university_b"]) == tuple(sorted([SNU, YONSEI]))


def test_duplicate_single_rule_is_conflict(admin_client: TestClient):
    _create(admin_client)
    assert _create(admin_client).status_code == 409


def test_duplicate_pair_in_swapped_order_is_conflict(admin_client: TestClient):
    _create(admin_client, university_a=SNU, university_b=YONSEI)
    res = _create(admin_client, university_a=YONSEI, university_b=SNU)
    assert res.status_code == 409


def test_blank_university_a_is_rejected(admin_client: TestClient):
    assert _create(admin_client, university_a="   ").status_code == 400


def test_negative_bonus_is_allowed(admin_client: TestClient):
    assert _create(admin_client, bonus=-20).json()["bonus"] == -20


def test_list_returns_all_rules(admin_client: TestClient):
    _create(admin_client)
    _create(admin_client, university_a=YONSEI)
    res = admin_client.get(URL)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_includes_inactive_rules(admin_client: TestClient):
    """끈 규칙도 관리자에겐 보여야 다시 켤 수 있다."""
    _create(admin_client, active=False)
    assert len(admin_client.get(URL).json()) == 1


def test_update_toggles_active(admin_client: TestClient):
    weight_id = _create(admin_client).json()["id"]
    res = admin_client.put(f"{URL}/{weight_id}", json={
        "university_a": SNU, "university_b": "", "bonus": 30,
        "active": False, "note": "이벤트 종료",
    })
    assert res.status_code == 200
    assert res.json()["active"] is False
    assert res.json()["note"] == "이벤트 종료"


def test_update_into_duplicate_is_conflict(admin_client: TestClient):
    _create(admin_client)
    other_id = _create(admin_client, university_a=YONSEI).json()["id"]
    res = admin_client.put(f"{URL}/{other_id}", json={
        "university_a": SNU, "university_b": "", "bonus": 5,
        "active": True, "note": None,
    })
    assert res.status_code == 409


def test_update_missing_is_404(admin_client: TestClient):
    res = admin_client.put(f"{URL}/999", json={
        "university_a": SNU, "university_b": "", "bonus": 5,
        "active": True, "note": None,
    })
    assert res.status_code == 404


def test_delete_removes_rule(admin_client: TestClient):
    weight_id = _create(admin_client).json()["id"]
    assert admin_client.delete(f"{URL}/{weight_id}").status_code == 204
    assert admin_client.get(URL).json() == []


def test_delete_missing_is_404(admin_client: TestClient):
    assert admin_client.delete(f"{URL}/999").status_code == 404


def test_non_admin_is_forbidden(client: TestClient):
    client.post("/auth/register", json={
        "email": "plain@test.com", "password": "password123", "name": "김일반",
        "university": SNU, "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    token = client.post("/auth/login", json={
        "email": "plain@test.com", "password": "password123",
    }).json()["access_token"]
    res = client.get(URL, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
```

⚠️ `test_non_admin_is_forbidden`의 기대 상태코드는 `app/core/deps.py`의 `require_admin`이
실제로 내는 값에 맞춘다. 403이 아니면 **테스트를 고치기 전에 deps 코드를 읽고** 실제 값으로
맞춘 뒤 보고하라.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_admin_university_weights.py -v`
Expected: FAIL — 라우트가 없어서 404

- [ ] **Step 3: 스키마를 만든다**

`backend/app/schemas/university_weight.py` 생성:

```python
from pydantic import BaseModel, ConfigDict, Field


class UniversityWeightIn(BaseModel):
    """생성·수정 공용 (설계 §7).

    university_b는 빈 문자열이 기본이다 — 단일 대학 규칙을 뜻한다.
    """

    university_a: str = Field(min_length=1, max_length=100)
    university_b: str = Field(default="", max_length=100)
    bonus: int  # 음수 허용 = 페널티
    active: bool = True
    note: str | None = Field(default=None, max_length=200)


class UniversityWeightOut(BaseModel):
    id: int
    university_a: str
    university_b: str
    bonus: int
    active: bool
    note: str | None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: 라우터를 만든다**

`backend/app/api/university_weights.py` 생성:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.match import MatchingUniversityWeight
from app.models.user import User
from app.schemas.university_weight import UniversityWeightIn, UniversityWeightOut
from app.services.matching import university_pair_key

admin_router = APIRouter(
    prefix="/admin/university-weights", tags=["university-weights"]
)


def _normalized(payload: UniversityWeightIn) -> tuple[str, str]:
    """저장 직전 정규화. 쌍은 사전순으로 눕혀야 유니크가 순서 바뀐 중복을 잡는다 (설계 §4.2)."""
    a = payload.university_a.strip()
    b = payload.university_b.strip()
    if not a:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="대학명을 입력하세요"
        )
    if b == "":
        return a, ""
    return university_pair_key(a, b)


def _get_weight(db: Session, weight_id: int) -> MatchingUniversityWeight:
    weight = db.get(MatchingUniversityWeight, weight_id)
    if weight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 규칙입니다"
        )
    return weight


def _commit_or_conflict(db: Session) -> None:
    """유니크 위반을 409로 바꾼다 — 같은 대학·같은 쌍의 규칙은 하나뿐이다."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 규칙입니다"
        )


@admin_router.get("", response_model=list[UniversityWeightOut])
def list_weights(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """끈 규칙도 함께 준다 — 관리자가 다시 켤 수 있어야 한다."""
    return (
        db.query(MatchingUniversityWeight)
        .order_by(MatchingUniversityWeight.id.asc())
        .all()
    )


@admin_router.post("", response_model=UniversityWeightOut, status_code=status.HTTP_201_CREATED)
def create_weight(
    payload: UniversityWeightIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university_a, university_b = _normalized(payload)
    weight = MatchingUniversityWeight(
        university_a=university_a,
        university_b=university_b,
        bonus=payload.bonus,
        active=payload.active,
        note=payload.note,
    )
    db.add(weight)
    _commit_or_conflict(db)
    db.refresh(weight)
    return weight


@admin_router.put("/{weight_id}", response_model=UniversityWeightOut)
def update_weight(
    weight_id: int,
    payload: UniversityWeightIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    weight = _get_weight(db, weight_id)
    weight.university_a, weight.university_b = _normalized(payload)
    weight.bonus = payload.bonus
    weight.active = payload.active
    weight.note = payload.note
    _commit_or_conflict(db)
    db.refresh(weight)
    return weight


@admin_router.delete("/{weight_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_weight(
    weight_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    weight = _get_weight(db, weight_id)
    db.delete(weight)
    db.commit()
```

- [ ] **Step 5: 라우터를 등록한다**

`backend/app/api/router.py` — import 줄에 `university_weights`를 넣고(알파벳 순 유지),
파일 끝 `include_router` 목록에 한 줄 추가한다:

```python
router.include_router(university_weights.admin_router)
```

- [ ] **Step 6: 테스트를 돌린다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_admin_university_weights.py -v`
Expected: PASS

- [ ] **Step 7: 전체 백엔드 회귀 확인**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 8: 커밋**

```bash
git add backend/app/schemas/university_weight.py backend/app/api/university_weights.py backend/app/api/router.py backend/tests/test_admin_university_weights.py
git commit -F- <<'MSG'
feat(backend): /admin/university-weights CRUD — 대학 가중치 관리

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 5: 관리자 화면 탭

관리 범위는 **추가 / 목록 / 활성 토글 / 삭제**다. 규칙 내용을 통째로 고치는 화면은 만들지
않는다 — 스펙 §8은 "대학 가중치 관리"만 요구하고, 대학명·점수를 바꾸려면 지우고 다시
넣으면 된다. `PUT`은 토글이 쓴다.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/pages/Admin/UniversityWeightTab.tsx`
- Create: `frontend/src/pages/Admin/UniversityWeightTab.test.tsx`
- Modify: `frontend/src/pages/Admin/Admin.tsx`
- Modify: `frontend/src/pages/Admin/Admin.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `/admin/university-weights` 4개 엔드포인트와 `UniversityWeightOut` 필드
- Produces: `UniversityWeightTab` 컴포넌트, `listUniversityWeights` / `createUniversityWeight` / `updateUniversityWeight` / `deleteUniversityWeight` API 래퍼

- [ ] **Step 1: 타입과 API 래퍼를 추가한다**

`frontend/src/lib/types.ts` — `MatchingRunOut` 아래에 붙인다:

```ts
export interface UniversityWeightOut {
  id: number;
  university_a: string;
  university_b: string;
  bonus: number;
  active: boolean;
  note: string | null;
}

/** 생성·수정 공용 본문. university_b가 빈 문자열이면 단일 대학 규칙. */
export interface UniversityWeightIn {
  university_a: string;
  university_b: string;
  bonus: number;
  active: boolean;
  note: string | null;
}
```

`frontend/src/lib/api.ts` — 최상단 import 목록에 `UniversityWeightOut`, `UniversityWeightIn`을
넣고, `resetMatchRound` 아래에 붙인다:

```ts
export function listUniversityWeights(): Promise<UniversityWeightOut[]> {
  return apiFetch<UniversityWeightOut[]>("/admin/university-weights", {
    method: "GET",
  });
}

export function createUniversityWeight(
  payload: UniversityWeightIn,
): Promise<UniversityWeightOut> {
  return apiFetch<UniversityWeightOut>("/admin/university-weights", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUniversityWeight(
  id: number,
  payload: UniversityWeightIn,
): Promise<UniversityWeightOut> {
  return apiFetch<UniversityWeightOut>(`/admin/university-weights/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteUniversityWeight(id: number): Promise<void> {
  return apiFetch<void>(`/admin/university-weights/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`frontend/src/pages/Admin/UniversityWeightTab.test.tsx` 생성:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UniversityWeightTab from "./UniversityWeightTab";
import * as api from "../../lib/api";

const SINGLE = {
  id: 1, university_a: "서울대학교", university_b: "",
  bonus: 30, active: true, note: "가을 이벤트",
};
const PAIR = {
  id: 2, university_a: "고려대학교", university_b: "연세대학교",
  bonus: -10, active: false, note: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("UniversityWeightTab", () => {
  it("단일 규칙과 쌍 규칙을 구분해 보여준다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE, PAIR]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("서울대학교")).toBeInTheDocument();
    expect(screen.getByText("고려대학교 × 연세대학교")).toBeInTheDocument();
    expect(screen.getByText("+30점")).toBeInTheDocument();
    expect(screen.getByText("-10점")).toBeInTheDocument();
  });

  it("끈 규칙은 중지로 표시된다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([PAIR]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("중지")).toBeInTheDocument();
  });

  it("규칙이 없으면 빈 상태 문구", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("등록된 규칙 없음")).toBeInTheDocument();
  });

  it("추가하면 목록에 붙는다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    const create = vi.spyOn(api, "createUniversityWeight").mockResolvedValue(SINGLE);
    render(<UniversityWeightTab />);
    await screen.findByText("등록된 규칙 없음");

    fireEvent.change(screen.getByLabelText(/대학 A/), { target: { value: "서울대학교" } });
    fireEvent.change(screen.getByLabelText(/보너스/), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => expect(create).toHaveBeenCalledWith({
      university_a: "서울대학교", university_b: "", bonus: 30,
      active: true, note: null,
    }));
    expect(await screen.findByText("서울대학교")).toBeInTheDocument();
  });

  it("대학명이 비면 요청하지 않고 에러를 띄운다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    const create = vi.spyOn(api, "createUniversityWeight");
    render(<UniversityWeightTab />);
    await screen.findByText("등록된 규칙 없음");

    fireEvent.change(screen.getByLabelText(/보너스/), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(await screen.findByText("대학명과 보너스를 확인하세요.")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  it("중지를 누르면 active를 반전해 저장한다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE]);
    const update = vi.spyOn(api, "updateUniversityWeight")
      .mockResolvedValue({ ...SINGLE, active: false });
    render(<UniversityWeightTab />);
    fireEvent.click(await screen.findByRole("button", { name: "중지" }));

    await waitFor(() => expect(update).toHaveBeenCalledWith(1, {
      university_a: "서울대학교", university_b: "", bonus: 30,
      active: false, note: "가을 이벤트",
    }));
    expect(await screen.findByText("중지")).toBeInTheDocument();
  });

  it("삭제하면 목록에서 사라진다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE]);
    const remove = vi.spyOn(api, "deleteUniversityWeight").mockResolvedValue(undefined);
    render(<UniversityWeightTab />);
    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));

    await waitFor(() => expect(remove).toHaveBeenCalledWith(1));
    expect(await screen.findByText("등록된 규칙 없음")).toBeInTheDocument();
  });

  it("목록 조회가 실패하면 에러 문구", async () => {
    vi.spyOn(api, "listUniversityWeights").mockRejectedValue(new Error("boom"));
    render(<UniversityWeightTab />);
    expect(await screen.findByText("목록을 불러오지 못했어요.")).toBeInTheDocument();
  });
});
```

⚠️ `중지` 버튼과 `중지` 배지가 같은 문구라 `getByText("중지")`가 모호해질 수 있다. 위 테스트는
버튼은 `getByRole("button", ...)`으로, 배지는 `findByText`로 잡는데, 그래도 충돌하면
배지 문구를 바꾸지 말고 **테스트 쿼리를 좁혀라**(`within`, `getAllByText` 등). 실패 원인을
보고에 남겨라.

- [ ] **Step 3: 실패를 확인한다**

Run: `cd frontend && npm test -- --run src/pages/Admin/UniversityWeightTab.test.tsx`
Expected: FAIL — 컴포넌트 파일이 없다

- [ ] **Step 4: 탭 컴포넌트를 만든다**

`frontend/src/pages/Admin/UniversityWeightTab.tsx` 생성:

```tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listUniversityWeights,
  createUniversityWeight,
  updateUniversityWeight,
  deleteUniversityWeight,
} from "../../lib/api";
import type { UniversityWeightOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

const INVALID_INPUT = "대학명과 보너스를 확인하세요.";
const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

// 단일 규칙은 대학 하나, 쌍 규칙은 둘을 나란히 보여준다
function ruleLabel(weight: UniversityWeightOut): string {
  return weight.university_b === ""
    ? weight.university_a
    : `${weight.university_a} × ${weight.university_b}`;
}

export default function UniversityWeightTab() {
  const [items, setItems] = useState<UniversityWeightOut[]>([]);
  const [uniA, setUniA] = useState("");
  const [uniB, setUniB] = useState("");
  const [bonus, setBonus] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listUniversityWeights()
      .then((data) => {
        if (active) setItems(data);
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
    const parsed = Number(bonus);
    // 빈 문자열은 Number가 0으로 바꾸므로 따로 걸러야 한다
    if (uniA.trim() === "" || bonus.trim() === "" || !Number.isInteger(parsed)) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      const created = await createUniversityWeight({
        university_a: uniA.trim(),
        university_b: uniB.trim(),
        bonus: parsed,
        active: true,
        note: note.trim() === "" ? null : note.trim(),
      });
      setItems((prev) => [...prev, created]);
      setUniA("");
      setUniB("");
      setBonus("");
      setNote("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleToggle(weight: UniversityWeightOut) {
    setError("");
    try {
      const saved = await updateUniversityWeight(weight.id, {
        university_a: weight.university_a,
        university_b: weight.university_b,
        bonus: weight.bonus,
        active: !weight.active,
        note: weight.note,
      });
      setItems((prev) => prev.map((w) => (w.id === saved.id ? saved : w)));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("이 규칙을 삭제할까요?")) return;
    setError("");
    try {
      await deleteUniversityWeight(id);
      setItems((prev) => prev.filter((w) => w.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.formRow} onSubmit={handleCreate}>
        <label className={styles.formLabel} htmlFor="weight-a">
          대학 A
          <input id="weight-a" value={uniA} onChange={(e) => setUniA(e.target.value)} />
        </label>
        <label className={styles.formLabel} htmlFor="weight-b">
          대학 B (비우면 단일 대학 규칙)
          <input id="weight-b" value={uniB} onChange={(e) => setUniB(e.target.value)} />
        </label>
        <label className={styles.formLabel} htmlFor="weight-bonus">
          보너스 (음수는 페널티)
          <input
            id="weight-bonus"
            type="number"
            value={bonus}
            onChange={(e) => setBonus(e.target.value)}
          />
        </label>
        <label className={styles.formLabel} htmlFor="weight-note">
          메모
          <input id="weight-note" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <Button type="submit">추가</Button>
      </form>

      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>등록된 규칙 없음</p>}

      {items.map((weight) => (
        <div key={weight.id} className={styles.card}>
          <span className={styles.badge}>{weight.active ? "적용" : "중지"}</span>
          <div className={styles.name}>{ruleLabel(weight)}</div>
          <div className={styles.university}>
            {weight.bonus > 0 ? `+${weight.bonus}점` : `${weight.bonus}점`}
          </div>
          {weight.note && <p className={styles.reason}>{weight.note}</p>}
          <div className={styles.actions}>
            <Button onClick={() => handleToggle(weight)}>
              {weight.active ? "중지" : "적용"}
            </Button>
            <Button onClick={() => handleDelete(weight.id)}>삭제</Button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: 관리자 페이지에 탭을 붙인다**

`frontend/src/pages/Admin/Admin.tsx`:

import를 추가한다:

```tsx
import UniversityWeightTab from "./UniversityWeightTab";
```

`Tab` 타입에 값을 추가한다:

```tsx
type Tab = "verification" | "report" | "round" | "weight";
```

`role="tablist"` 안의 라운드 버튼 **뒤에** 버튼 하나를 추가한다 (기존 세 버튼과 같은 모양):

```tsx
        <button
          type="button"
          role="tab"
          id="tab-weight"
          aria-selected={tab === "weight"}
          className={tab === "weight" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("weight")}
        >
          대학 가중치
        </button>
```

그리고 라운드 패널 뒤에 패널을 추가한다:

```tsx
      {tab === "weight" && (
        <div role="tabpanel" aria-labelledby="tab-weight" tabIndex={0}>
          <UniversityWeightTab />
        </div>
      )}
```

- [ ] **Step 6: Admin 탭 전환 테스트를 추가한다**

`frontend/src/pages/Admin/Admin.test.tsx`를 **먼저 읽고**, 라운드 탭을 다루는 기존 케이스와
같은 모양으로 "대학 가중치" 탭 케이스를 하나 추가한다. 기존 파일이 자식 탭을 모킹한다면
`UniversityWeightTab`도 같은 방식으로 모킹한다. 새로운 패턴을 만들지 말고 그 파일의 관례를
그대로 따라라. 검증 내용은 "대학 가중치 탭 버튼을 누르면 그 패널이 보인다" 하나면 된다.

- [ ] **Step 7: 테스트를 돌린다**

Run: `cd frontend && npm test -- --run src/pages/Admin/`
Expected: PASS — 새 8건 + Admin 기존/신규 전부

- [ ] **Step 8: 프론트 전체 검증**

Run: `cd frontend && npm test -- --run` 그리고 `npm run build`
Expected: 전부 PASS, 타입 에러 없음

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Admin
git commit -F- <<'MSG'
feat(frontend): 관리자 대학 가중치 탭 — 추가·활성 토글·삭제

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 6: 스펙 갱신

**Files:**
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§10)
- Add: `docs/superpowers/plans/2026-09-03-university-weights.md` (이 계획 문서, 아직 미추적)

- [ ] **Step 1: 4단계를 완료로 표시한다**

§10 표의 4단계 행을 이렇게 바꾼다:

```markdown
| **4. 대학 가중치** | 테이블 + CRUD API + 관리자 탭 | 2단계 없이는 붙일 데가 없음. ✅ 완료 (2026-09-03) |
```

- [ ] **Step 2: 커밋한다**

```bash
git add docs/superpowers/specs/2026-08-21-matching-algorithm-design.md docs/superpowers/plans/2026-09-03-university-weights.md
git commit -F- <<'MSG'
docs(spec): §10 4단계 완료 표시

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

- [ ] **Step 3: push·PR은 사용자 허락 후에만**

CLAUDE.md 규칙 — 허락 없이 push 금지.

---

## Self-Review

**스펙 커버리지**

| 스펙 항목 | 담당 |
|---|---|
| §4.2 단일·쌍을 한 테이블에 | Task 2 모델 |
| §4.2 `university_b` nullable 금지 | Task 2 모델 + 마이그레이션 + `test_duplicate_single_rule_is_rejected` |
| §4.2 사전순 정규화 | Task 3 `university_pair_key`, Task 4 `_normalized` + `test_pair_is_stored_in_sorted_order`, `test_duplicate_pair_in_swapped_order_is_conflict` |
| §4.2 단일 X·단일 Y·쌍 합산 | Task 3 `university_bonus` + 테스트 4건 |
| §4.2 동일 대학은 한 번만 (2026-09-03 확정) | Task 1 스펙 명문화 + `test_same_university_counts_the_single_rule_once` |
| §4.2 ±50 상한 | `UNIVERSITY_BONUS_CAP` + 상·하한 테스트 2건 |
| §4.2 `active=false` 무시 | `university_weights` 필터 + `test_weights_lookup_skips_inactive_rows` |
| §4.2 대학명 자유 텍스트 | 목록 하드코딩 없음. `String(100)` 자유 입력 |
| §7 CRUD 4개 엔드포인트 | Task 4 |
| §8 관리자 신규 탭 | Task 5 |
| §10 4단계 완료 표시 | Task 6 |

**범위 밖 (이 계획에서 안 한다)**

- 규칙 전체 수정 화면 — 토글만. 내용 변경은 삭제 후 재등록
- 대학 목록 드롭다운 — 대학 목록은 팀 미결, 자유 텍스트 유지
- 카카오 알림톡, 스케줄러 자동 실행
