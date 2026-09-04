# 가입 데이터 정합성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대학명을 관리자 관리 목록에서만 고르게 하고, 연락처 없는 유저를 매칭에서 빼고, 학번으로 동명이인 지목을 구분한다.

**Architecture:** 대학명은 지금처럼 문자열로 저장하되(FK 정규화 아님), 값이 들어오는 쓰기 4경로에서 `universities` 목록과 대조 검증한다. 검증은 `app/services/universities.py` 한 곳에 모으고 API 계층이 422로 변환한다. 학번은 선택 입력이며 `_identity_resolver`에서 후보를 좁히는 추가 필터로만 쓴다.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · pytest / React(Vite) · TypeScript · vitest

**Spec:** `docs/superpowers/specs/2026-09-04-signup-data-integrity-design.md`

## Global Constraints

- 대학명 저장은 **문자열 유지**. FK 정규화하지 않는다 (스펙 §3.1)
- 대학 **이름 변경(rename) 기능을 만들지 않는다** (스펙 §4.1)
- 신규 쓰기는 **활성 대학만** 허용. 비활성 대학으로 이미 가입한 유저는 유지 (스펙 §5.3)
- `matching_university_weights.university_b == ""` 는 단일 대학 규칙 관례 — **검증에서 건너뛴다** (스펙 §5.2)
- 지목 테이블 학번은 **NOT NULL, 0 = 미입력**. `users.admission_year`는 **nullable** (스펙 §4.2)
- 학번 허용 범위: `2000 <= admission_year <= 현재 연도 + 1` (스펙 §4.2)
- 서비스 계층은 HTTP를 모른다. 도메인 예외를 API 계층에서 HTTPException으로 바꾼다 (스펙 §5.1)
- 마이그레이션은 **리비전 1개**에 몰아넣고 Task 1에서 적용한다 (스펙 §4.3)
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 신고(`reports`)는 검증 경로가 **아니다**. `test_reports.py`의 자유 텍스트 대학명은 그대로 둔다

---

## File Structure

**신규 (backend)**

| 파일 | 책임 |
|---|---|
| `backend/app/models/university.py` | `University` 모델 |
| `backend/app/schemas/university.py` | `UniversityIn` · `UniversityActiveUpdate` · `UniversityOut` |
| `backend/app/schemas/admission.py` | 학번 범위 검증 함수 (가입·지목 스키마가 공유) |
| `backend/app/services/universities.py` | `known_names` · `UnknownUniversity` · `require_known` |
| `backend/app/api/universities.py` | 공개 `GET /universities` + 관리자 CRUD + `validate_universities` 헬퍼 |
| `backend/alembic/versions/<rev>_universities_and_admission_year.py` | 리비전 1개 |
| `backend/tests/test_university_model.py` | 모델·제약 |
| `backend/tests/test_university_service.py` | `known_names` · `require_known` |
| `backend/tests/test_universities.py` | 공개 목록 API |
| `backend/tests/test_admin_universities.py` | 관리자 CRUD |
| `backend/tests/test_university_validation.py` | 쓰기 4경로 검증 |
| `backend/tests/test_contact_required.py` | 연락처 3중 방어 |
| `backend/tests/test_identity_resolver.py` | 학번 판정 |
| `backend/tests/test_migration_signup_integrity.py` | upgrade/downgrade + 드리프트 |

**수정 (backend)**

| 파일 | 변경 |
|---|---|
| `backend/app/models/__init__.py` | `University` re-export (CLAUDE.md 규칙) |
| `backend/app/models/user.py` | `admission_year` 컬럼 |
| `backend/app/models/game.py` | 학번 컬럼 3개 + 유니크 제약 2개 |
| `backend/app/api/router.py` | `universities.router` · `universities.admin_router` 등록 |
| `backend/app/schemas/auth.py` | `RegisterRequest` 학번 + 연락처 3개 + 최소 1개 |
| `backend/app/schemas/game.py` | 지목 스키마 학번 |
| `backend/app/api/auth.py` | 대학 검증 |
| `backend/app/api/game.py` | 대학 검증 + 학번 저장 |
| `backend/app/api/university_weights.py` | 대학 검증 |
| `backend/app/api/me.py` | 프로필 연락처 최소 1개 |
| `backend/app/services/matching.py` | `eligible_users` 연락처 조건, `_identity_resolver` 학번 |
| `backend/tests/conftest.py` | 기준 대학 시드 |

**신규 (frontend)**

| 파일 | 책임 |
|---|---|
| `frontend/src/components/UniversitySelect/UniversitySelect.tsx` | 4곳이 공유하는 대학 셀렉트 |
| `frontend/src/components/UniversitySelect/UniversitySelect.test.tsx` | |
| `frontend/src/pages/Admin/UniversityTab.tsx` | 관리자 5번째 탭 |
| `frontend/src/pages/Admin/UniversityTab.test.tsx` | |

**수정 (frontend)**: `lib/types.ts` · `lib/api.ts` · `pages/Register/Register.tsx` · `pages/Game/OjakgyoTab.tsx` · `pages/Game/RedThreadTab.tsx` · `pages/Admin/UniversityWeightTab.tsx` · `pages/Admin/Admin.tsx` · `pages/MyPage/MyPage.tsx` + 각 테스트

---

# 1단계 — 대학 목록 기반

## Task 1: University 모델 + 마이그레이션

스키마 변경을 여기서 전부 끝낸다. 학번 컬럼은 3단계에서 쓰지만 지목 테이블을 두 번 고치지 않으려고 지금 넣는다 (스펙 §4.3).

**Files:**
- Create: `backend/app/models/university.py`
- Create: `backend/tests/test_university_model.py`
- Create: `backend/alembic/versions/<생성된 rev>_universities_and_admission_year.py`
- Create: `backend/tests/test_migration_signup_integrity.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/game.py`

**Interfaces:**
- Produces: `University(id, name, active, created_at)` · `User.admission_year: int | None` · `Ojakgyo.person_a_admission_year: int` · `Ojakgyo.person_b_admission_year: int` · `RedThread.target_admission_year: int`

- [ ] **Step 1: 실패하는 모델 테스트를 쓴다**

`backend/tests/test_university_model.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from tests.conftest import TestingSessionLocal
from app.models.university import University
from app.models.game import Ojakgyo, RedThread
from app.models.user import User


def test_name_is_unique():
    db = TestingSessionLocal()
    db.add(University(name="서울대학교"))
    db.commit()
    db.add(University(name="서울대학교"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_active_defaults_true():
    db = TestingSessionLocal()
    uni = University(name="한양대학교")
    db.add(uni)
    db.commit()
    assert uni.active is True
    db.close()


def test_user_admission_year_is_optional():
    """모르는 사람이 있어 선택 입력이다 (설계 §4.2)."""
    db = TestingSessionLocal()
    user = User(
        email="noyear@test.com", password_hash="x", name="김노학번",
        university="서울대학교", gender="female",
    )
    db.add(user)
    db.commit()
    assert user.admission_year is None
    db.close()


def _recommender(db) -> int:
    """지목 행의 recommender_id가 가리킬 유저. SQLite는 기본적으로 FK를 강제하지
    않지만, 실재하는 id를 쓰는 편이 테스트 의도가 분명하다."""
    user = User(
        email="rec@test.com", password_hash="x", name="지목자",
        university="서울대학교", gender="male",
    )
    db.add(user)
    db.commit()
    return user.id


def test_ojakgyo_same_pair_with_different_admission_year_is_allowed():
    """동명이인 두 명을 각각 지목할 수 있어야 한다 (설계 §4.2)."""
    db = TestingSessionLocal()
    common = dict(
        recommender_id=_recommender(db),
        person_a_name="김철수", person_a_university="서울대학교",
        person_b_name="이영희", person_b_university="연세대학교",
        person_b_admission_year=0,
    )
    db.add(Ojakgyo(person_a_admission_year=2021, **common))
    db.add(Ojakgyo(person_a_admission_year=2022, **common))
    db.commit()
    assert db.query(Ojakgyo).count() == 2
    db.close()


def test_ojakgyo_identical_rows_still_conflict():
    """학번까지 같으면 여전히 중복이다 — 0 센티넬이 NULL이었다면 이게 통과해버린다."""
    db = TestingSessionLocal()
    common = dict(
        recommender_id=_recommender(db),
        person_a_name="김철수", person_a_university="서울대학교", person_a_admission_year=0,
        person_b_name="이영희", person_b_university="연세대학교", person_b_admission_year=0,
    )
    db.add(Ojakgyo(**common))
    db.commit()
    db.add(Ojakgyo(**common))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_red_thread_same_target_different_year_is_allowed():
    db = TestingSessionLocal()
    user_id = _recommender(db)
    db.add(RedThread(user_id=user_id, target_name="박민수", target_university="고려대학교", target_admission_year=2020))
    db.add(RedThread(user_id=user_id, target_name="박민수", target_university="고려대학교", target_admission_year=2023))
    db.commit()
    assert db.query(RedThread).count() == 2
    db.close()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_university_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.university'`

- [ ] **Step 3: University 모델을 만든다**

`backend/app/models/university.py`:

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class University(Base):
    """가입·지목·가중치 규칙에서 고를 수 있는 대학 목록 (설계 §4.1).

    이름 변경 기능은 없다. 대학명은 users·ojakgyo·red_threads·
    matching_university_weights에 문자열로 복사 저장되므로, 여기서 이름을 고치면
    그 행들이 전부 고아가 된다 — 지금 고치려는 그 버그가 그대로 재발한다.
    """

    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    # 삭제 대신 끈다 — 이미 그 대학으로 가입한 유저는 그대로 매칭된다 (설계 §5.3)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 4: `models/__init__.py`에 re-export한다**

CLAUDE.md 백엔드 규칙: 모델 추가 시 re-export 필수.

```python
from app.models.university import University
```

`__all__` 목록에도 `"University",`를 추가한다.

- [ ] **Step 5: `users.admission_year`를 추가한다**

`backend/app/models/user.py`, `matching_paused` 위 줄에:

```python
    # 입학년도 4자리. 선택 입력 — 상대 학번을 모를 수 있어 필수로 두지 않는다 (설계 §4.2)
    admission_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 6: 지목 테이블에 학번 컬럼과 유니크 제약을 넣는다**

`backend/app/models/game.py` — `Ojakgyo`:

```python
    __table_args__ = (
        UniqueConstraint(
            "recommender_id",
            "person_a_name", "person_a_university", "person_a_admission_year",
            "person_b_name", "person_b_university", "person_b_admission_year",
            name="uq_ojakgyo_recommender_pair",
        ),
    )
```

컬럼 2개를 `person_b_university` 아래에 추가한다:

```python
    # 0 = 미입력. nullable로 두면 유니크 인덱스가 NULL을 서로 다른 값으로 봐서
    # 같은 사람을 학번 없이 몇 번이고 중복 지목할 수 있게 된다 (설계 §4.2)
    person_a_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    person_b_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
```

`RedThread`도 같은 방식으로:

```python
    __table_args__ = (
        UniqueConstraint(
            "user_id", "target_name", "target_university", "target_admission_year",
            name="uq_red_thread_user_target",
        ),
    )
```

```python
    # 0 = 미입력 (설계 §4.2)
    target_admission_year: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
```

- [ ] **Step 7: 모델 테스트가 통과하는지 본다**

Run: `cd backend && uv run pytest tests/test_university_model.py -v`
Expected: 6 passed

- [ ] **Step 8: 마이그레이션을 만든다**

Run: `cd backend && uv run alembic revision -m "universities and admission year"`

생성된 파일의 `down_revision`이 `"c3f5a1d20b47"`인지 확인하고, 본문을 아래로 채운다.
**autogenerate를 쓰지 않는다** — SQLite는 제약 변경에 `batch_alter_table`이 필요한데 autogenerate가 이를 만들어주지 않는다.

```python
import sqlalchemy as sa
from alembic import op

revision = "<생성된 값 그대로 둔다>"
down_revision = "c3f5a1d20b47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_universities_id"), "universities", ["id"])
    op.create_index(op.f("ix_universities_name"), "universities", ["name"], unique=True)

    op.add_column("users", sa.Column("admission_year", sa.Integer(), nullable=True))

    with op.batch_alter_table("ojakgyo", schema=None) as batch:
        batch.add_column(sa.Column(
            "person_a_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.add_column(sa.Column(
            "person_b_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.drop_constraint("uq_ojakgyo_recommender_pair", type_="unique")
        batch.create_unique_constraint(
            "uq_ojakgyo_recommender_pair",
            [
                "recommender_id",
                "person_a_name", "person_a_university", "person_a_admission_year",
                "person_b_name", "person_b_university", "person_b_admission_year",
            ],
        )

    with op.batch_alter_table("red_threads", schema=None) as batch:
        batch.add_column(sa.Column(
            "target_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.drop_constraint("uq_red_thread_user_target", type_="unique")
        batch.create_unique_constraint(
            "uq_red_thread_user_target",
            ["user_id", "target_name", "target_university", "target_admission_year"],
        )


def downgrade() -> None:
    with op.batch_alter_table("red_threads", schema=None) as batch:
        batch.drop_constraint("uq_red_thread_user_target", type_="unique")
        batch.create_unique_constraint(
            "uq_red_thread_user_target",
            ["user_id", "target_name", "target_university"],
        )
        batch.drop_column("target_admission_year")

    with op.batch_alter_table("ojakgyo", schema=None) as batch:
        batch.drop_constraint("uq_ojakgyo_recommender_pair", type_="unique")
        batch.create_unique_constraint(
            "uq_ojakgyo_recommender_pair",
            [
                "recommender_id",
                "person_a_name", "person_a_university",
                "person_b_name", "person_b_university",
            ],
        )
        batch.drop_column("person_b_admission_year")
        batch.drop_column("person_a_admission_year")

    op.drop_column("users", "admission_year")
    op.drop_index(op.f("ix_universities_name"), table_name="universities")
    op.drop_index(op.f("ix_universities_id"), table_name="universities")
    op.drop_table("universities")
```

- [ ] **Step 9: 마이그레이션 테스트를 쓴다**

테스트 스위트는 `Base.metadata.create_all`로 스키마를 만들어 **마이그레이션을 타지 않는다.**
그래서 별도로 실측한다 (PR #25가 쓴 방식).

`backend/tests/test_migration_signup_integrity.py`:

```python
import pathlib
import tempfile

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.database import Base
import app.models  # noqa: F401  — 모든 모델을 메타데이터에 등록시킨다

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_then_downgrade_runs_clean():
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{tmp}/mig.db"
        cfg = _config(url)
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")


def test_migrations_match_models():
    """모델↔마이그레이션 드리프트 0. 하나라도 어긋나면 diff가 비지 않는다."""
    with tempfile.TemporaryDirectory() as tmp:
        url = f"sqlite:///{tmp}/mig.db"
        command.upgrade(_config(url), "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            diff = compare_metadata(
                MigrationContext.configure(conn), Base.metadata
            )
        assert diff == [], diff
```

- [ ] **Step 10: 마이그레이션 테스트를 돌린다**

Run: `cd backend && uv run pytest tests/test_migration_signup_integrity.py -v`
Expected: 2 passed. `test_migrations_match_models`가 실패하면 diff 내용대로 마이그레이션을 모델에 맞춘다.

- [ ] **Step 11: 개발 DB에 적용한다**

Run: `cd backend && uv run alembic upgrade head`
Expected: 이전에 2개 밀려 있던 리비전까지 함께 올라간다. `uv run alembic current`가 새 head를 가리키는지 확인한다.

- [ ] **Step 12: 전체 테스트를 돌린다**

Run: `cd backend && uv run pytest -q`
Expected: 341 + 8 = 349 passed

- [ ] **Step 13: 커밋**

```bash
git add backend/app/models backend/alembic/versions backend/tests/test_university_model.py backend/tests/test_migration_signup_integrity.py
git commit -m "feat(backend): universities 테이블 + 학번 컬럼 — 스키마와 마이그레이션"
```

---

## Task 2: 대학명 검증 서비스

**Files:**
- Create: `backend/app/services/universities.py`
- Create: `backend/tests/test_university_service.py`

**Interfaces:**
- Consumes: `University` (Task 1)
- Produces: `known_names(db) -> set[str]` · `UnknownUniversity(Exception)` with `.name` · `require_known(db, *names) -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_university_service.py`:

```python
import pytest

from tests.conftest import TestingSessionLocal
from app.models.university import University
from app.services.universities import (
    UnknownUniversity,
    known_names,
    require_known,
)


def _seed(**kwargs):
    db = TestingSessionLocal()
    db.add(University(**kwargs))
    db.commit()
    db.close()


def test_known_names_returns_active_only():
    _seed(name="활성대학교", active=True)
    _seed(name="비활성대학교", active=False)
    db = TestingSessionLocal()
    names = known_names(db)
    db.close()
    assert "활성대학교" in names
    assert "비활성대학교" not in names


def test_require_known_passes_for_active():
    _seed(name="활성대학교")
    db = TestingSessionLocal()
    require_known(db, "활성대학교")  # 예외 없이 통과
    db.close()


def test_require_known_rejects_inactive():
    """비활성 대학은 신규 입력에 못 쓴다 (설계 §5.3)."""
    _seed(name="비활성대학교", active=False)
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity) as exc:
        require_known(db, "비활성대학교")
    db.close()
    assert exc.value.name == "비활성대학교"


def test_require_known_rejects_unlisted():
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity):
        require_known(db, "없는대학교")
    db.close()


def test_require_known_checks_every_name():
    _seed(name="활성대학교")
    db = TestingSessionLocal()
    with pytest.raises(UnknownUniversity) as exc:
        require_known(db, "활성대학교", "없는대학교")
    db.close()
    assert exc.value.name == "없는대학교"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_university_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.universities'`

- [ ] **Step 3: 서비스를 구현한다**

`backend/app/services/universities.py`:

```python
from sqlalchemy.orm import Session

from app.models.university import University


class UnknownUniversity(Exception):
    """목록에 없는 대학명. API 계층이 422로 바꾼다 (설계 §5.1).

    서비스는 HTTP를 모른다 (매칭 설계 §2.1).
    """

    def __init__(self, name: str):
        self.name = name
        super().__init__(name)


def known_names(db: Session) -> set[str]:
    """신규 입력에 쓸 수 있는 활성 대학명 (설계 §5.3)."""
    rows = db.query(University.name).filter(University.active.is_(True)).all()
    return {name for (name,) in rows}


def require_known(db: Session, *names: str) -> None:
    """하나라도 목록 밖이면 UnknownUniversity.

    호출자가 strip한 값을 넘긴다 — 여기서 정규화하지 않는다. 저장되는 값과
    검증되는 값이 반드시 같아야 하기 때문이다.
    """
    allowed = known_names(db)
    for name in names:
        if name not in allowed:
            raise UnknownUniversity(name)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_university_service.py -v`
Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/universities.py backend/tests/test_university_service.py
git commit -m "feat(backend): 대학명 검증 서비스 — known_names, require_known"
```

---

## Task 3: 대학 목록 API + 테스트 시드

`conftest.py`가 `"university": "서울대학교"`로 가입하고, 백엔드 테스트 16개 파일이 대학명 리터럴을 쓴다. Task 4에서 가입 검증을 켜면 이들이 전부 422로 깨진다. **시드를 여기서 먼저 넣는다.**

**Files:**
- Create: `backend/app/schemas/university.py`
- Create: `backend/app/api/universities.py`
- Create: `backend/tests/test_universities.py`
- Create: `backend/tests/test_admin_universities.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `known_names` · `UnknownUniversity` · `require_known` (Task 2)
- Produces: `GET /universities` · `GET|POST /admin/universities` · `PATCH|DELETE /admin/universities/{id}` · `validate_universities(db, *names) -> None` (HTTPException 422를 던지는 API 계층 헬퍼)

- [ ] **Step 1: 실패하는 API 테스트를 쓴다**

`backend/tests/test_universities.py`:

```python
from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.university import University


def _seed(name: str, active: bool = True):
    db = TestingSessionLocal()
    db.add(University(name=name, active=active))
    db.commit()
    db.close()


def test_public_list_needs_no_auth(client: TestClient):
    """가입 폼이 로그인 전에 호출한다 (설계 §8)."""
    _seed("한양대학교")
    res = client.get("/universities")
    assert res.status_code == 200
    assert "한양대학교" in [u["name"] for u in res.json()]


def test_public_list_hides_inactive(client: TestClient):
    _seed("꺼진대학교", active=False)
    res = client.get("/universities")
    assert "꺼진대학교" not in [u["name"] for u in res.json()]


def test_public_list_is_sorted_by_name(client: TestClient):
    names = [u["name"] for u in client.get("/universities").json()]
    assert names == sorted(names)
```

`backend/tests/test_admin_universities.py`:

```python
from fastapi.testclient import TestClient

URL = "/admin/universities"


def test_create(admin_client: TestClient):
    res = admin_client.post(URL, json={"name": "한양대학교"})
    assert res.status_code == 201
    assert res.json()["name"] == "한양대학교"
    assert res.json()["active"] is True


def test_create_trims_whitespace(admin_client: TestClient):
    res = admin_client.post(URL, json={"name": "  중앙대학교  "})
    assert res.status_code == 201
    assert res.json()["name"] == "중앙대학교"


def test_duplicate_name_is_conflict(admin_client: TestClient):
    admin_client.post(URL, json={"name": "한양대학교"})
    assert admin_client.post(URL, json={"name": "한양대학교"}).status_code == 409


def test_admin_list_includes_inactive(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    admin_client.patch(f"{URL}/{created['id']}", json={"active": False})
    names = [u["name"] for u in admin_client.get(URL).json()]
    assert "한양대학교" in names


def test_toggle_active(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    res = admin_client.patch(f"{URL}/{created['id']}", json={"active": False})
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_delete_unreferenced(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    assert admin_client.delete(f"{URL}/{created['id']}").status_code == 204


def test_delete_referenced_by_user_is_conflict(admin_client: TestClient):
    """admin_client 자신이 서울대학교로 가입돼 있다 (conftest 시드)."""
    listed = admin_client.get(URL).json()
    snu = next(u for u in listed if u["name"] == "서울대학교")
    res = admin_client.delete(f"{URL}/{snu['id']}")
    assert res.status_code == 409


def test_delete_missing_is_404(admin_client: TestClient):
    assert admin_client.delete(f"{URL}/99999").status_code == 404


def test_requires_admin(client: TestClient):
    assert client.get(URL).status_code in (401, 403)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_universities.py tests/test_admin_universities.py -v`
Expected: FAIL — 404 (라우터 없음)

- [ ] **Step 3: 스키마를 만든다**

`backend/app/schemas/university.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UniversityIn(BaseModel):
    """추가 전용. 이름 변경은 지원하지 않는다 (설계 §4.1)."""

    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("대학명을 입력하세요")
        return stripped


class UniversityActiveUpdate(BaseModel):
    active: bool


class UniversityOut(BaseModel):
    id: int
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: API를 만든다**

`backend/app/api/universities.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.game import Ojakgyo, RedThread
from app.models.match import MatchingUniversityWeight
from app.models.university import University
from app.models.user import User
from app.schemas.university import (
    UniversityActiveUpdate,
    UniversityIn,
    UniversityOut,
)
from app.services.universities import UnknownUniversity, require_known

router = APIRouter(prefix="/universities", tags=["universities"])
admin_router = APIRouter(prefix="/admin/universities", tags=["universities"])


def validate_universities(db: Session, *names: str) -> None:
    """쓰기 경로 공용 — 도메인 예외를 HTTP 422로 바꾼다 (설계 §5.1).

    서비스가 HTTP를 모르므로 변환은 API 계층인 여기서 한 번만 한다.
    """
    try:
        require_known(db, *names)
    except UnknownUniversity as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"목록에 없는 대학입니다: {exc.name}",
        )


# 삭제 전에 훑을 참조 지점. 하나라도 걸리면 끄기만 허용한다 (설계 §4.1)
_REFERENCES = (
    User.university,
    Ojakgyo.person_a_university,
    Ojakgyo.person_b_university,
    RedThread.target_university,
    MatchingUniversityWeight.university_a,
    MatchingUniversityWeight.university_b,
)


def _is_referenced(db: Session, name: str) -> bool:
    return any(
        db.query(column).filter(column == name).first() is not None
        for column in _REFERENCES
    )


def _get(db: Session, university_id: int) -> University:
    university = db.get(University, university_id)
    if university is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="존재하지 않는 대학입니다"
        )
    return university


@router.get("", response_model=list[UniversityOut])
def list_active(db: Session = Depends(get_db)):
    """비인증 공개 — 가입 폼이 로그인 전에 호출한다 (설계 §8)."""
    return (
        db.query(University)
        .filter(University.active.is_(True))
        .order_by(University.name.asc())
        .all()
    )


@admin_router.get("", response_model=list[UniversityOut])
def list_all(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """끈 대학도 함께 준다 — 관리자가 다시 켤 수 있어야 한다."""
    return db.query(University).order_by(University.name.asc()).all()


@admin_router.post("", response_model=UniversityOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: UniversityIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university = University(name=payload.name)
    db.add(university)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 등록된 대학입니다"
        )
    db.refresh(university)
    return university


@admin_router.patch("/{university_id}", response_model=UniversityOut)
def set_active(
    university_id: int,
    payload: UniversityActiveUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """활성 토글만. 이름은 바꿀 수 없다 (설계 §4.1)."""
    university = _get(db, university_id)
    university.active = payload.active
    db.commit()
    db.refresh(university)
    return university


@admin_router.delete("/{university_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    university_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    university = _get(db, university_id)
    if _is_referenced(db, university.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 대학입니다. 삭제 대신 비활성으로 끄세요",
        )
    db.delete(university)
    db.commit()
```

- [ ] **Step 5: 라우터를 등록한다**

`backend/app/api/router.py` — import 줄에 `universities`를 넣고:

```python
router.include_router(universities.router)
router.include_router(universities.admin_router)
```

- [ ] **Step 6: conftest에 기준 대학을 시드한다**

기존 테스트가 쓰는 대학명 전부를 넣는다. `A대`·`B대`·`C대`는 `test_game.py`가 쓰는 자리표시자다.

`backend/tests/conftest.py` — `setup_db` 픽스처를 아래로 교체한다:

```python
# 기존 테스트가 쓰는 대학명 전부. Task 4에서 가입 검증이 켜지면 이 시드가 없는 한
# 유저를 만드는 모든 테스트가 422로 깨진다.
BASELINE_UNIVERSITIES = [
    "서울대학교", "연세대학교", "고려대학교", "성균관대학교",
    "A대", "B대", "C대",
]


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    from app.models.university import University

    db = TestingSessionLocal()
    db.add_all([University(name=name) for name in BASELINE_UNIVERSITIES])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
```

- [ ] **Step 7: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_universities.py tests/test_admin_universities.py -v`
Expected: 12 passed

- [ ] **Step 8: 전체 테스트를 돌린다**

Run: `cd backend && uv run pytest -q`
Expected: 349 + 12 = 361 passed. 시드 때문에 깨지는 기존 테스트가 있으면 여기서 드러난다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/schemas/university.py backend/app/api/universities.py backend/app/api/router.py backend/tests/conftest.py backend/tests/test_universities.py backend/tests/test_admin_universities.py
git commit -m "feat(backend): 대학 목록 API — 공개 조회 + 관리자 CRUD"
```

---

## Task 4: 쓰기 4경로에 검증을 건다

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/game.py`
- Modify: `backend/app/api/university_weights.py`
- Create: `backend/tests/test_university_validation.py`

**Interfaces:**
- Consumes: `validate_universities(db, *names)` (Task 3)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_university_validation.py`:

```python
from fastapi.testclient import TestClient

UNLISTED = "없는대학교"


def _register(client: TestClient, university: str, email: str = "v@test.com"):
    return client.post("/auth/register", json={
        "email": email, "password": "password123", "name": "검증",
        "university": university, "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })


def _auth(client: TestClient, email: str) -> dict:
    _register(client, "서울대학교", email)
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_rejects_unlisted_university(client: TestClient):
    res = _register(client, UNLISTED)
    assert res.status_code == 422


def test_register_accepts_listed_university(client: TestClient):
    assert _register(client, "서울대학교").status_code == 201


def test_register_rejects_inactive_university(client: TestClient, admin_client: TestClient):
    """끈 대학으로는 새로 가입할 수 없다 (설계 §5.3)."""
    listed = admin_client.get("/admin/universities").json()
    korea = next(u for u in listed if u["name"] == "고려대학교")
    admin_client.patch(f"/admin/universities/{korea['id']}", json={"active": False})
    assert _register(client, "고려대학교", "inactive@test.com").status_code == 422


def test_ojakgyo_rejects_unlisted_university(client: TestClient):
    headers = _auth(client, "oj@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가", "person_a_university": UNLISTED,
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_red_thread_rejects_unlisted_university(client: TestClient):
    headers = _auth(client, "rt@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "갑", "target_university": UNLISTED},
    ]}, headers=headers)
    assert res.status_code == 422


def test_weight_rejects_unlisted_university(admin_client: TestClient):
    res = admin_client.post("/admin/university-weights", json={
        "university_a": UNLISTED, "university_b": "", "bonus": 10,
        "active": True, "note": None,
    })
    assert res.status_code == 422


def test_weight_single_rule_keeps_empty_university_b(admin_client: TestClient):
    """빈 university_b는 단일 대학 규칙 관례라 검증을 건너뛴다 (설계 §5.2)."""
    res = admin_client.post("/admin/university-weights", json={
        "university_a": "서울대학교", "university_b": "", "bonus": 10,
        "active": True, "note": None,
    })
    assert res.status_code == 201
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_university_validation.py -v`
Expected: 검증 관련 5개 FAIL (201/200을 받는다), 통과 케이스 2개는 PASS

- [ ] **Step 3: 회원가입에 검증을 건다**

`backend/app/api/auth.py`의 register 핸들러에서, 유저를 만들기 **전에**:

```python
from app.api.universities import validate_universities

    validate_universities(db, payload.university)
```

`RegisterRequest`가 이미 `university`를 strip하므로 (`not_blank` validator) 추가 정규화는 하지 않는다.

- [ ] **Step 4: 게임 지목 2경로에 검증을 건다**

`backend/app/api/game.py` — `create_ojakgyo`에서 `_normalize_pair` 호출 뒤, 저장 전에:

```python
from app.api.universities import validate_universities

    validate_universities(db, a_univ, b_univ)
```

`submit_red_thread`에서는 targets를 순회하기 전에:

```python
    validate_universities(db, *[t.target_university.strip() for t in payload.targets])
```

**strip한 값으로 검증하고 strip한 값으로 저장해야 한다** — 검증한 값과 저장한 값이 다르면 검증이 무의미해진다. 기존 코드가 이미 strip해서 저장하는지 확인하고, 안 하면 맞춘다.

- [ ] **Step 5: 가중치 규칙에 검증을 건다**

`backend/app/api/university_weights.py` — `create_weight`와 `update_weight` 둘 다, `_normalized()` 결과를 받은 직후:

```python
from app.api.universities import validate_universities

    university_a, university_b = _normalized(payload)
    # 빈 university_b는 단일 대학 규칙 관례다 — 검증 대상이 아니다 (설계 §5.2)
    validate_universities(db, *[n for n in (university_a, university_b) if n])
```

- [ ] **Step 6: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_university_validation.py -v`
Expected: 7 passed

- [ ] **Step 7: 전체 테스트를 돌린다**

Run: `cd backend && uv run pytest -q`
Expected: 361 + 7 = 368 passed. 실패가 나오면 대부분 시드에 없는 대학명을 쓰는 테스트다 — 그 테스트의 대학명을 `BASELINE_UNIVERSITIES`의 값으로 바꾼다. `test_reports.py`는 검증 경로가 아니므로 손대지 않는다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/api backend/tests/test_university_validation.py
git commit -m "fix(backend): 대학명이 들어오는 쓰기 4경로에 목록 검증 — 오타가 조용히 통과하던 문제"
```

---

## Task 5: 프론트 타입 · API · 공용 셀렉트

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/components/UniversitySelect/UniversitySelect.tsx`
- Create: `frontend/src/components/UniversitySelect/UniversitySelect.test.tsx`

**Interfaces:**
- Produces: `UniversityOut` 타입 · `listUniversities()` · `listAllUniversities()` · `createUniversity(name)` · `setUniversityActive(id, active)` · `deleteUniversity(id)` · `<UniversitySelect id label value onChange required allowEmpty emptyLabel />`

- [ ] **Step 1: 실패하는 컴포넌트 테스트를 쓴다**

`frontend/src/components/UniversitySelect/UniversitySelect.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { UniversitySelect } from "./UniversitySelect";
import * as api from "../../lib/api";

describe("UniversitySelect", () => {
  beforeEach(() => {
    vi.spyOn(api, "listUniversities").mockResolvedValue([
      { id: 1, name: "서울대학교", active: true },
      { id: 2, name: "연세대학교", active: true },
    ]);
  });

  it("목록을 받아 옵션으로 그린다", async () => {
    render(<UniversitySelect id="u" label="학교" value="" onChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "서울대학교" })).toBeInTheDocument();
    });
  });

  it("목록이 비면 안내를 띄운다", async () => {
    vi.spyOn(api, "listUniversities").mockResolvedValue([]);
    render(<UniversitySelect id="u" label="학교" value="" onChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText(/등록된 대학이 없습니다/)).toBeInTheDocument();
    });
  });

  it("allowEmpty면 '없음' 옵션이 있다", async () => {
    render(
      <UniversitySelect id="u" label="학교" value="" onChange={() => {}} allowEmpty emptyLabel="없음" />
    );
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "없음" })).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/UniversitySelect`
Expected: FAIL — 모듈을 찾을 수 없음

- [ ] **Step 3: 타입을 추가한다**

`frontend/src/lib/types.ts`:

```ts
export interface UniversityOut {
  id: number;
  name: string;
  active: boolean;
}
```

`RegisterPayload`는 Task 8·12에서 확장한다. 지금은 건드리지 않는다.

- [ ] **Step 4: API 함수를 추가한다**

`frontend/src/lib/api.ts` 끝에:

```ts
export function listUniversities(): Promise<UniversityOut[]> {
  return apiFetch<UniversityOut[]>("/universities");
}

export function listAllUniversities(): Promise<UniversityOut[]> {
  return apiFetch<UniversityOut[]>("/admin/universities");
}

export function createUniversity(name: string): Promise<UniversityOut> {
  return apiFetch<UniversityOut>("/admin/universities", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function setUniversityActive(id: number, active: boolean): Promise<UniversityOut> {
  return apiFetch<UniversityOut>(`/admin/universities/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ active }),
  });
}

export function deleteUniversity(id: number): Promise<void> {
  return apiFetch<void>(`/admin/universities/${id}`, { method: "DELETE" });
}
```

`UniversityOut`을 파일 상단 `import type { ... }` 목록에 추가한다.

- [ ] **Step 5: 컴포넌트를 만든다**

`frontend/src/components/UniversitySelect/UniversitySelect.tsx`:

```tsx
import { useEffect, useState } from "react";
import { listUniversities } from "../../lib/api";
import type { UniversityOut } from "../../lib/types";

interface Props {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  /** 가중치 규칙의 단일 대학(university_b="")처럼 "고르지 않음"이 유효한 경우 */
  allowEmpty?: boolean;
  emptyLabel?: string;
}

export function UniversitySelect({
  id, label, value, onChange, required, allowEmpty, emptyLabel = "선택하세요",
}: Props) {
  const [items, setItems] = useState<UniversityOut[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    listUniversities()
      .then((data) => { if (active) setItems(data); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  return (
    <div>
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{allowEmpty ? emptyLabel : "선택하세요"}</option>
        {items.map((u) => (
          <option key={u.id} value={u.name}>{u.name}</option>
        ))}
      </select>
      {loaded && items.length === 0 && (
        <p role="alert">등록된 대학이 없습니다. 관리자에게 문의하세요.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 6: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/UniversitySelect`
Expected: 3 passed

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib frontend/src/components/UniversitySelect
git commit -m "feat(frontend): 대학 목록 API 클라이언트 + 공용 UniversitySelect"
```

---

## Task 6: 대학 입력 4곳을 셀렉트로 교체

**Files:**
- Modify: `frontend/src/pages/Register/Register.tsx` + `Register.test.tsx`
- Modify: `frontend/src/pages/Game/OjakgyoTab.tsx` + `OjakgyoTab.test.tsx`
- Modify: `frontend/src/pages/Game/RedThreadTab.tsx` + `RedThreadTab.test.tsx`
- Modify: `frontend/src/pages/Admin/UniversityWeightTab.tsx` + `UniversityWeightTab.test.tsx`

**Interfaces:**
- Consumes: `<UniversitySelect />` · `listUniversities` (Task 5)

- [ ] **Step 1: Register 테스트를 셀렉트 기준으로 고친다**

`Register.test.tsx`에서 학교 입력을 찾던 부분을 바꾸고, 각 테스트 파일 맨 위에 목록 목킹을 추가한다:

```tsx
vi.spyOn(api, "listUniversities").mockResolvedValue([
  { id: 1, name: "서울대학교", active: true },
]);
```

그리고 학교 선택 검증을 추가한다:

```tsx
it("목록에서 학교를 고른다", async () => {
  render(<Register />, { wrapper: MemoryRouter });
  const select = await screen.findByLabelText("학교");
  await userEvent.selectOptions(select, "서울대학교");
  expect((select as HTMLSelectElement).value).toBe("서울대학교");
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/pages/Register`
Expected: FAIL — 학교가 아직 `<input>`이라 `selectOptions`가 실패한다

- [ ] **Step 3: Register의 학교 입력을 교체한다**

`Register.tsx`에서 학교 `<Input>`을 지우고:

```tsx
<UniversitySelect
  id="university"
  label="학교"
  value={university}
  onChange={setUniversity}
  required
/>
```

`validate()`의 `if (!university.trim()) return "학교를 입력하세요";`는 `"학교를 선택하세요"`로 문구만 바꾼다.

- [ ] **Step 4: 게임 지목 2곳을 교체한다**

`OjakgyoTab.tsx` — `사람1 학교` · `사람2 학교` `<Input>` 2개를 `<UniversitySelect>`로:

```tsx
<UniversitySelect id="a-univ" label="사람1 학교" value={aUniv} onChange={setAUniv} required />
<UniversitySelect id="b-univ" label="사람2 학교" value={bUniv} onChange={setBUniv} required />
```

`RedThreadTab.tsx`도 같은 방식으로 대상 학교 입력을 교체한다. 각 테스트 파일에 Step 1의 목킹을 추가한다.

- [ ] **Step 5: 관리자 가중치 탭을 교체한다**

`UniversityWeightTab.tsx`:

```tsx
<UniversitySelect id="uni-a" label="대학 A" value={uniA} onChange={setUniA} required />
<UniversitySelect
  id="uni-b"
  label="대학 B"
  value={uniB}
  onChange={setUniB}
  allowEmpty
  emptyLabel="없음 (단일 대학 규칙)"
/>
```

빈 `uniB`가 단일 대학 규칙을 뜻하는 기존 동작은 그대로다 — `allowEmpty`가 그것을 화면에 드러낼 뿐이다.

- [ ] **Step 6: 프론트 테스트 전체를 돌린다**

Run: `cd frontend && npm test`
Expected: 전부 통과. 목킹을 빠뜨린 파일이 있으면 여기서 드러난다.

- [ ] **Step 7: 타입 빌드를 확인한다**

Run: `cd frontend && npm run build`
Expected: 에러 없음

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/pages
git commit -m "feat(frontend): 대학 입력 4곳을 목록 셀렉트로 교체"
```

---

## Task 7: 관리자 대학 목록 탭

**Files:**
- Create: `frontend/src/pages/Admin/UniversityTab.tsx`
- Create: `frontend/src/pages/Admin/UniversityTab.test.tsx`
- Modify: `frontend/src/pages/Admin/Admin.tsx` + `Admin.test.tsx`

**Interfaces:**
- Consumes: `listAllUniversities` · `createUniversity` · `setUniversityActive` · `deleteUniversity` (Task 5)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/pages/Admin/UniversityTab.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import UniversityTab from "./UniversityTab";
import * as api from "../../lib/api";

describe("UniversityTab", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "listAllUniversities").mockResolvedValue([
      { id: 1, name: "서울대학교", active: true },
      { id: 2, name: "꺼진대학교", active: false },
    ]);
  });

  it("비활성 대학도 목록에 보인다", async () => {
    render(<UniversityTab />);
    expect(await screen.findByText("꺼진대학교")).toBeInTheDocument();
  });

  it("대학을 추가한다", async () => {
    const create = vi.spyOn(api, "createUniversity").mockResolvedValue({
      id: 3, name: "한양대학교", active: true,
    });
    render(<UniversityTab />);
    await userEvent.type(await screen.findByLabelText("대학명"), "한양대학교");
    await userEvent.click(screen.getByRole("button", { name: "추가" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("한양대학교"));
  });

  it("사용 중인 대학 삭제는 안내를 띄운다", async () => {
    vi.spyOn(api, "deleteUniversity").mockRejectedValue(
      new api.ApiError(409, "이미 사용 중인 대학입니다. 삭제 대신 비활성으로 끄세요")
    );
    render(<UniversityTab />);
    const rows = await screen.findAllByRole("button", { name: "삭제" });
    await userEvent.click(rows[0]);
    expect(await screen.findByText(/삭제 대신 비활성/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/pages/Admin/UniversityTab`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 탭을 만든다**

`frontend/src/pages/Admin/UniversityTab.tsx` — `UniversityWeightTab.tsx`의 구조(로딩·에러·낙관적 갱신 없이 재조회)를 그대로 따른다:

```tsx
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listAllUniversities,
  createUniversity,
  setUniversityActive,
  deleteUniversity,
} from "../../lib/api";
import type { UniversityOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Input } from "../../components/Input/Input";
import styles from "./Admin.module.css";

const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

export default function UniversityTab() {
  const [items, setItems] = useState<UniversityOut[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function reload() {
    try {
      setItems(await listAllUniversities());
    } catch {
      setError("목록을 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (name.trim() === "") { setError("대학명을 입력하세요."); return; }
    try {
      await createUniversity(name.trim());
      setName("");
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleToggle(item: UniversityOut) {
    setError("");
    try {
      await setUniversityActive(item.id, !item.active);
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(item: UniversityOut) {
    setError("");
    try {
      await deleteUniversity(item.id);
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (loading) return <p>불러오는 중…</p>;

  return (
    <div className={styles.panel}>
      <form onSubmit={handleCreate}>
        <Input
          id="university-name"
          label="대학명"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit">추가</Button>
      </form>

      <p className={styles.hint}>
        이름은 등록 후 바꿀 수 없습니다. 쓰지 않는 대학은 삭제 대신 끄세요.
      </p>

      {error && <p role="alert">{error}</p>}

      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <span>{item.name}</span>
            <span>{item.active ? "활성" : "비활성"}</span>
            <Button type="button" onClick={() => void handleToggle(item)}>
              {item.active ? "끄기" : "켜기"}
            </Button>
            <Button type="button" onClick={() => void handleDelete(item)}>삭제</Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Admin에 5번째 탭을 붙인다**

`Admin.tsx` — `type Tab`에 `"university"`를 추가하고, 기존 탭 버튼과 동일한 형태로 버튼 하나를 더 넣은 뒤 패널 분기에 `{tab === "university" && <UniversityTab />}`를 추가한다. import도 함께.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd frontend && npm test`
Expected: 전부 통과

- [ ] **Step 6: 빌드 확인 + 커밋**

```bash
cd frontend && npm run build
git add frontend/src/pages/Admin
git commit -m "feat(frontend): 관리자 대학 목록 탭 — 추가·활성 토글·삭제"
```

---

# 2단계 — 연락처 필수

## Task 8: 가입 연락처 최소 1개

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/test_contact_required.py`

**Interfaces:**
- Produces: `RegisterRequest.instagram | kakao_id | phone: str | None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_contact_required.py`:

```python
from fastapi.testclient import TestClient

BASE = {
    "password": "password123", "name": "연락처", "university": "서울대학교",
    "gender": "male", "agreed_terms": True, "agreed_privacy": True,
    "agreed_age_14": True,
}


def _register(client: TestClient, email: str, **contacts):
    return client.post("/auth/register", json={**BASE, "email": email, **contacts})


def test_register_without_contact_is_rejected(client: TestClient):
    assert _register(client, "none@test.com").status_code == 422


def test_register_with_empty_strings_is_rejected(client: TestClient):
    """빈 문자열은 None으로 정규화되므로 연락처가 없는 것과 같다 (설계 §7.1)."""
    res = _register(client, "empty@test.com", instagram="", kakao_id="", phone="")
    assert res.status_code == 422


def test_register_with_one_contact_succeeds(client: TestClient):
    assert _register(client, "one@test.com", kakao_id="drop_kakao").status_code == 201


def test_register_stores_contact(client: TestClient):
    _register(client, "store@test.com", instagram="drop_insta")
    token = client.post("/auth/login", json={
        "email": "store@test.com", "password": "password123",
    }).json()["access_token"]
    me = client.get("/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["instagram"] == "drop_insta"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_contact_required.py -v`
Expected: 앞 2개 FAIL (201을 받는다), 뒤 2개도 FAIL (필드가 저장되지 않음)

- [ ] **Step 3: 스키마를 고친다**

`backend/app/schemas/auth.py` — import에 `model_validator`를 추가하고 `RegisterRequest`에:

```python
    instagram: str | None = None
    kakao_id: str | None = None
    phone: str | None = None

    @field_validator("instagram", "kakao_id", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        return None if v == "" else v

    @model_validator(mode="after")
    def at_least_one_contact(self):
        """연락처가 없으면 매칭돼도 서로 닿을 방법이 없다 (설계 §7.1)."""
        if not (self.instagram or self.kakao_id or self.phone):
            raise ValueError("연락처를 최소 1개 입력하세요")
        return self
```

- [ ] **Step 4: 저장한다**

`backend/app/api/auth.py`의 `User(...)` 생성에 세 필드를 넘긴다:

```python
        instagram=payload.instagram,
        kakao_id=payload.kakao_id,
        phone=payload.phone,
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_contact_required.py -v`
Expected: 4 passed

- [ ] **Step 6: 전체 테스트를 돌리고 conftest를 고친다**

Run: `cd backend && uv run pytest -q`
Expected: **대량 실패.** 유저를 만드는 모든 테스트가 연락처 없이 가입하기 때문이다.

`conftest.py`의 `admin_client` 픽스처 가입 payload에 `"kakao_id": "admin_kakao"`를 추가한다.
그 밖에 직접 `/auth/register`를 호출하는 테스트 파일들도 같은 방식으로 연락처를 하나씩 넣는다.
`_auth`/`_register` 같은 헬퍼가 있는 파일은 헬퍼 한 곳만 고치면 된다.

Run: `cd backend && uv run pytest -q`
Expected: 전부 통과

- [ ] **Step 7: 커밋**

```bash
git add backend/app/schemas/auth.py backend/app/api/auth.py backend/tests
git commit -m "feat(backend): 가입 시 연락처 최소 1개 필수"
```

---

## Task 9: 프로필에서 마지막 연락처 삭제 차단

**Files:**
- Modify: `backend/app/api/me.py:162-172`
- Modify: `backend/tests/test_contact_required.py`

- [ ] **Step 1: 테스트를 추가한다**

`test_contact_required.py` 끝에:

```python
def _login(client: TestClient, email: str) -> dict:
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cannot_clear_last_contact(client: TestClient):
    _register(client, "last@test.com", kakao_id="only_one")
    headers = _login(client, "last@test.com")
    res = client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert res.status_code == 422


def test_can_clear_one_of_two_contacts(client: TestClient):
    _register(client, "two@test.com", kakao_id="a", instagram="b")
    headers = _login(client, "two@test.com")
    res = client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert res.status_code == 200
    assert res.json()["kakao_id"] is None
    assert res.json()["instagram"] == "b"


def test_rejected_clear_does_not_touch_db(client: TestClient):
    """422를 받은 뒤에도 기존 연락처가 살아 있어야 한다 (설계 §7.1)."""
    _register(client, "intact@test.com", kakao_id="keep_me")
    headers = _login(client, "intact@test.com")
    client.put("/me/profile", json={"kakao_id": ""}, headers=headers)
    assert client.get("/me", headers=headers).json()["kakao_id"] == "keep_me"


def test_bio_only_update_still_works(client: TestClient):
    """연락처를 건드리지 않는 수정은 영향받지 않는다."""
    _register(client, "bio@test.com", kakao_id="x")
    headers = _login(client, "bio@test.com")
    res = client.put("/me/profile", json={"bio": "안녕하세요"}, headers=headers)
    assert res.status_code == 200
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_contact_required.py -v`
Expected: `test_cannot_clear_last_contact`·`test_rejected_clear_does_not_touch_db` FAIL

- [ ] **Step 3: 병합 결과로 판정하게 고친다**

`backend/app/api/me.py`의 `update_profile`을 교체한다. `exclude_unset=True` 부분 업데이트라 payload만 봐서는 판정할 수 없다 — 반영 후 상태를 먼저 계산한다.

```python
_CONTACT_FIELDS = ("instagram", "kakao_id", "phone")


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    changes = payload.model_dump(exclude_unset=True)
    # 부분 업데이트라 payload가 아니라 "반영 후 상태"로 판정해야 한다 (설계 §7.1).
    # setattr 전에 계산해서 거부된 요청이 DB에 닿지 않게 한다
    merged = {
        field: changes.get(field, getattr(current_user, field))
        for field in _CONTACT_FIELDS
    }
    if not any(merged.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="연락처는 최소 1개를 남겨야 합니다",
        )
    for field, value in changes.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_contact_required.py -v`
Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/me.py backend/tests/test_contact_required.py
git commit -m "fix(backend): 프로필에서 마지막 연락처 삭제 차단 — 병합 결과로 판정"
```

---

## Task 10: 매칭 자격에 연락처 조건

**Files:**
- Modify: `backend/app/services/matching.py:82-98`
- Modify: `backend/tests/test_matching.py`
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§6.2)

- [ ] **Step 1: 테스트를 추가한다**

`test_matching.py`에 (파일의 기존 유저 생성 헬퍼를 그대로 쓴다):

```python
def test_user_without_contact_is_excluded():
    """DB 직접 수정이나 과거 데이터로 연락처 0개가 생겨도 매칭되면 안 된다 (설계 §7.1)."""
    db = TestingSessionLocal()
    user = db.query(User).first()
    user.instagram = None
    user.kakao_id = None
    user.phone = None
    db.commit()
    assert user.id not in [u.id for u in eligible_users(db)]
    db.close()


def test_empty_string_contact_counts_as_missing():
    """과거 데이터에 빈 문자열이 남아 있을 수 있다."""
    db = TestingSessionLocal()
    user = db.query(User).first()
    user.instagram = ""
    user.kakao_id = ""
    user.phone = ""
    db.commit()
    assert user.id not in [u.id for u in eligible_users(db)]
    db.close()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_matching.py -k contact -v`
Expected: 2 FAIL

- [ ] **Step 3: `eligible_users`에 조건을 넣는다**

`backend/app/services/matching.py` — import에 `and_`, `or_`를 추가하고:

```python
def _has_contact():
    """연락처 1개 이상 (설계 §7.2). 빈 문자열도 없는 것으로 본다 —
    스키마는 None으로 정규화하지만 과거 데이터나 DB 직접 수정이 남길 수 있다."""
    return or_(
        *[
            and_(column.isnot(None), column != "")
            for column in (User.instagram, User.kakao_id, User.phone)
        ]
    )
```

`eligible_users`의 `.filter(...)`에 `_has_contact(),`를 한 줄 추가하고, docstring의 자격 목록에 연락처 조건을 적는다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_matching.py -v`
Expected: 전부 통과

- [ ] **Step 5: 선행 스펙 §6.2를 고친다**

`docs/superpowers/specs/2026-08-21-matching-algorithm-design.md`의 §6.2 표에 행을 추가한다:

```markdown
| 연락처 1개 이상 | `instagram` · `kakao_id` · `phone` 중 최소 1개 (2026-09-04 추가) |
```

- [ ] **Step 6: 전체 테스트 + 커밋**

```bash
cd backend && uv run pytest -q
git add backend/app/services/matching.py backend/tests/test_matching.py docs/superpowers/specs/2026-08-21-matching-algorithm-design.md
git commit -m "feat(backend): 연락처 없는 유저를 매칭 자격에서 제외"
```

---

## Task 11: 가입 폼 연락처 + 마이페이지 에러

**Files:**
- Modify: `frontend/src/lib/types.ts` (`RegisterPayload`)
- Modify: `frontend/src/pages/Register/Register.tsx` + `Register.test.tsx`
- Modify: `frontend/src/pages/MyPage/MyPage.tsx` + 테스트

- [ ] **Step 1: 테스트를 추가한다**

`Register.test.tsx`:

```tsx
it("연락처를 하나도 안 채우면 제출을 막는다", async () => {
  render(<Register />, { wrapper: MemoryRouter });
  await userEvent.type(screen.getByLabelText("이메일"), "a@test.com");
  await userEvent.type(screen.getByLabelText("비밀번호"), "password123");
  await userEvent.type(screen.getByLabelText("이름"), "김테스트");
  await userEvent.selectOptions(await screen.findByLabelText("학교"), "서울대학교");
  await userEvent.click(screen.getByRole("button", { name: "가입하기" }));
  expect(await screen.findByText(/연락처를 최소 1개/)).toBeInTheDocument();
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/pages/Register`
Expected: FAIL

- [ ] **Step 3: 타입을 넓힌다**

`types.ts`의 `RegisterPayload`에:

```ts
  instagram?: string | null;
  kakao_id?: string | null;
  phone?: string | null;
```

- [ ] **Step 4: 폼에 연락처를 넣는다**

`Register.tsx` — state 3개와 `<Input>` 3개(인스타그램 아이디 / 카카오톡 ID / 전화번호)를 추가하고, `validate()`에:

```tsx
if (!instagram.trim() && !kakaoId.trim() && !phone.trim()) {
  return "연락처를 최소 1개 입력하세요";
}
```

`registerUser` payload에 세 값을 `.trim() || null`로 넘긴다. 폼에 안내를 한 줄 둔다:
"매칭된 상대가 연락할 수 있도록 최소 1개는 필요합니다."

- [ ] **Step 5: 마이페이지에 에러 표시를 붙인다**

`MyPage.tsx`의 프로필 저장 `catch`에서 `ApiError.message`를 그대로 화면에 띄운다. 서버가
"연락처는 최소 1개를 남겨야 합니다"를 주므로 별도 문구를 만들지 않는다.

- [ ] **Step 6: 통과 확인 + 빌드 + 커밋**

```bash
cd frontend && npm test && npm run build
git add frontend/src
git commit -m "feat(frontend): 가입 폼 연락처 3필드 + 최소 1개 검증"
```

---

# 3단계 — 학번

## Task 12: 학번 수용 + `_identity_resolver`

스키마는 Task 1에서 이미 들어갔다. 여기서는 값을 받고 쓰는 코드만 얹는다.

**Files:**
- Create: `backend/app/schemas/admission.py`
- Create: `backend/tests/test_identity_resolver.py`
- Modify: `backend/app/schemas/auth.py` · `backend/app/schemas/game.py` · `backend/app/schemas/user.py`
- Modify: `backend/app/api/auth.py` · `backend/app/api/game.py`
- Modify: `backend/app/services/matching.py:118-135` (`_identity_resolver`), `:137-172` (`game_signals`)

**Interfaces:**
- Produces: `check_admission_year(value: int | None) -> int | None` · `resolve(name, university, admission_year=0) -> int | None`

- [ ] **Step 1: 실패하는 resolver 테스트를 쓴다**

`backend/tests/test_identity_resolver.py`:

```python
from tests.conftest import TestingSessionLocal
from app.models.user import User
from app.services.matching import _identity_resolver

SNU = "서울대학교"


def _add(db, email, name, university=SNU, admission_year=None):
    user = User(
        email=email, password_hash="x", name=name, university=university,
        gender="female", admission_year=admission_year, kakao_id="k",
    )
    db.add(user)
    db.commit()
    return user


def test_single_candidate_without_year():
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일")
    assert _identity_resolver(db)("김유일", SNU) == user.id
    db.close()


def test_namesakes_resolved_by_year():
    """학번의 존재 이유 (설계 §6.2)."""
    db = TestingSessionLocal()
    a = _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2022)
    assert _identity_resolver(db)("김동명", SNU, 2021) == a.id
    db.close()


def test_namesakes_without_year_are_ignored():
    db = TestingSessionLocal()
    _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2022)
    assert _identity_resolver(db)("김동명", SNU) is None
    db.close()


def test_namesakes_with_same_year_are_ignored():
    db = TestingSessionLocal()
    _add(db, "n1@test.com", "김동명", admission_year=2021)
    _add(db, "n2@test.com", "김동명", admission_year=2021)
    assert _identity_resolver(db)("김동명", SNU, 2021) is None
    db.close()


def test_single_candidate_with_mismatched_year_still_resolves():
    """학번을 안 적었으면 성공했을 지목이 적었다는 이유로 실패하면 안 된다 (설계 §6.3)."""
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일", admission_year=2020)
    assert _identity_resolver(db)("김유일", SNU, 2019) == user.id
    db.close()


def test_year_does_not_exclude_unregistered_candidates():
    """대상이 학번을 안 넣었다는 이유로 지목이 사라지면 안 된다 (설계 §6.1)."""
    db = TestingSessionLocal()
    user = _add(db, "solo@test.com", "김유일", admission_year=None)
    assert _identity_resolver(db)("김유일", SNU, 2021) == user.id
    db.close()


def test_different_university_is_not_a_candidate():
    db = TestingSessionLocal()
    _add(db, "y@test.com", "김동명", university="연세대학교")
    assert _identity_resolver(db)("김동명", SNU) is None
    db.close()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_identity_resolver.py -v`
Expected: 학번을 넘기는 케이스가 `TypeError` — resolve가 인자 2개만 받는다

- [ ] **Step 3: resolver를 고친다**

`backend/app/services/matching.py`의 `_identity_resolver`를 교체한다:

```python
def _identity_resolver(db: Session):
    """이름+학교로 후보를 찾고 학번으로 좁힌다 (설계 §6).

    학번은 후보를 좁히는 추가 필터일 뿐이다. 학번 미등록 유저를 후보에서 빼지 않는다 —
    그러면 대상이 학번을 안 넣었다는 이유만으로 지목이 조용히 사라진다.
    """
    index: dict[tuple[str, str], list[tuple[int, int | None]]] = defaultdict(list)
    for user_id, name, university, admission_year in db.query(
        User.id, User.name, User.university, User.admission_year
    ).all():
        index[(name.strip(), university.strip())].append((user_id, admission_year))

    def resolve(name: str, university: str, admission_year: int = 0) -> int | None:
        hits = index.get((name.strip(), university.strip()), [])
        if admission_year:
            narrowed = [hit for hit in hits if hit[1] == admission_year]
            if len(narrowed) == 1:
                return narrowed[0][0]
            # 0명이거나 2명 이상이면 학번으로 못 좁힌다 — 이름+학교 결과로 폴백 (설계 §6.3)
        return hits[0][0] if len(hits) == 1 else None

    return resolve
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_identity_resolver.py -v`
Expected: 7 passed

- [ ] **Step 5: `game_signals`가 학번을 넘기게 한다**

같은 파일의 `game_signals`에서 세 호출을 고친다:

```python
        target_id = resolve(
            thread.target_name, thread.target_university, thread.target_admission_year
        )
```

```python
        a = resolve(
            entry.person_a_name, entry.person_a_university, entry.person_a_admission_year
        )
        b = resolve(
            entry.person_b_name, entry.person_b_university, entry.person_b_admission_year
        )
```

- [ ] **Step 6: 학번 범위 검증 모듈을 만든다**

`backend/app/schemas/admission.py`:

```python
from datetime import datetime

ADMISSION_YEAR_MIN = 2000


def check_admission_year(value: int | None) -> int | None:
    """입학년도 4자리 검증 (설계 §4.2).

    상한이 현재 연도가 아니라 +1인 것은 신입생이 입학 전 학기에 가입할 수 있어서다.
    """
    if value is None:
        return None
    upper = datetime.utcnow().year + 1
    if not (ADMISSION_YEAR_MIN <= value <= upper):
        raise ValueError(f"학번은 {ADMISSION_YEAR_MIN}~{upper} 사이여야 합니다")
    return value
```

- [ ] **Step 7: 가입·지목 스키마에 학번을 넣는다**

`schemas/auth.py`의 `RegisterRequest`:

```python
    admission_year: int | None = None

    @field_validator("admission_year")
    @classmethod
    def valid_admission_year(cls, v: int | None) -> int | None:
        return check_admission_year(v)
```

`schemas/game.py`의 `OjakgyoCreate`에 `person_a_admission_year` · `person_b_admission_year`,
`RedThreadTarget`에 `target_admission_year`를 각각 `int | None = None`으로 넣고 같은 validator를 건다.
`OjakgyoOut` · `RedThreadTargetOut`에도 응답 필드를 추가한다.
`schemas/user.py`의 `UserOut`에 `admission_year: int | None`을 추가한다.

- [ ] **Step 8: API가 학번을 저장하게 한다**

`api/auth.py` — `User(...)`에 `admission_year=payload.admission_year`.

`api/game.py` — 지목 테이블은 NOT NULL 0 센티넬이므로 None을 0으로 바꿔 저장한다:

```python
        # 미입력(None)은 0으로 저장한다 — 유니크 제약에 NULL을 넣지 않기 위해서다 (설계 §4.2)
        person_a_admission_year=payload.person_a_admission_year or 0,
```

`red-thread`의 각 target도 같은 방식으로 처리한다.

- [ ] **Step 9: 학번 범위 테스트를 추가한다**

`test_contact_required.py` 옆에 두지 말고 `test_university_validation.py`에 추가한다:

```python
def test_register_rejects_year_below_range(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "y1@test.com", "password": "password123", "name": "학번",
        "university": "서울대학교", "gender": "male", "kakao_id": "k",
        "admission_year": 1999,
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    assert res.status_code == 422


def test_register_accepts_next_year(client: TestClient):
    """입학 전 학기 가입을 허용한다 (설계 §4.2)."""
    from datetime import datetime
    res = client.post("/auth/register", json={
        "email": "y2@test.com", "password": "password123", "name": "학번",
        "university": "서울대학교", "gender": "male", "kakao_id": "k",
        "admission_year": datetime.utcnow().year + 1,
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    assert res.status_code == 201
```

- [ ] **Step 10: 전체 테스트 + 커밋**

```bash
cd backend && uv run pytest -q
git add backend/app backend/tests
git commit -m "feat(backend): 학번으로 동명이인 지목 구분 — 후보 1명일 때만 적용"
```

---

## Task 13: 학번 입력 화면 3곳

**Files:**
- Modify: `frontend/src/lib/types.ts` · `frontend/src/pages/Register/Register.tsx` · `frontend/src/pages/Game/OjakgyoTab.tsx` · `frontend/src/pages/Game/RedThreadTab.tsx` + 각 테스트

- [ ] **Step 1: 테스트를 추가한다**

`OjakgyoTab.test.tsx`:

```tsx
it("학번 없이도 지목할 수 있다", async () => {
  const create = vi.spyOn(api, "createOjakgyo").mockResolvedValue({} as never);
  render(<OjakgyoTab />);
  await userEvent.type(screen.getByLabelText("사람1 이름"), "김철수");
  await userEvent.selectOptions(await screen.findByLabelText("사람1 학교"), "서울대학교");
  await userEvent.type(screen.getByLabelText("사람2 이름"), "이영희");
  await userEvent.selectOptions(screen.getByLabelText("사람2 학교"), "서울대학교");
  await userEvent.click(screen.getByRole("button", { name: "지목하기" }));
  await waitFor(() => {
    expect(create).toHaveBeenCalledWith(
      expect.objectContaining({ person_a_admission_year: null })
    );
  });
});

it("동명이인 안내를 보여준다", async () => {
  render(<OjakgyoTab />);
  expect(await screen.findByText(/동명이인이 있으면/)).toBeInTheDocument();
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/pages/Game/OjakgyoTab`
Expected: FAIL

- [ ] **Step 3: 타입을 넓힌다**

`types.ts` — `RegisterPayload`에 `admission_year?: number | null`,
`OjakgyoCreate`에 `person_a_admission_year` · `person_b_admission_year`,
붉은실 target 타입에 `target_admission_year`를 각각 `number | null`로 추가한다.

- [ ] **Step 4: 입력과 안내 문구를 넣는다**

세 화면 모두 `<Input type="number" />` 하나씩 추가하고, 값은 `Number(v) || null`로 넘긴다.

안내 문구 (스펙 §6.4 그대로):

```tsx
// 게임 지목 폼
<p>선택 입력. 동명이인이 있으면 학번 없이는 지목이 반영되지 않을 수 있습니다.</p>

// 회원가입 폼
<p>선택 입력. 입력하지 않으면 다른 사람이 회원님을 지목할 때 동명이인과 구분되지 않을 수 있습니다.</p>
```

- [ ] **Step 5: 통과 확인 + 빌드 + 커밋**

```bash
cd frontend && npm test && npm run build
git add frontend/src
git commit -m "feat(frontend): 학번 입력 3곳 + 동명이인 정확도 안내"
```

---

## Task 14: 스펙·CLAUDE.md 정리

**Files:**
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md`
- Modify: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`
- Modify: `docs/superpowers/specs/2026-07-17-signup-consent-design.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 매칭 설계 문서를 고친다**

- §4.4 — "⚠️ 학번 필드는 아직 없다" 경고 블록을 지우고, 학번이 들어왔음과 §6 폴백 규칙(스펙 §6.3)을 적는다
- §10 — "본 설계 범위 밖" 목록에서 "학번 필드 추가" 줄을 지운다
- §12 — "대학명 오타 시 규칙이 조용히 안 먹음", "연락처 1개 이상 서버 검증 부재" 두 행을 지우고 각각 해결됨을 적는다 (§6.2는 Task 10에서 이미 고쳤다)

- [ ] **Step 2: 상위 스펙과 가입 동의 스펙을 고친다**

회원가입 항목에 대학 선택 · 연락처 최소 1개 · 학번(선택)을 반영한다.

- [ ] **Step 3: CLAUDE.md를 고친다**

- 핵심 위반 금지 표의 "대학 목록 하드코딩" 행 → 목록은 `universities` 테이블에서 관리하며 코드 상수로 두지 않는다로 갱신
- 미결 항목 표의 "학번(입학년도) 필드" 행 → ✅ 완료 (2026-09-04)
- "16개 대학 목록" 행 → 관리 방식은 확정, 실제 값만 팀 결정으로 갱신

- [ ] **Step 4: 커밋**

```bash
git add docs CLAUDE.md
git commit -m "docs(spec): 가입 데이터 정합성 반영 — 학번·연락처·대학 목록"
```

---

## 완료 기준

- [ ] `cd backend && uv run pytest -q` 전부 통과
- [ ] `cd frontend && npm test` 전부 통과
- [ ] `cd frontend && npm run build` 타입 클린
- [ ] `cd backend && uv run alembic upgrade head` 후 `alembic current`가 새 head
- [ ] 목록에 없는 대학명으로 가입·지목·가중치 등록이 전부 422
- [ ] 연락처 0개로 가입 불가, 마지막 연락처 삭제 불가, 연락처 0개 유저는 매칭 풀 제외
- [ ] 동명이인 2명 중 학번이 맞는 1명으로 지목이 붙는다
