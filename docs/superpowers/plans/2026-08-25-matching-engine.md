# 매칭 엔진 (2단계) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 설문 응답으로 궁합 점수를 계산해 라운드별 남녀 1:1 최적 매칭을 실행하고 결과를 DB에 저장하는 엔진과, 관리자가 그것을 실행하는 버튼을 만든다.

**Architecture:** 순수 함수 계층(`scoring.py` = 설문→점수, `pairing.py` = 점수표→최적 조합)은 DB를 모른다. 그 위에 `matching.py`가 풀 구성·하드필터·보정·저장을 오케스트레이션하고, `api/matching.py`는 HTTP 껍데기로 `run_matching()`만 호출한다. 이 경계 덕에 나중에 스케줄러로 실행 트리거를 바꿔도 아래 세 파일은 손대지 않는다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, networkx(신규), pytest / React(Vite) + Vitest

**Spec:** `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md`

## Global Constraints

- **범위는 스펙 §10의 2단계뿐이다.** 대학 가중치(§4.2)는 3단계, `GET /me/match`·홈 카드(§7.1·§8)는 4단계다. 이 계획에서 대학 가중치는 **상수 `UNIVERSITY_BONUS = 0`으로 자리만 마련**한다. 테이블·CRUD·관리자 탭을 만들지 않는다.
- 설문 답안 형식은 `Survey.answers = {"responses": {문항id: 값}, "absolute": [문항id, ...]}`. `absolute`에는 `_pref` 문항 id만 들어온다(프론트가 partner 섹션에서만 토글 허용).
- 문항 id는 `X_pref` ↔ `X_self` 짝. 예외는 `grooming_self`(짝 없음, 매칭에서 제외).
- 카테고리 가중치: 가치관 1.5 / 관계 1.3 / 생활 1.0 / 외모 0.8. **코드 상수.**
- 이월 보너스 = `min(missed_rounds × 15, 45)`.
- 오작교 지목자 1명 +33, 2명 +66, 3명 이상 보장. 붉은실 상호 보장. **절대질문이 보장을 이긴다.**
- 게임 대상 유저 식별은 **이름+학교가 유일할 때만** 적용(학번 필드는 아직 없음 — 별도 작업).
- 백엔드 규칙(`backend/CLAUDE.md`): 엔드포인트는 Pydantic 스키마 사용, dict 반환 금지 / 모델 추가 시 `app/models/__init__.py` re-export 갱신 / 인증은 `core.deps`의 `require_admin` 사용.
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- 테스트 실행: 백엔드 `cd backend; uv run pytest`, 프론트 `cd frontend; npm test -- --run`.
- **git push·PR 생성은 사용자 허락 후에만.** 각 태스크의 커밋은 로컬까지만 한다.

---

## 파일 구조

| 파일 | 책임 | 태스크 |
|---|---|---|
| `backend/app/models/user.py` (수정) | `missed_rounds` 컬럼 | 1 |
| `backend/app/models/match.py` (수정) | `RoundStatus.running`, `Match.score`, 라운드별 유니크 | 1 |
| `backend/alembic/versions/<rev>_matching_engine.py` (신규) | 위 스키마 변경 마이그레이션 | 1 |
| `backend/app/services/__init__.py` (신규) | 패키지 마커 | 2 |
| `backend/app/services/scoring.py` (신규) | 문항 만족도 → 방향 점수 → 페어 점수 → 절대질문 필터 | 2, 3 |
| `backend/app/services/pairing.py` (신규) | 점수표 → 최적 조합 (networkx) | 4 |
| `backend/app/services/matching.py` (신규) | 8단계 오케스트레이션 | 5, 6, 7 |
| `backend/app/schemas/matching.py` (신규) | `MatchingRunOut` | 8 |
| `backend/app/api/matching.py` (신규) | `POST /admin/match-rounds/{id}/run` | 8 |
| `backend/app/api/router.py` (수정) | 라우터 등록 | 8 |
| `frontend/src/lib/types.ts` (수정) | `MatchingRunOut`, `status`에 `running` 추가 | 9 |
| `frontend/src/lib/api.ts` (수정) | `runMatchRound` | 9 |
| `frontend/src/pages/Admin/RoundTab.tsx` (수정) | 매칭 실행 버튼 + 결과 요약 | 9 |

테스트: `backend/tests/test_matching_models.py`, `test_scoring.py`, `test_pairing.py`, `test_matching.py`, `test_admin_matching.py`, `frontend/src/pages/Admin/RoundTab.test.tsx`(추가).

---

### Task 1: 데이터 모델 변경

**Files:**
- Modify: `backend/app/models/user.py` (User 클래스에 컬럼 1개)
- Modify: `backend/app/models/match.py` (RoundStatus, Match)
- Create: `backend/alembic/versions/<rev>_matching_engine.py`
- Test: `backend/tests/test_matching_models.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `User.missed_rounds: int` (기본 0) / `RoundStatus.running` / `Match.score: int` / `Match`의 유니크 제약 `uq_matches_round_user_a`, `uq_matches_round_user_b`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_matching_models.py` 새 파일:

```python
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.match import Match, MatchRound, RoundStatus
from app.models.user import Gender, User, UserStatus
from tests.conftest import TestingSessionLocal


def _user(db, email: str, gender: Gender = Gender.male) -> User:
    user = User(
        email=email, password_hash="x", name="테스트",
        university="서울대학교", gender=gender, status=UserStatus.active,
    )
    db.add(user)
    db.commit()
    return user


def test_missed_rounds_defaults_to_zero():
    db = TestingSessionLocal()
    user = _user(db, "carry@test.com")
    assert user.missed_rounds == 0
    db.close()


def test_round_status_has_running():
    assert RoundStatus.running.value == "running"


def test_match_stores_score():
    db = TestingSessionLocal()
    a = _user(db, "a@test.com", Gender.male)
    b = _user(db, "b@test.com", Gender.female)
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()

    db.add(Match(user_a_id=a.id, user_b_id=b.id, match_round_id=round_.id, score=72))
    db.commit()
    assert db.query(Match).one().score == 72
    db.close()


def test_same_user_cannot_match_twice_in_one_round():
    """한 라운드에서 한 사람이 두 번 짝지어지는 사고를 DB가 막는다 (설계 §6.1)."""
    db = TestingSessionLocal()
    a = _user(db, "a@test.com", Gender.male)
    b = _user(db, "b@test.com", Gender.female)
    c = _user(db, "c@test.com", Gender.female)
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()

    db.add(Match(user_a_id=a.id, user_b_id=b.id, match_round_id=round_.id, score=50))
    db.commit()
    db.add(Match(user_a_id=a.id, user_b_id=c.id, match_round_id=round_.id, score=50))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_matching_models.py -v`
Expected: FAIL — `AttributeError: missed_rounds` / `AttributeError: RoundStatus.running` / `TypeError: 'score' is an invalid keyword argument`

- [ ] **Step 3: `User.missed_rounds` 추가**

`backend/app/models/user.py`의 `matching_paused` 줄 바로 아래에 추가:

```python
    matching_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 이월 보너스 계산용. 매칭 실행 시 매칭된 사람은 0, 안 된 사람은 +1 (설계 §4.1)
    missed_rounds: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
```

- [ ] **Step 4: `RoundStatus.running` + `Match` 변경**

`backend/app/models/match.py`:

```python
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RoundStatus(str, enum.Enum):
    pending = "pending"
    running = "running"  # 실행 중. 서버가 죽으면 여기 멈춰 관리자가 인지한다 (설계 §5.5)
    done = "done"
```

`Match` 클래스에 유니크 제약과 `score`를 추가한다 (기존 필드는 그대로):

```python
class Match(Base):
    __tablename__ = "matches"
    # 한 라운드에서 한 사람이 두 번 매칭되는 사고를 DB가 막는다 (설계 §6.1)
    __table_args__ = (
        UniqueConstraint("match_round_id", "user_a_id", name="uq_matches_round_user_a"),
        UniqueConstraint("match_round_id", "user_b_id", name="uq_matches_round_user_b"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    match_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("match_rounds.id"), nullable=False
    )
    # 보정 전 궁합 점수. 카테고리 가중치를 나중에 조정하려면 이 기록이 필요하다 (설계 §6.1)
    score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    round: Mapped["MatchRound"] = relationship("MatchRound", back_populates="matches")
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_matching_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: 마이그레이션 작성**

빈 리비전을 만든다 (autogenerate는 Enum 값 추가를 잡지 못하므로 손으로 쓴다):

```bash
cd backend; uv run alembic revision -m "matching engine schema"
```

생성된 파일의 `upgrade`/`downgrade`를 아래로 교체한다 (`revision`·`down_revision` 헤더는 건드리지 않는다):

```python
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("missed_rounds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "matches",
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )
    # SQLite는 ALTER로 제약을 못 붙인다. batch_alter_table이 테이블 재생성으로 처리한다
    with op.batch_alter_table("matches") as batch:
        batch.create_unique_constraint(
            "uq_matches_round_user_a", ["match_round_id", "user_a_id"]
        )
        batch.create_unique_constraint(
            "uq_matches_round_user_b", ["match_round_id", "user_b_id"]
        )
    # PostgreSQL은 enum 타입에 값을 명시적으로 추가해야 한다. SQLite는 VARCHAR라 불필요
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE round_status ADD VALUE IF NOT EXISTS 'running'")


def downgrade() -> None:
    with op.batch_alter_table("matches") as batch:
        batch.drop_constraint("uq_matches_round_user_b", type_="unique")
        batch.drop_constraint("uq_matches_round_user_a", type_="unique")
    op.drop_column("matches", "score")
    op.drop_column("users", "missed_rounds")
    # PostgreSQL은 enum 값 제거를 지원하지 않는다. 'running'은 남겨둔다
```

- [ ] **Step 7: 마이그레이션 적용 확인**

Run: `cd backend; uv run alembic upgrade head`
Expected: 에러 없이 종료. 실패하면 그 에러를 고친 뒤 진행한다.

> 주의: PostgreSQL 11 이하는 `ALTER TYPE ... ADD VALUE`를 트랜잭션 안에서 실행하지 못한다. 운영 DB가 PG 12 미만이면 그 문장만 따로 수동 실행해야 한다.

- [ ] **Step 8: 전체 테스트 + 커밋**

Run: `cd backend; uv run pytest -q`
Expected: 전부 PASS

```bash
git add backend/app/models/user.py backend/app/models/match.py backend/alembic/versions backend/tests/test_matching_models.py
git commit -m "$(cat <<'EOF'
feat(backend): 매칭 엔진 스키마 — missed_rounds·running·Match.score

한 라운드에서 같은 사람이 두 번 매칭되지 않도록 유니크 제약 2개 추가.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: scoring.py — 문항 만족도

**Files:**
- Create: `backend/app/services/__init__.py` (빈 파일)
- Create: `backend/app/services/scoring.py`
- Test: `backend/tests/test_scoring.py`

**Interfaces:**
- Consumes: `app.survey.catalog`의 `QUESTIONS`, `Category`, `Question`
- Produces:
  - `CATEGORY_WEIGHT: dict[Category, float]`
  - `PAIRS: dict[str, tuple[Question, Question]]` — base 이름 → (pref 문항, self 문항)
  - `satisfaction(base: str, pref_responses: dict, self_responses: dict) -> float | None` — `None`은 "계산에서 제외"

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_scoring.py` 새 파일:

```python
import pytest

from app.services.scoring import PAIRS, satisfaction


def sat(base, pref, self_):
    """문항 하나만 담은 responses 두 개로 만족도를 구한다."""
    return satisfaction(base, pref, self_)


def test_every_pref_question_has_a_self_pair():
    """카탈로그 정합성 — grooming_self만 짝이 없다 (설계 §3.1)."""
    self_ids = {self_q.id for _, self_q in PAIRS.values()}
    assert "grooming_self" not in self_ids
    assert "height" in PAIRS and "living" in PAIRS


def test_height_bucket_distance():
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 180}) == 1.0
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 170}) == 0.5
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 160}) == 0.0
    # 경계: 175는 175_185 구간, 185는 o185 구간
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 175}) == 1.0
    assert sat("height", {"height_pref": "o185"}, {"height_self": 185}) == 1.0


def test_no_pref_and_missing_are_excluded():
    assert sat("height", {"height_pref": "any"}, {"height_self": 180}) is None
    assert sat("height", {}, {"height_self": 180}) is None
    assert sat("height", {"height_pref": "175_185"}, {}) is None
    # 다중선택에 '상관없음'이 섞여 있으면 다른 값과 함께 골랐어도 제외 (설계 §3.1)
    assert sat("style", {"style_pref": ["casual", "any"]}, {"style_self": ["formal"]}) is None


def test_multi_select_rules():
    assert sat("face", {"face_pref": ["type_a", "type_b"]}, {"face_self": "type_b"}) == 1.0
    assert sat("face", {"face_pref": ["type_a"]}, {"face_self": "type_b"}) == 0.0
    assert sat("style", {"style_pref": ["casual"]}, {"style_self": ["casual", "street"]}) == 1.0
    assert sat("style", {"style_pref": ["formal"]}, {"style_self": ["casual"]}) == 0.0


def test_tattoo_and_piercing():
    assert sat("tattoo", {"tattoo_pref": "ok"}, {"tattoo_self": "yes"}) == 1.0
    assert sat("tattoo", {"tattoo_pref": "none"}, {"tattoo_self": "no"}) == 1.0
    assert sat("tattoo", {"tattoo_pref": "none"}, {"tattoo_self": "yes"}) == 0.0
    assert sat("piercing", {"piercing_pref": "none"}, {"piercing_self": "yes"}) == 0.0


def test_politics_ordinal_and_unknown():
    assert sat("politics", {"politics_pref": "moderate"}, {"politics_self": "moderate"}) == 1.0
    assert sat("politics", {"politics_pref": "moderate"}, {"politics_self": "progressive"}) == 0.5
    assert sat("politics", {"politics_pref": "progressive"}, {"politics_self": "conservative"}) == 0.0
    assert sat("politics", {"politics_pref": "progressive"}, {"politics_self": "unknown"}) == 0.5


def test_religion_other_is_half():
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "none"}) == 1.0
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "buddhist"}) == 0.0
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "other"}) == 0.5


def test_scale_questions():
    assert sat("contact_freq", {"contact_freq_pref": 3}, {"contact_freq_self": 3}) == 1.0
    assert sat("contact_freq", {"contact_freq_pref": 3}, {"contact_freq_self": 4}) == 0.75
    assert sat("affection", {"affection_pref": 1}, {"affection_self": 5}) == 0.0


def test_conflict_style_and_sleep_are_exact_match():
    assert sat("conflict_style", {"conflict_style_pref": "later"}, {"conflict_style_self": "later"}) == 1.0
    assert sat("conflict_style", {"conflict_style_pref": "later"}, {"conflict_style_self": "alone"}) == 0.0
    assert sat("sleep", {"sleep_pref": "night"}, {"sleep_self": "night"}) == 1.0
    assert sat("sleep", {"sleep_pref": "night"}, {"sleep_self": "morning"}) == 0.0


def test_priority_rank_distance():
    same = ["lover", "friend", "self_dev", "family"]
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": same}) == 1.0
    reversed_ = list(reversed(same))
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": reversed_}) == 0.0
    swapped = ["friend", "lover", "self_dev", "family"]
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": swapped}) == 0.75


def test_budget_and_exercise_ordinal():
    assert sat("date_budget", {"date_budget_pref": "10_20"}, {"date_budget_self": "10_20"}) == 1.0
    assert sat("date_budget", {"date_budget_pref": "10_20"}, {"date_budget_self": "5_10"}) == 0.5
    assert sat("date_budget", {"date_budget_pref": "u5"}, {"date_budget_self": "o30"}) == 0.0
    assert sat("exercise", {"exercise_pref": "w3"}, {"exercise_self": "w1_2"}) == 0.5
    assert sat("exercise", {"exercise_pref": "w3"}, {"exercise_self": "none"}) == 0.0


def test_mapping_tables():
    assert sat("cost_share", {"cost_share_pref": "partner"}, {"cost_share_self": "me"}) == 1.0
    assert sat("cost_share", {"cost_share_pref": "partner"}, {"cost_share_self": "dutch"}) == 0.0
    assert sat("cost_share", {"cost_share_pref": "dutch"}, {"cost_share_self": "richer"}) == 0.5
    assert sat("smoking", {"smoking_pref": "none_only"}, {"smoking_self": "sometimes"}) == 0.0
    assert sat("smoking", {"smoking_pref": "sometimes_ok"}, {"smoking_self": "sometimes"}) == 1.0
    assert sat("smoking", {"smoking_pref": "sometimes_ok"}, {"smoking_self": "yes"}) == 0.0
    assert sat("drinking", {"drinking_pref": "none"}, {"drinking_self": "sometimes"}) == 0.5
    assert sat("drinking", {"drinking_pref": "sometimes_ok"}, {"drinking_self": "often"}) == 0.5
    assert sat("hobby", {"hobby_pref": "indoor"}, {"hobby_self": "both"}) == 1.0
    assert sat("hobby", {"hobby_pref": "indoor"}, {"hobby_self": "outdoor"}) == 0.0


def test_living():
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "independent"}) == 1.0
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "dorm"}) == 0.5
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "home"}) == 0.0


@pytest.mark.parametrize(
    "pref, mine, theirs, expected",
    [
        ("h1", "서울", "서울", 1.0),    # 0홉
        ("h1", "서울", "경기", 0.5),    # 1홉
        ("h1", "서울", "강원", 0.0),    # 2홉
        ("h2", "서울", "강원", 1.0),
        ("h2", "서울", "충남", 0.5),    # 서울-경기-충남 … 2홉
        ("h3", "서울", "부산", 0.0),    # 4홉 이상
        ("h3", "서울", "충북", 1.0),    # 2홉
        ("h1", "제주", "제주", 1.0),    # 제주끼리는 0홉
        ("h3", "제주", "서울", 0.0),    # 육로 연결 없음
    ],
)
def test_residence_hops(pref, mine, theirs, expected):
    """거주지는 '내' 거주지도 필요하다 — pref 쪽 responses에서 함께 읽는다 (설계 §3.3)."""
    assert sat("residence", {"residence_pref": pref, "residence_self": mine},
               {"residence_self": theirs}) == expected


def test_residence_needs_my_own_residence():
    assert sat("residence", {"residence_pref": "h1"}, {"residence_self": "서울"}) is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: 패키지 마커 생성**

```bash
cd backend; touch app/services/__init__.py
```

(디렉터리가 없으면 먼저 만든다: `mkdir -p app/services`)

- [ ] **Step 4: `scoring.py` 만족도 부분 구현**

`backend/app/services/scoring.py` 새 파일:

```python
"""설문 응답 → 궁합 점수. DB를 모른다 (설계 §2.1).

용어
  responses : {문항id: 값}                        = Survey.answers["responses"]
  answers   : {"responses": {...}, "absolute": [...]} = Survey.answers 전체
"""

from collections import deque

from app.survey.catalog import QUESTIONS, Category, Question

# 설계 §3.4. 운영 데이터가 쌓이면 조정한다
CATEGORY_WEIGHT: dict[Category, float] = {
    Category.VALUES: 1.5,
    Category.RELATIONSHIP: 1.3,
    Category.LIFESTYLE: 1.0,
    Category.APPEARANCE: 0.8,
}

_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}
_PREF_SUFFIX = "_pref"


def _build_pairs() -> dict[str, tuple[Question, Question]]:
    """`X_pref` ↔ `X_self` 짝을 카탈로그에서 뽑는다. 짝 없는 _pref는 설정 오류다."""
    pairs: dict[str, tuple[Question, Question]] = {}
    for q in QUESTIONS:
        if not q.id.endswith(_PREF_SUFFIX):
            continue
        base = q.id[: -len(_PREF_SUFFIX)]
        self_q = _BY_ID.get(f"{base}_self")
        if self_q is None:
            raise ValueError(f"짝이 없는 _pref 문항: {q.id}")
        pairs[base] = (q, self_q)
    return pairs


PAIRS: dict[str, tuple[Question, Question]] = _build_pairs()


# ── 값 도우미 ──────────────────────────────────────────────

def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def _is_empty(value) -> bool:
    return value is None or value == "" or (isinstance(value, list) and not value)


def _is_no_pref(question: Question, value) -> bool:
    if question.no_pref_id is None:
        return False
    if value == question.no_pref_id:
        return True
    return isinstance(value, list) and question.no_pref_id in value


def _step(diff: int) -> float:
    """순서형 3단계 공통: 차이 0→1.0, 1→0.5, 2 이상→0.0"""
    return {0: 1.0, 1: 0.5}.get(diff, 0.0)


def _ordinal(order: dict[str, int]):
    def rule(pref, self_value):
        i, j = order.get(pref), order.get(self_value)
        if i is None or j is None:
            return None
        return _step(abs(i - j))
    return rule


def _table(table: dict[str, dict[str, float]]):
    """행=pref, 열=self 매핑표. 표에 없는 값이면 판정 불가(None)."""
    def rule(pref, self_value):
        row = table.get(pref)
        return None if row is None else row.get(self_value)
    return rule


# ── 문항별 규칙 (설계 §3.2) ────────────────────────────────

_HEIGHT_PREF_INDEX = {"u165": 0, "165_175": 1, "175_185": 2, "o185": 3}


def _height_index(cm) -> int | None:
    if isinstance(cm, bool) or not isinstance(cm, (int, float)):
        return None
    if cm < 165:
        return 0
    if cm < 175:
        return 1
    if cm < 185:
        return 2
    return 3


def _height(pref, self_value):
    i, j = _HEIGHT_PREF_INDEX.get(pref), _height_index(self_value)
    if i is None or j is None:
        return None
    return _step(abs(i - j))


def _contains(pref, self_value):
    return 1.0 if self_value in _as_list(pref) else 0.0


def _intersects(pref, self_value):
    return 1.0 if set(_as_list(pref)) & set(_as_list(self_value)) else 0.0


def _body_mark(pref, self_value):
    """문신·피어싱 공통. ok는 무조건 만족, none은 '없음'만 만족."""
    if pref == "ok":
        return 1.0
    if pref != "none":
        return None
    return 1.0 if self_value == "no" else 0.0


_POLITICS_ORDER = {"progressive": 0, "moderate": 1, "conservative": 2}


def _politics(pref, self_value):
    if self_value == "unknown":  # 판정 불가라 중간값
        return 0.5
    return _ordinal(_POLITICS_ORDER)(pref, self_value)


def _religion(pref, self_value):
    if self_value == "other":  # 세부 종교를 모르니 중간값
        return 0.5
    return _contains(pref, self_value)


def _scale(pref, self_value):
    """1~5 척도. 1 − |차이| / 4"""
    if isinstance(pref, bool) or isinstance(self_value, bool):
        return None
    if not isinstance(pref, (int, float)) or not isinstance(self_value, (int, float)):
        return None
    return 1 - abs(pref - self_value) / 4


def _exact(pref, self_value):
    return 1.0 if pref == self_value else 0.0


_RANK_MAX_DISTANCE = 8  # 4개 항목이 완전 역순일 때의 순위차 합


def _priority_rank(pref, self_value):
    a, b = _as_list(pref), _as_list(self_value)
    if len(a) != 4 or sorted(a) != sorted(b):
        return None
    position = {item: i for i, item in enumerate(b)}
    distance = sum(abs(i - position[item]) for i, item in enumerate(a))
    return 1 - distance / _RANK_MAX_DISTANCE


_COST_SHARE = {
    "dutch": {"dutch": 1.0, "alternate": 0.5, "richer": 0.5, "me": 0.5},
    "alternate": {"dutch": 0.5, "alternate": 1.0, "richer": 0.5, "me": 0.5},
    "richer": {"dutch": 0.5, "alternate": 0.5, "richer": 1.0, "me": 0.5},
    "partner": {"dutch": 0.0, "alternate": 0.5, "richer": 0.5, "me": 1.0},
}
_SMOKING = {
    "none_only": {"none": 1.0, "sometimes": 0.0, "yes": 0.0},
    "sometimes_ok": {"none": 1.0, "sometimes": 1.0, "yes": 0.0},
}
_DRINKING = {
    "none": {"none": 1.0, "sometimes": 0.5, "often": 0.0},
    "sometimes_ok": {"none": 1.0, "sometimes": 1.0, "often": 0.5},
}
_HOBBY = {
    "indoor": {"indoor": 1.0, "outdoor": 0.0, "both": 1.0},
    "outdoor": {"indoor": 0.0, "outdoor": 1.0, "both": 1.0},
}
_LIVING = {"prefer_independent": {"independent": 1.0, "dorm": 0.5, "home": 0.0}}


# ── 거주지 (설계 §3.3) ────────────────────────────────────

_ADJACENT: dict[str, tuple[str, ...]] = {
    "서울": ("인천", "경기"),
    "인천": ("서울", "경기"),
    "경기": ("서울", "인천", "강원", "충북", "충남"),
    "강원": ("경기", "충북", "경북"),
    "충북": ("경기", "강원", "충남", "세종", "대전", "경북", "전북"),
    "충남": ("경기", "충북", "세종", "대전", "전북"),
    "세종": ("충북", "충남", "대전"),
    "대전": ("충북", "충남", "세종"),
    "전북": ("충남", "충북", "전남", "경남", "경북"),
    "전남": ("전북", "광주", "경남"),
    "광주": ("전남",),
    "경북": ("강원", "충북", "전북", "경남", "대구", "울산"),
    "대구": ("경북",),
    "경남": ("전북", "전남", "경북", "부산", "울산"),
    "부산": ("경남", "울산"),
    "울산": ("경남", "경북", "부산"),
    "제주": (),  # 육로 연결 없음
}

# 홉 수 → 만족도. 표에 없는 홉 수(연결 없음 포함)는 0.0
_RESIDENCE_TABLE = {
    "h1": {0: 1.0, 1: 0.5},
    "h2": {0: 1.0, 1: 1.0, 2: 0.5},
    "h3": {0: 1.0, 1: 1.0, 2: 1.0},
}


def _hops(start: str, goal: str) -> int | None:
    """인접 그래프 최단 홉. 도달 불가면 None."""
    if start not in _ADJACENT or goal not in _ADJACENT:
        return None
    if start == goal:
        return 0
    seen = {start}
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        for nxt in _ADJACENT[node]:
            if nxt in seen:
                continue
            if nxt == goal:
                return depth + 1
            seen.add(nxt)
            queue.append((nxt, depth + 1))
    return None


def _residence(pref, my_sido, their_sido):
    table = _RESIDENCE_TABLE.get(pref)
    if table is None or _is_empty(my_sido) or _is_empty(their_sido):
        return None
    hops = _hops(my_sido, their_sido)
    return 0.0 if hops is None else table.get(hops, 0.0)


_RULES = {
    "height": _height,
    "face": _contains,
    "style": _intersects,
    "tattoo": _body_mark,
    "piercing": _body_mark,
    "politics": _politics,
    "religion": _religion,
    "contact_freq": _scale,
    "date_freq": _scale,
    "alone_time": _scale,
    "affection": _scale,
    "conflict_style": _exact,
    "priority_rank": _priority_rank,
    "date_budget": _ordinal({"u5": 0, "5_10": 1, "10_20": 2, "20_30": 3, "o30": 4}),
    "cost_share": _table(_COST_SHARE),
    "smoking": _table(_SMOKING),
    "drinking": _table(_DRINKING),
    "exercise": _ordinal({"none": 0, "w1_2": 1, "w3": 2}),
    "sleep": _exact,
    "hobby": _table(_HOBBY),
    "living": _table(_LIVING),
    # residence는 '내 거주지'가 더 필요해 satisfaction()에서 따로 처리한다
}


def satisfaction(base: str, pref_responses: dict, self_responses: dict) -> float | None:
    """`base` 문항 한 쌍의 만족도. `None`이면 계산에서 제외한다 (설계 §3.1)."""
    pref_q, self_q = PAIRS[base]
    pref_value = pref_responses.get(pref_q.id)
    self_value = self_responses.get(self_q.id)
    if _is_empty(pref_value) or _is_empty(self_value):
        return None
    if _is_no_pref(pref_q, pref_value):
        return None
    if base == "residence":
        return _residence(pref_value, pref_responses.get("residence_self"), self_value)
    return _RULES[base](pref_value, self_value)
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_scoring.py -v`
Expected: PASS (전부)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services backend/tests/test_scoring.py
git commit -m "$(cat <<'EOF'
feat(backend): scoring.py 문항 만족도 계산

카탈로그에서 _pref ↔ _self 짝을 뽑아 문항 유형별 규칙 적용.
거주지는 인접 시·도 그래프 홉 수로 근사.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: scoring.py — 방향 점수·페어 점수·절대질문 필터

**Files:**
- Modify: `backend/app/services/scoring.py` (파일 끝에 추가)
- Test: `backend/tests/test_scoring.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: Task 2의 `PAIRS`, `CATEGORY_WEIGHT`, `satisfaction`
- Produces:
  - `direction_score(pref_responses: dict, self_responses: dict) -> float` — 0~100
  - `pair_score(a_answers: dict, b_answers: dict) -> float` — `min(A→B, B→A)`
  - `absolute_ok(pref_answers: dict, self_responses: dict) -> bool`
  - `pair_allowed(a_answers: dict, b_answers: dict) -> bool` — 양방향 절대질문 통과 여부

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_scoring.py` 끝에 추가 (상단 import에 `absolute_ok, direction_score, pair_allowed, pair_score` 추가):

```python
from app.services.scoring import (  # noqa: E402  (파일 상단 import에 합칠 것)
    absolute_ok,
    direction_score,
    pair_allowed,
    pair_score,
)


def _answers(responses: dict, absolute: list[str] | None = None) -> dict:
    return {"responses": responses, "absolute": absolute or []}


def test_direction_score_is_percentage_of_answered_questions():
    """만족 1개 + 불만족 1개 = 가중치 비율대로 환산된다."""
    pref = {"sleep_pref": "night", "hobby_pref": "indoor"}
    self_ = {"sleep_self": "night", "hobby_self": "outdoor"}
    # 둘 다 LIFESTYLE(가중치 1.0) → (1.0 + 0.0) / 2.0 × 100 = 50
    assert direction_score(pref, self_) == 50.0


def test_category_weight_is_applied():
    """가치관(1.5)만 만족, 외모(0.8)만 불만족 → 1.5 / 2.3 × 100"""
    pref = {"politics_pref": "moderate", "tattoo_pref": "none"}
    self_ = {"politics_self": "moderate", "tattoo_self": "yes"}
    assert direction_score(pref, self_) == pytest.approx(1.5 / 2.3 * 100)


def test_direction_score_is_zero_when_nothing_comparable():
    """비교 가능한 문항이 하나도 없으면 0. 0으로 나누지 않는다 (설계 §3.5)."""
    assert direction_score({}, {}) == 0.0
    assert direction_score({"sleep_pref": "any"}, {"sleep_self": "night"}) == 0.0


def test_pair_score_takes_the_lower_direction():
    a = _answers({"sleep_pref": "night", "sleep_self": "morning"})
    b = _answers({"sleep_pref": "morning", "sleep_self": "night"})
    # A→B: A가 원하는 night를 B가 만족 → 100 / B→A: B가 원하는 morning을 A가 만족 → 100
    assert pair_score(a, b) == 100.0

    c = _answers({"sleep_pref": "night", "sleep_self": "night"})
    d = _answers({"sleep_pref": "morning", "sleep_self": "night"})
    # C→D 100, D→C 0 → min = 0
    assert pair_score(c, d) == 0.0


def test_absolute_question_must_be_fully_satisfied():
    picky = _answers({"sleep_pref": "night"}, absolute=["sleep_pref"])
    assert absolute_ok(picky, {"sleep_self": "night"}) is True
    assert absolute_ok(picky, {"sleep_self": "morning"}) is False


def test_absolute_scale_question_allows_one_step():
    """척도형만 0.75까지 완화 (설계 §3.6)."""
    picky = _answers({"contact_freq_pref": 3}, absolute=["contact_freq_pref"])
    assert absolute_ok(picky, {"contact_freq_self": 4}) is True   # 0.75
    assert absolute_ok(picky, {"contact_freq_self": 5}) is False  # 0.5


def test_absolute_passes_when_undecidable():
    """상대가 미응답이라 판정 불가면 통과시킨다 (설계 §3.6)."""
    picky = _answers({"sleep_pref": "night"}, absolute=["sleep_pref"])
    assert absolute_ok(picky, {}) is True


def test_pair_allowed_checks_both_directions():
    a = _answers({"sleep_pref": "night", "sleep_self": "morning"}, absolute=["sleep_pref"])
    b = _answers({"sleep_self": "night"})
    assert pair_allowed(a, b) is True

    strict_b = _answers({"sleep_pref": "night", "sleep_self": "night"}, absolute=["sleep_pref"])
    # B의 절대질문(night)을 A(morning)가 어긴다
    assert pair_allowed(a, strict_b) is False
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_scoring.py -v`
Expected: FAIL — `ImportError: cannot import name 'direction_score'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/scoring.py` 끝에 추가:

```python
# ── 집계 (설계 §3.5) ──────────────────────────────────────

def direction_score(pref_responses: dict, self_responses: dict) -> float:
    """"내 선호를 상대가 얼마나 만족하나"를 0~100으로. 제외 문항은 분모에서도 빠진다."""
    numerator = denominator = 0.0
    for base, (pref_q, _) in PAIRS.items():
        value = satisfaction(base, pref_responses, self_responses)
        if value is None:
            continue
        weight = CATEGORY_WEIGHT[pref_q.category]
        numerator += value * weight
        denominator += weight
    if denominator == 0:
        return 0.0  # 비교 가능한 문항 없음. 0으로 나누지 않는다
    return numerator / denominator * 100


def pair_score(a_answers: dict, b_answers: dict) -> float:
    """페어 점수 = min(A→B, B→A). 한쪽만 만족하는 짝을 걸러낸다."""
    a_responses = a_answers.get("responses") or {}
    b_responses = b_answers.get("responses") or {}
    return min(
        direction_score(a_responses, b_responses),
        direction_score(b_responses, a_responses),
    )


# ── 절대질문 하드필터 (설계 §3.6) ─────────────────────────

_SCALE_BASES = {"contact_freq", "date_freq", "alone_time", "affection"}
ABSOLUTE_SCALE_MIN = 0.75


def absolute_ok(pref_answers: dict, self_responses: dict) -> bool:
    """pref 쪽이 지정한 절대질문을 상대가 전부 만족하는가."""
    pref_responses = pref_answers.get("responses") or {}
    for qid in pref_answers.get("absolute") or []:
        if not qid.endswith(_PREF_SUFFIX):
            continue
        base = qid[: -len(_PREF_SUFFIX)]
        if base not in PAIRS:
            continue
        value = satisfaction(base, pref_responses, self_responses)
        if value is None:
            continue  # 판정 불가는 탈락 사유로 쓰지 않는다
        threshold = ABSOLUTE_SCALE_MIN if base in _SCALE_BASES else 1.0
        if value < threshold:
            return False
    return True


def pair_allowed(a_answers: dict, b_answers: dict) -> bool:
    """양쪽 절대질문을 모두 통과해야 후보로 남는다."""
    a_responses = a_answers.get("responses") or {}
    b_responses = b_answers.get("responses") or {}
    return absolute_ok(a_answers, b_responses) and absolute_ok(b_answers, a_responses)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_scoring.py -v`
Expected: PASS (전부)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "$(cat <<'EOF'
feat(backend): 방향 점수·페어 점수·절대질문 하드필터

페어 점수는 min(A→B, B→A) — 한쪽만 만족하는 짝을 막는다.
비교 가능 문항이 0개면 0점 (0 나눗셈 회피).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: pairing.py — 최적 조합

**Files:**
- Modify: `backend/pyproject.toml` (networkx 의존성)
- Create: `backend/app/services/pairing.py`
- Test: `backend/tests/test_pairing.py`

**Interfaces:**
- Consumes: 없음 (숫자만 다룬다)
- Produces: `optimal_pairs(scores: Mapping[tuple[int, int], float]) -> list[tuple[int, int]]` — 점수 합이 최대인 짝 목록. 각 튜플은 `(작은 id, 큰 id)`, 반환 목록은 정렬됨

- [ ] **Step 1: 의존성 추가**

```bash
cd backend; uv add networkx
```

Expected: `pyproject.toml`의 `dependencies`에 `networkx>=3` 계열이 추가된다.

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_pairing.py` 새 파일:

```python
from app.services.pairing import optimal_pairs


def test_empty_input():
    assert optimal_pairs({}) == []


def test_single_pair():
    assert optimal_pairs({(1, 2): 50.0}) == [(1, 2)]


def test_beats_greedy():
    """그리디였다면 틀렸을 케이스 (설계 §11).

    가장 비싼 간선 1-3(10점)을 먼저 집으면 2-4(1점)밖에 안 남아 합 11.
    최적은 1-4(9) + 2-3(9) = 18.
    """
    scores = {
        (1, 3): 10.0,
        (1, 4): 9.0,
        (2, 3): 9.0,
        (2, 4): 1.0,
    }
    assert optimal_pairs(scores) == [(1, 4), (2, 3)]


def test_zero_score_pairs_are_still_matched():
    """최소 점수 컷이 없다 — 0점짜리도 짝지어야 한다 (설계 §1)."""
    assert optimal_pairs({(1, 2): 0.0}) == [(1, 2)]


def test_prefers_matching_more_people():
    """1-2를 붙이면 3,4가 남는다. 셋 다 붙는 조합이 이긴다."""
    scores = {(1, 2): 40.0, (1, 3): 20.0, (2, 4): 20.0}
    assert optimal_pairs(scores) == [(1, 3), (2, 4)]


def test_ties_prefer_smaller_ids():
    """동점이면 작은 id 우선 (설계 §5.2)."""
    scores = {(1, 3): 50.0, (1, 4): 50.0, (2, 3): 50.0, (2, 4): 50.0}
    assert optimal_pairs(scores) == [(1, 3), (2, 4)]


def test_is_deterministic():
    scores = {
        (1, 4): 70.0, (1, 5): 70.0, (1, 6): 70.0,
        (2, 4): 70.0, (2, 5): 70.0, (2, 6): 70.0,
        (3, 4): 70.0, (3, 5): 70.0, (3, 6): 70.0,
    }
    assert optimal_pairs(scores) == optimal_pairs(scores)


def test_leftover_when_counts_differ():
    """3명 대 1명 — 한 쌍만 나오고 나머지는 미매칭 (설계 §5.3)."""
    scores = {(1, 4): 10.0, (2, 4): 30.0, (3, 4): 20.0}
    assert optimal_pairs(scores) == [(2, 4)]
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_pairing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.pairing'`

- [ ] **Step 4: 구현**

`backend/app/services/pairing.py` 새 파일:

```python
"""점수표 → 최적 짝. 유저·설문을 모른다 (설계 §2.1)."""

from collections.abc import Mapping

import networkx as nx

_SCALE = 1000  # 소수점 점수를 정수로. 정수라야 아래 tie-break 계산이 정확하다
_MATCH_BONUS = 1  # 0점 페어도 매칭되게 하는 최소 가중치 (최소 점수 컷 없음)


def optimal_pairs(scores: Mapping[tuple[int, int], float]) -> list[tuple[int, int]]:
    """점수 합이 최대가 되는 짝 목록. 같은 입력은 항상 같은 결과를 낸다.

    가중치를 `점수 × BIG − tie` 형태의 정수로 만든다. tie 항의 총합이 BIG보다
    작으므로 점수 합이 항상 우선하고, 점수가 같을 때만 tie가 승부를 가른다.

    tie는 페어 폭 `(b − a)²`이다. 제곱이라 폭이 넓은 페어가 급격히 손해를 보고,
    그 결과 동점일 때는 작은 id끼리 먼저 묶이는 조합이 이긴다 (설계 §5.2).
    """
    if not scores:
        return []

    normalized = {
        ((a, b) if a < b else (b, a)): value for (a, b), value in scores.items()
    }
    ids = sorted({node for key in normalized for node in key})
    span = ids[-1] + 1
    tie_bound = span * span            # (b − a)² 의 상한
    big = tie_bound * (len(ids) // 2 + 1)  # 한 매칭에 들어갈 수 있는 tie 총합보다 크다

    graph = nx.Graph()
    graph.add_nodes_from(ids)  # 정렬된 순서로 넣어 순회 순서를 고정한다
    for a, b in sorted(normalized):
        base = int(round(normalized[(a, b)] * _SCALE)) + _MATCH_BONUS
        graph.add_edge(a, b, weight=base * big - (b - a) ** 2)

    matched = nx.max_weight_matching(graph, maxcardinality=False)
    return sorted((a, b) if a < b else (b, a) for a, b in matched)
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_pairing.py -v`
Expected: PASS (8 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/services/pairing.py backend/tests/test_pairing.py
git commit -m "$(cat <<'EOF'
feat(backend): pairing.py 전체 최적 매칭 (networkx)

그리디 대신 max_weight_matching. 금지 페어는 '간선 없음'으로 표현된다.
동점 시 작은 id 우선 — 정수 가중치 tie-break로 결정론성 확보.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: matching.py — 풀 구성·하드필터·이월 보너스

**Files:**
- Create: `backend/app/services/matching.py`
- Test: `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: Task 3의 `pair_allowed`, `pair_score` / Task 4의 `optimal_pairs` / Task 1의 모델 변경
- Produces:
  - `CARRYOVER_PER_ROUND = 15`, `CARRYOVER_CAP = 45`, `UNIVERSITY_BONUS = 0`
  - `eligible_users(db) -> list[User]`
  - `past_pairs(db) -> set[tuple[int, int]]`
  - `carryover_bonus(user: User) -> int`
  - `pair_key(a: int, b: int) -> tuple[int, int]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_matching.py` 새 파일:

```python
from datetime import datetime, timedelta

from app.models.match import Match, MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from app.services import matching
from tests.conftest import TestingSessionLocal


def make_user(
    db,
    email: str,
    gender: Gender = Gender.male,
    responses: dict | None = None,
    absolute: list[str] | None = None,
    status: UserStatus = UserStatus.active,
    paused: bool = False,
    missed_rounds: int = 0,
    with_survey: bool = True,
    name: str = "테스트",
    university: str = "서울대학교",
) -> User:
    user = User(
        email=email, password_hash="x", name=name, university=university,
        gender=gender, status=status, matching_paused=paused,
        missed_rounds=missed_rounds,
    )
    db.add(user)
    db.commit()
    if with_survey:
        db.add(Survey(user_id=user.id, answers={
            "responses": responses or {}, "absolute": absolute or [],
        }))
        db.commit()
    db.refresh(user)
    return user


def make_round(db) -> MatchRound:
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    db.refresh(round_)
    return round_


def test_eligible_pool_requires_active_unpaused_and_survey():
    db = TestingSessionLocal()
    ok = make_user(db, "ok@test.com")
    make_user(db, "pending@test.com", status=UserStatus.pending)
    make_user(db, "paused@test.com", paused=True)
    make_user(db, "nosurvey@test.com", with_survey=False)

    assert [u.id for u in matching.eligible_users(db)] == [ok.id]
    db.close()


def test_past_pairs_are_collected_regardless_of_round():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male)
    b = make_user(db, "b@test.com", Gender.female)
    round_ = make_round(db)
    db.add(Match(user_a_id=b.id, user_b_id=a.id, match_round_id=round_.id, score=50))
    db.commit()

    assert matching.past_pairs(db) == {matching.pair_key(a.id, b.id)}
    db.close()


def test_carryover_bonus_is_capped():
    db = TestingSessionLocal()
    fresh = make_user(db, "fresh@test.com", missed_rounds=0)
    twice = make_user(db, "twice@test.com", missed_rounds=2)
    long_wait = make_user(db, "long@test.com", missed_rounds=10)

    assert matching.carryover_bonus(fresh) == 0
    assert matching.carryover_bonus(twice) == 30
    assert matching.carryover_bonus(long_wait) == 45  # 상한
    db.close()


def test_pair_key_is_order_independent():
    assert matching.pair_key(7, 3) == matching.pair_key(3, 7) == (3, 7)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: FAIL — `ImportError: cannot import name 'matching'`

- [ ] **Step 3: 구현**

`backend/app/services/matching.py` 새 파일:

```python
"""매칭 파이프라인 오케스트레이션 (설계 §2). HTTP는 모른다."""

from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.survey import Survey
from app.models.user import User, UserStatus

# 설계 §4.1 — 상한이 없으면 대기자끼리 묶이는 최악 궁합 매칭이 양산된다
CARRYOVER_PER_ROUND = 15
CARRYOVER_CAP = 45

# 설계 §4.2는 3단계 작업이다. 지금은 자리만 마련해 둔다
UNIVERSITY_BONUS = 0


def pair_key(a: int, b: int) -> tuple[int, int]:
    """페어를 순서 무관하게 다루기 위한 정규화 키."""
    return (a, b) if a < b else (b, a)


def eligible_users(db: Session) -> list[User]:
    """매칭 자격: active + 일시정지 OFF + 설문 행 존재 (설계 §6.2).

    응답 개수는 따지지 않는다 — 부분 응답도 풀에 넣는다.
    """
    return (
        db.query(User)
        .join(Survey, Survey.user_id == User.id)
        .filter(
            User.status == UserStatus.active,
            User.matching_paused.is_(False),
        )
        .order_by(User.id)
        .all()
    )


def past_pairs(db: Session) -> set[tuple[int, int]]:
    """한 번이라도 짝이었던 페어. 라운드와 무관하게 영구 제외한다 (설계 §5.4)."""
    return {
        pair_key(a, b)
        for a, b in db.query(Match.user_a_id, Match.user_b_id).all()
    }


def carryover_bonus(user: User) -> int:
    """미매칭 라운드마다 쌓이는 보너스. 상한 있음 (설계 §4.1)."""
    return min(user.missed_rounds * CARRYOVER_PER_ROUND, CARRYOVER_CAP)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/matching.py backend/tests/test_matching.py
git commit -m "$(cat <<'EOF'
feat(backend): 매칭 풀 구성·과거 이력·이월 보너스

풀 자격은 active + 일시정지 OFF + 설문 행 존재.
이월 보너스는 15점씩 쌓되 45점 상한 — 궁합을 뒤집지 못하게.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: matching.py — 게임 보정과 보장 충돌 해소

**Files:**
- Modify: `backend/app/services/matching.py` (파일 끝에 추가)
- Test: `backend/tests/test_matching.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: Task 5의 `pair_key`
- Produces:
  - `OJAKGYO_BONUS = 33`, `OJAKGYO_GUARANTEE_COUNT = 3`
  - `game_signals(db, pool: list[User]) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]` — (붉은실 상호 페어, 오작교 지목자 수)
  - `resolve_guarantees(red, ojakgyo, score) -> list[tuple[int, int]]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_matching.py` 끝에 추가:

```python
from app.models.game import Ojakgyo, RedThread


def test_red_thread_needs_both_directions():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.female, name="박여자", university="B대")
    db.add(RedThread(user_id=a.id, target_name="박여자", target_university="B대"))
    db.commit()

    pool = matching.eligible_users(db)
    red, _ = matching.game_signals(db, pool)
    assert red == set()  # 한쪽만 입력 → 상호 아님

    db.add(RedThread(user_id=b.id, target_name="김남자", target_university="A대"))
    db.commit()
    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == {matching.pair_key(a.id, b.id)}
    db.close()


def test_same_gender_red_thread_is_ignored():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.male, name="이남자", university="B대")
    db.add_all([
        RedThread(user_id=a.id, target_name="이남자", target_university="B대"),
        RedThread(user_id=b.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()

    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == set()  # 남녀 1:1 전제 (설계 §4.3)
    db.close()


def test_duplicate_name_and_university_is_ignored():
    """이름+학교가 유일하지 않으면 게임 효과를 적용하지 않는다 (설계 §4.4)."""
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    make_user(db, "twin1@test.com", Gender.female, name="박여자", university="B대")
    twin2 = make_user(db, "twin2@test.com", Gender.female, name="박여자", university="B대")
    db.add_all([
        RedThread(user_id=a.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=twin2.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()

    red, _ = matching.game_signals(db, matching.eligible_users(db))
    assert red == set()
    db.close()


def test_ojakgyo_counts_recommenders():
    db = TestingSessionLocal()
    a = make_user(db, "a@test.com", Gender.male, name="김남자", university="A대")
    b = make_user(db, "b@test.com", Gender.female, name="박여자", university="B대")
    r1 = make_user(db, "r1@test.com", Gender.female, name="추천1", university="C대")
    r2 = make_user(db, "r2@test.com", Gender.male, name="추천2", university="C대")
    for recommender in (r1, r2):
        db.add(Ojakgyo(
            recommender_id=recommender.id,
            person_a_name="김남자", person_a_university="A대",
            person_b_name="박여자", person_b_university="B대",
        ))
    db.commit()

    _, counts = matching.game_signals(db, matching.eligible_users(db))
    assert counts == {matching.pair_key(a.id, b.id): 2}
    db.close()


def test_red_thread_wins_over_ojakgyo_when_a_user_is_in_both():
    """붉은실 상호 > 오작교 3인 (설계 §4.3)."""
    red = {(1, 2)}
    ojakgyo = {(1, 3)}
    score = {(1, 2): 40.0, (1, 3): 90.0}
    assert matching.resolve_guarantees(red, ojakgyo, score) == [(1, 2)]


def test_same_tier_conflict_prefers_higher_score():
    red = {(1, 2), (1, 3)}
    score = {(1, 2): 40.0, (1, 3): 90.0}
    assert matching.resolve_guarantees(red, set(), score) == [(1, 3)]


def test_same_tier_tie_prefers_smaller_user_id():
    red = {(1, 3), (1, 2)}
    score = {(1, 2): 50.0, (1, 3): 50.0}
    assert matching.resolve_guarantees(red, set(), score) == [(1, 2)]


def test_non_conflicting_guarantees_all_survive():
    red = {(1, 2)}
    ojakgyo = {(3, 4)}
    score = {(1, 2): 10.0, (3, 4): 10.0}
    assert matching.resolve_guarantees(red, ojakgyo, score) == [(1, 2), (3, 4)]
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: FAIL — `AttributeError: module 'app.services.matching' has no attribute 'game_signals'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/matching.py` 상단 import에 다음을 더한다:

```python
from collections import Counter, defaultdict

from app.models.game import Ojakgyo, RedThread
```

그리고 파일 끝에 추가:

```python
# 설계 §4.3 — 상위 스펙의 "+33%"를 100점 만점 기준 점수로 환산
OJAKGYO_BONUS = 33
OJAKGYO_GUARANTEE_COUNT = 3


def _identity_resolver(db: Session):
    """이름+학교가 유일할 때만 유저를 특정한다 (설계 §4.4).

    학번(admission_year)은 아직 없다 — 도입 전까지 이름+학교로만 판정하되
    '유일할 때만 적용' 규칙은 그대로 지킨다. 2명 이상이면 무시(None).
    """
    index: dict[tuple[str, str], list[int]] = defaultdict(list)
    for user_id, name, university in db.query(
        User.id, User.name, User.university
    ).all():
        index[(name.strip(), university.strip())].append(user_id)

    def resolve(name: str, university: str) -> int | None:
        hits = index.get((name.strip(), university.strip()), [])
        return hits[0] if len(hits) == 1 else None

    return resolve


def game_signals(
    db: Session, pool: list[User]
) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    """(붉은실 상호 페어, 페어별 오작교 지목자 수).

    둘 다 풀 안에 있고 성별이 다른 페어만 남긴다 — 남녀 1:1 전제.
    """
    by_id = {user.id: user for user in pool}
    resolve = _identity_resolver(db)

    def usable(a: int, b: int) -> bool:
        left, right = by_id.get(a), by_id.get(b)
        return left is not None and right is not None and left.gender != right.gender

    targets: dict[int, set[int]] = defaultdict(set)
    for thread in db.query(RedThread).all():
        target_id = resolve(thread.target_name, thread.target_university)
        if target_id is not None:
            targets[thread.user_id].add(target_id)

    red: set[tuple[int, int]] = set()
    for user_id, target_ids in targets.items():
        for target_id in target_ids:
            if user_id in targets.get(target_id, set()) and usable(user_id, target_id):
                red.add(pair_key(user_id, target_id))

    counts: Counter[tuple[int, int]] = Counter()
    for entry in db.query(Ojakgyo).all():
        a = resolve(entry.person_a_name, entry.person_a_university)
        b = resolve(entry.person_b_name, entry.person_b_university)
        # 같은 지목자가 같은 쌍을 두 번 넣는 건 DB 유니크 제약이 이미 막는다
        if a is None or b is None or a == b or not usable(a, b):
            continue
        counts[pair_key(a, b)] += 1

    return red, dict(counts)


def resolve_guarantees(
    red: set[tuple[int, int]],
    ojakgyo: set[tuple[int, int]],
    score: dict[tuple[int, int], float],
) -> list[tuple[int, int]]:
    """보장 충돌 해소 (설계 §4.3).

    우선순위: 붉은실 상호 > 오작교 3인 → 궁합 점수 높은 쪽 → user_id 작은 쪽.
    버려진 페어는 일반 매칭 풀로 돌아간다(여기서 반환하지 않는 것이 곧 그 뜻).
    """
    ranked = sorted(
        [(0, pair) for pair in red] + [(1, pair) for pair in ojakgyo],
        key=lambda item: (item[0], -score.get(item[1], 0.0), item[1]),
    )
    used: set[int] = set()
    confirmed: list[tuple[int, int]] = []
    for _, (a, b) in ranked:
        if a in used or b in used:
            continue
        used.update((a, b))
        confirmed.append((a, b))
    return confirmed
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: PASS (12 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/matching.py backend/tests/test_matching.py
git commit -m "$(cat <<'EOF'
feat(backend): 게임 보정 — 붉은실 상호·오작교 지목 수

이름+학교가 유일할 때만 유저를 특정한다(동명이인 오적용 차단).
보장 충돌은 붉은실 > 오작교 > 높은 점수 > 작은 id 순으로 해소.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: matching.py — run_matching 오케스트레이션

**Files:**
- Modify: `backend/app/services/matching.py` (파일 끝에 추가)
- Test: `backend/tests/test_matching.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: Task 5·6의 모든 함수, Task 3의 `pair_allowed`·`pair_score`, Task 4의 `optimal_pairs`
- Produces:
  - `class RoundNotFound(Exception)` / `class RoundNotPending(Exception)`
  - `@dataclass(frozen=True) class MatchingResult: matched: int; unmatched: int; guaranteed: int`
  - `run_matching(db: Session, round_id: int) -> MatchingResult`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_matching.py` 끝에 추가:

```python
import pytest


NIGHT = {"sleep_self": "night", "sleep_pref": "night"}
MORNING = {"sleep_self": "morning", "sleep_pref": "morning"}


def test_run_matching_pairs_and_marks_round_done():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 1
    assert result.unmatched == 0
    assert result.guaranteed == 0
    saved = db.query(Match).one()
    assert (saved.user_a_id, saved.user_b_id) == matching.pair_key(man.id, woman.id)
    assert saved.score == 100
    db.refresh(round_)
    assert round_.status == RoundStatus.done
    assert round_.executed_at is not None
    db.close()


def test_absolute_question_removes_the_pair():
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male,
              responses=NIGHT, absolute=["sleep_pref"])
    make_user(db, "w@test.com", Gender.female, responses=MORNING)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 0
    assert result.unmatched == 2
    assert db.query(Match).count() == 0
    db.close()


def test_past_pair_is_never_rematched():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    old = make_round(db)
    db.add(Match(user_a_id=man.id, user_b_id=woman.id,
                 match_round_id=old.id, score=100))
    old.status = RoundStatus.done
    db.commit()

    fresh = make_round(db)
    result = matching.run_matching(db, fresh.id)

    assert result.matched == 0
    assert db.query(Match).filter(Match.match_round_id == fresh.id).count() == 0
    db.close()


def test_missed_rounds_reset_and_increment():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT, missed_rounds=2)
    woman = make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    lonely = make_user(db, "l@test.com", Gender.female, responses=NIGHT, missed_rounds=1)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    db.refresh(man), db.refresh(woman), db.refresh(lonely)
    assert man.missed_rounds == 0
    assert woman.missed_rounds == 0
    assert lonely.missed_rounds == 2  # 풀에 있었지만 못 붙었다
    db.close()


def test_paused_user_missed_rounds_untouched():
    """풀에 없는 유저는 우선순위를 쌓지 못한다 (설계 §4.1)."""
    db = TestingSessionLocal()
    paused = make_user(db, "p@test.com", Gender.female,
                       responses=NIGHT, paused=True, missed_rounds=1)
    make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    db.refresh(paused)
    assert paused.missed_rounds == 1
    db.close()


def test_carryover_bonus_cannot_override_compatibility():
    """이월 보너스는 순위를 밀어줄 뿐 궁합을 뒤집지 못한다 — 상한의 목적 (설계 §4.1)."""
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    good = make_user(db, "good@test.com", Gender.female, responses=NIGHT)
    waiting = make_user(db, "wait@test.com", Gender.female,
                        responses=MORNING, missed_rounds=3)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)

    partner = db.query(Match).one()
    # 궁합만 보면 good(100점)이지만 waiting은 45점 보너스 → 0 + 45 > 100? 아니다.
    # 보너스가 궁합을 뒤집지 못하는 것이 상한의 목적이다
    assert waiting.id not in (partner.user_a_id, partner.user_b_id)
    assert good.id in (partner.user_a_id, partner.user_b_id)
    assert man.id in (partner.user_a_id, partner.user_b_id)
    db.close()


def test_red_thread_guarantees_the_pair():
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=MORNING,
                    name="김남자", university="A대")
    fated = make_user(db, "f@test.com", Gender.female, responses=MORNING,
                      name="박여자", university="B대")
    better = make_user(db, "b@test.com", Gender.female, responses=MORNING,
                       name="최여자", university="C대")
    db.add_all([
        RedThread(user_id=man.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=fated.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.guaranteed == 1
    saved = db.query(Match).one()
    assert saved.user_a_id in (man.id, fated.id)
    assert saved.user_b_id in (man.id, fated.id)
    assert better.id not in (saved.user_a_id, saved.user_b_id)
    db.close()


def test_absolute_question_beats_a_guarantee():
    """절대질문이 보장을 이긴다 (설계 §4.3)."""
    db = TestingSessionLocal()
    man = make_user(db, "m@test.com", Gender.male, responses=NIGHT,
                    absolute=["sleep_pref"], name="김남자", university="A대")
    fated = make_user(db, "f@test.com", Gender.female, responses=MORNING,
                      name="박여자", university="B대")
    db.add_all([
        RedThread(user_id=man.id, target_name="박여자", target_university="B대"),
        RedThread(user_id=fated.id, target_name="김남자", target_university="A대"),
    ])
    db.commit()
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.guaranteed == 0
    assert db.query(Match).count() == 0
    db.close()


def test_uneven_gender_counts_leave_people_unmatched():
    db = TestingSessionLocal()
    make_user(db, "m1@test.com", Gender.male, responses=NIGHT)
    make_user(db, "m2@test.com", Gender.male, responses=NIGHT)
    make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    result = matching.run_matching(db, round_.id)

    assert result.matched == 1
    assert result.unmatched == 1
    db.close()


def test_second_run_returns_conflict():
    db = TestingSessionLocal()
    make_user(db, "m@test.com", Gender.male, responses=NIGHT)
    make_user(db, "w@test.com", Gender.female, responses=NIGHT)
    round_ = make_round(db)

    matching.run_matching(db, round_.id)
    with pytest.raises(matching.RoundNotPending):
        matching.run_matching(db, round_.id)
    db.close()


def test_missing_round_raises():
    db = TestingSessionLocal()
    with pytest.raises(matching.RoundNotFound):
        matching.run_matching(db, 9999)
    db.close()


def test_same_input_produces_same_result():
    """결정론성 (설계 §5.2). 같은 풀을 두 라운드에 넣어도 짝이 같아야 한다."""
    db = TestingSessionLocal()
    for i in range(3):
        make_user(db, f"m{i}@test.com", Gender.male, responses=NIGHT)
        make_user(db, f"w{i}@test.com", Gender.female, responses=NIGHT)
    first = make_round(db)
    matching.run_matching(db, first.id)
    pairs_first = sorted(
        (m.user_a_id, m.user_b_id)
        for m in db.query(Match).filter(Match.match_round_id == first.id).all()
    )
    db.query(Match).delete()
    db.commit()

    second = make_round(db)
    matching.run_matching(db, second.id)
    pairs_second = sorted(
        (m.user_a_id, m.user_b_id)
        for m in db.query(Match).filter(Match.match_round_id == second.id).all()
    )
    assert pairs_first == pairs_second
    db.close()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: FAIL — `AttributeError: module 'app.services.matching' has no attribute 'run_matching'`

- [ ] **Step 3: 구현 추가**

`backend/app/services/matching.py` 상단 import에 다음을 더한다:

```python
from dataclasses import dataclass
from datetime import datetime

from app.models.match import Match, MatchRound, RoundStatus
from app.models.user import Gender  # 기존 User·UserStatus import 줄에 합쳐도 된다
from app.services.pairing import optimal_pairs
from app.services.scoring import pair_allowed, pair_score
```

파일 끝에 추가:

```python
class RoundNotFound(Exception):
    """존재하지 않는 라운드."""


class RoundNotPending(Exception):
    """이미 실행 중이거나 완료된 라운드 — 중복 실행 방어 (설계 §5.5)."""


@dataclass(frozen=True)
class MatchingResult:
    matched: int
    unmatched: int
    guaranteed: int


def run_matching(db: Session, round_id: int) -> MatchingResult:
    """라운드 하나를 실행한다. 실패하면 라운드를 pending으로 되돌린다."""
    if db.get(MatchRound, round_id) is None:
        raise RoundNotFound

    # 조건부 UPDATE 한 번으로 검사와 선점을 동시에 한다 — 경쟁 구간이 없다
    claimed = (
        db.query(MatchRound)
        .filter(MatchRound.id == round_id, MatchRound.status == RoundStatus.pending)
        .update({MatchRound.status: RoundStatus.running}, synchronize_session=False)
    )
    db.commit()
    if claimed == 0:
        raise RoundNotPending

    round_ = db.get(MatchRound, round_id)
    try:
        result = _execute(db, round_)
        db.commit()
        return result
    except Exception:
        db.rollback()
        # 중간 실패는 전부 롤백된다. 절반만 매칭된 상태는 남지 않는다 (설계 §2)
        round_.status = RoundStatus.pending
        db.commit()
        raise


def _execute(db: Session, round_: MatchRound) -> MatchingResult:
    pool = eligible_users(db)
    answers = {user.id: (user.survey.answers or {}) for user in pool}
    men = [u for u in pool if u.gender == Gender.male]
    women = [u for u in pool if u.gender == Gender.female]
    excluded = past_pairs(db)
    red, ojakgyo_counts = game_signals(db, pool)

    base: dict[tuple[int, int], float] = {}   # 보정 전 궁합 점수 (Match.score에 기록)
    adjusted: dict[tuple[int, int], float] = {}  # 보정까지 얹은 매칭용 점수
    for man in men:
        for woman in women:
            key = pair_key(man.id, woman.id)
            if key in excluded:
                continue
            if not pair_allowed(answers[man.id], answers[woman.id]):
                continue
            score = pair_score(answers[man.id], answers[woman.id])
            base[key] = score
            bonus = carryover_bonus(man) + carryover_bonus(woman) + UNIVERSITY_BONUS
            count = ojakgyo_counts.get(key, 0)
            if 0 < count < OJAKGYO_GUARANTEE_COUNT:
                bonus += OJAKGYO_BONUS * count
            adjusted[key] = score + bonus

    # 하드필터를 통과한 페어만 보장 대상이다 — 절대질문이 보장을 이긴다
    guaranteed = resolve_guarantees(
        red={key for key in red if key in base},
        ojakgyo={
            key for key, count in ojakgyo_counts.items()
            if count >= OJAKGYO_GUARANTEE_COUNT and key in base
        },
        score=adjusted,
    )
    taken = {user_id for pair in guaranteed for user_id in pair}
    remaining = {
        key: value for key, value in adjusted.items()
        if key[0] not in taken and key[1] not in taken
    }

    pairs = guaranteed + optimal_pairs(remaining)
    for a, b in pairs:
        db.add(Match(
            user_a_id=a, user_b_id=b,
            match_round_id=round_.id,
            score=int(round(base[pair_key(a, b)])),
        ))

    matched_ids = {user_id for pair in pairs for user_id in pair}
    for user in pool:
        user.missed_rounds = 0 if user.id in matched_ids else user.missed_rounds + 1

    round_.status = RoundStatus.done
    round_.executed_at = datetime.utcnow()
    return MatchingResult(
        matched=len(pairs),
        unmatched=len(pool) - len(matched_ids),
        guaranteed=len(guaranteed),
    )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_matching.py -v`
Expected: PASS (전부)

- [ ] **Step 5: 전체 백엔드 테스트**

Run: `cd backend; uv run pytest -q`
Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/matching.py backend/tests/test_matching.py
git commit -m "$(cat <<'EOF'
feat(backend): run_matching — 8단계 파이프라인 오케스트레이션

조건부 UPDATE로 라운드를 선점해 중복 실행을 막는다(RoundNotPending).
실패 시 전부 롤백하고 라운드를 pending으로 되돌린다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: 매칭 실행 API

**Files:**
- Create: `backend/app/schemas/matching.py`
- Create: `backend/app/api/matching.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_admin_matching.py`

**Interfaces:**
- Consumes: Task 7의 `run_matching`, `MatchingResult`, `RoundNotFound`, `RoundNotPending`
- Produces: `POST /admin/match-rounds/{round_id}/run` → `{"matched": int, "unmatched": int, "guaranteed": int}`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_admin_matching.py` 새 파일:

```python
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from app.models.survey import Survey
from app.models.user import Gender, User, UserStatus
from tests.conftest import TestingSessionLocal

NIGHT = {"sleep_self": "night", "sleep_pref": "night"}


def _seed_pool_and_round() -> int:
    db = TestingSessionLocal()
    for email, gender in (("m@test.com", Gender.male), ("w@test.com", Gender.female)):
        user = User(
            email=email, password_hash="x", name="테스트", university="서울대학교",
            gender=gender, status=UserStatus.active,
        )
        db.add(user)
        db.commit()
        db.add(Survey(user_id=user.id, answers={"responses": NIGHT, "absolute": []}))
        db.commit()
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    return round_id


def test_admin_runs_matching(admin_client: TestClient):
    round_id = _seed_pool_and_round()

    res = admin_client.post(f"/admin/match-rounds/{round_id}/run")

    assert res.status_code == 200
    assert res.json() == {"matched": 1, "unmatched": 0, "guaranteed": 0}


def test_round_becomes_done(admin_client: TestClient):
    round_id = _seed_pool_and_round()
    admin_client.post(f"/admin/match-rounds/{round_id}/run")

    listed = admin_client.get("/admin/match-rounds").json()
    assert listed[0]["status"] == RoundStatus.done.value


def test_second_run_is_conflict(admin_client: TestClient):
    round_id = _seed_pool_and_round()
    admin_client.post(f"/admin/match-rounds/{round_id}/run")

    res = admin_client.post(f"/admin/match-rounds/{round_id}/run")
    assert res.status_code == 409


def test_missing_round_is_404(admin_client: TestClient):
    res = admin_client.post("/admin/match-rounds/9999/run")
    assert res.status_code == 404


def test_normal_user_is_forbidden(client: TestClient):
    round_id = _seed_pool_and_round()
    client.post("/auth/register", json={
        "email": "normal@test.com", "password": "password123", "name": "김일반",
        "university": "서울대학교", "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    token = client.post("/auth/login", json={
        "email": "normal@test.com", "password": "password123",
    }).json()["access_token"]

    res = client.post(
        f"/admin/match-rounds/{round_id}/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd backend; uv run pytest tests/test_admin_matching.py -v`
Expected: FAIL — 405 또는 404 (엔드포인트 없음)

- [ ] **Step 3: 스키마 작성**

`backend/app/schemas/matching.py` 새 파일:

```python
from pydantic import BaseModel, ConfigDict


class MatchingRunOut(BaseModel):
    """매칭 실행 결과 요약 (설계 §7)."""

    matched: int      # 만들어진 짝 수
    unmatched: int    # 풀에 있었지만 못 붙은 인원 수
    guaranteed: int   # 보장으로 먼저 확정된 짝 수

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: 엔드포인트 작성**

`backend/app/api/matching.py` 새 파일:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.matching import MatchingRunOut
from app.services.matching import (
    RoundNotFound,
    RoundNotPending,
    run_matching,
)

admin_router = APIRouter(prefix="/admin/match-rounds", tags=["matching"])


@admin_router.post("/{round_id}/run", response_model=MatchingRunOut)
def run_round(
    round_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """매칭 실행. 로직은 서비스 계층에 있고 여기서는 예외만 HTTP로 옮긴다."""
    try:
        return run_matching(db, round_id)
    except RoundNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 라운드입니다",
        ) from None
    except RoundNotPending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 실행 중이거나 완료된 라운드입니다",
        ) from None
```

- [ ] **Step 5: 라우터 등록**

`backend/app/api/router.py`:

```python
from fastapi import APIRouter
from app.api import auth, game, matching, me, reports, rounds, survey, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
router.include_router(reports.router)
router.include_router(game.router)
router.include_router(rounds.router)
router.include_router(survey.router)
router.include_router(reports.admin_router)
router.include_router(rounds.admin_router)
router.include_router(matching.admin_router)
```

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd backend; uv run pytest tests/test_admin_matching.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: 전체 백엔드 테스트 + 커밋**

Run: `cd backend; uv run pytest -q`
Expected: 전부 PASS

```bash
git add backend/app/schemas/matching.py backend/app/api/matching.py backend/app/api/router.py backend/tests/test_admin_matching.py
git commit -m "$(cat <<'EOF'
feat(backend): POST /admin/match-rounds/{id}/run 매칭 실행

엔드포인트는 얇은 껍데기 — 서비스 예외를 404/409로 옮기기만 한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: 관리자 매칭 실행 버튼

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Admin/RoundTab.tsx`
- Test: `frontend/src/pages/Admin/RoundTab.test.tsx`

**Interfaces:**
- Consumes: Task 8의 `POST /admin/match-rounds/{id}/run`
- Produces: `runMatchRound(id: number): Promise<MatchingRunOut>` / `AdminMatchRoundOut.status`에 `"running"` 추가

- [ ] **Step 1: 기존 테스트 파일 확인**

Run: `cd frontend; npm test -- --run src/pages/Admin/RoundTab.test.tsx`
Expected: 현재 테스트 전부 PASS. 이 파일의 모킹 방식(`vi.mock("../../lib/api")`)을 그대로 따른다.

- [ ] **Step 2: 실패하는 테스트 작성**

`frontend/src/pages/Admin/RoundTab.test.tsx` 끝에 추가한다. 파일 상단의 `vi.mock` 목록에 `runMatchRound: vi.fn()`을 더하고, import에 `runMatchRound`를 추가한다.

```tsx
describe("매칭 실행", () => {
  it("pending 라운드에 실행 버튼이 있고, 누르면 결과 요약이 보인다", async () => {
    vi.mocked(listMatchRounds).mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    vi.mocked(runMatchRound).mockResolvedValue({
      matched: 12, unmatched: 3, guaranteed: 2,
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<RoundTab />);
    const button = await screen.findByRole("button", { name: "매칭 실행" });
    fireEvent.click(button);

    expect(await screen.findByText(/12쌍/)).toBeInTheDocument();
    expect(screen.getByText(/미매칭 3명/)).toBeInTheDocument();
    expect(runMatchRound).toHaveBeenCalledWith(1);
  });

  it("확인 창에서 취소하면 실행하지 않는다", async () => {
    vi.mocked(listMatchRounds).mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<RoundTab />);
    fireEvent.click(await screen.findByRole("button", { name: "매칭 실행" }));

    expect(runMatchRound).not.toHaveBeenCalled();
  });

  it("done 라운드에는 실행 버튼이 없다", async () => {
    vi.mocked(listMatchRounds).mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "done" },
    ]);

    render(<RoundTab />);
    expect(await screen.findByText("완료")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "매칭 실행" })).toBeNull();
  });

  it("실행 실패 메시지를 보여준다", async () => {
    vi.mocked(listMatchRounds).mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    vi.mocked(runMatchRound).mockRejectedValue(
      new ApiError(409, "이미 실행 중이거나 완료된 라운드입니다"),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<RoundTab />);
    fireEvent.click(await screen.findByRole("button", { name: "매칭 실행" }));

    expect(
      await screen.findByText("이미 실행 중이거나 완료된 라운드입니다"),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd frontend; npm test -- --run src/pages/Admin/RoundTab.test.tsx`
Expected: FAIL — `runMatchRound is not exported` 또는 "매칭 실행" 버튼을 찾지 못함

- [ ] **Step 4: 타입 추가**

`frontend/src/lib/types.ts`의 `AdminMatchRoundOut`을 수정하고 아래 인터페이스를 더한다:

```ts
export interface AdminMatchRoundOut {
  id: number;
  scheduled_at: string;
  status: "pending" | "running" | "done";
}

export interface MatchingRunOut {
  matched: number;
  unmatched: number;
  guaranteed: number;
}
```

- [ ] **Step 5: API 함수 추가**

`frontend/src/lib/api.ts` — 상단 타입 import 목록에 `MatchingRunOut`을 더하고, `deleteMatchRound` 아래에 추가:

```ts
export function runMatchRound(id: number): Promise<MatchingRunOut> {
  return apiFetch<MatchingRunOut>(`/admin/match-rounds/${id}/run`, {
    method: "POST",
  });
}
```

- [ ] **Step 6: RoundTab 수정**

`frontend/src/pages/Admin/RoundTab.tsx`:

import에 `runMatchRound`, 타입에 `MatchingRunOut`을 추가하고 상태·핸들러·렌더를 더한다.

```tsx
const STATUS_LABEL: Record<AdminMatchRoundOut["status"], string> = {
  pending: "예정",
  running: "실행중",
  done: "완료",
};
```

컴포넌트 안 상태 선언부에 추가:

```tsx
  const [running, setRunning] = useState<number | null>(null);
  const [summary, setSummary] = useState<(MatchingRunOut & { id: number }) | null>(null);
```

핸들러 추가 (`handleDelete` 아래):

```tsx
  async function handleRun(id: number) {
    // 되돌릴 수 없는 작업이라 한 번 더 묻는다
    if (!window.confirm("이 라운드의 매칭을 실행할까요? 되돌릴 수 없어요.")) return;
    setError("");
    setRunning(id);
    try {
      const result = await runMatchRound(id);
      setSummary({ ...result, id });
      setItems((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: "done" } : r)),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(null);
    }
  }
```

배지를 `STATUS_LABEL`로 바꾸고, pending 라운드의 액션 영역에 버튼을 더한다:

```tsx
          <span className={styles.badge}>{STATUS_LABEL[round.status]}</span>
```

```tsx
              {round.status === "pending" && (
                <div className={styles.actions}>
                  <Button onClick={() => handleRun(round.id)} disabled={running === round.id}>
                    {running === round.id ? "실행 중…" : "매칭 실행"}
                  </Button>
                  <Button onClick={() => startEdit(round)}>수정</Button>
                  <Button onClick={() => handleDelete(round.id)}>삭제</Button>
                </div>
              )}
              {summary?.id === round.id && (
                <p className={styles.summary}>
                  {summary.matched}쌍 매칭 (보장 {summary.guaranteed}쌍) · 미매칭 {summary.unmatched}명
                </p>
              )}
```

`frontend/src/pages/Admin/Admin.module.css`에 `.summary` 클래스가 없으면 추가한다:

```css
.summary {
  margin-top: 8px;
  font-size: 14px;
  color: #444;
}
```

- [ ] **Step 7: 테스트 실행 — 통과 확인**

Run: `cd frontend; npm test -- --run src/pages/Admin/RoundTab.test.tsx`
Expected: PASS

- [ ] **Step 8: 전체 프론트 테스트 + 린트**

Run: `cd frontend; npm test -- --run`
Expected: 전부 PASS

Run: `cd frontend; npm run lint`
Expected: 에러 0

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Admin/RoundTab.tsx frontend/src/pages/Admin/RoundTab.test.tsx frontend/src/pages/Admin/Admin.module.css
git commit -m "$(cat <<'EOF'
feat(frontend): 관리자 라운드 탭 매칭 실행 버튼

실행 전 확인창 — 되돌릴 수 없는 작업이다.
결과는 매칭 쌍 수·보장 쌍 수·미매칭 인원으로 요약해 보여준다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## 수동 검증

자동 테스트가 잡지 못하는 부분이다. Task 9 이후 한 번 확인한다.

- [ ] 백엔드 실행: `cd backend; uv run uvicorn app.main:app --reload`
- [ ] 프론트 실행: `cd frontend; npm run dev`
- [ ] active 유저 남녀 각 2명 이상을 만들고 설문을 저장한다 (`/survey`)
- [ ] 관리자 계정으로 `/admin` → 라운드 탭에서 미래 시각 라운드를 하나 만든다
- [ ] "매칭 실행" 클릭 → 확인창 → 결과 요약(N쌍 / 보장 M쌍 / 미매칭 K명)이 뜨는지
- [ ] 배지가 "완료"로 바뀌고 수정·삭제 버튼이 사라지는지
- [ ] 같은 라운드에서 "매칭 실행"을 다시 시도할 수 없는지 (버튼 자체가 사라짐)
- [ ] DB에서 `matches` 행의 `score`가 0~100 범위에 있는지, `users.missed_rounds`가 매칭된 사람은 0인지
- [ ] 새 라운드를 하나 더 만들어 실행 → **같은 짝이 다시 나오지 않는지** ← **가장 중요.** 재매칭 금지가 깨지면 유저 신뢰가 무너진다

---

## Self-Review 결과

**스펙 커버리지** — 이 계획은 스펙 §10의 2단계를 다룬다.

| 스펙 | 담당 태스크 |
|---|---|
| §2 파이프라인 8단계 | Task 7 `_execute` |
| §2.1 모듈 경계 | Task 2·4·5·8 (파일 분리 그대로) |
| §3.1~§3.4 만족도·가중치 | Task 2 |
| §3.5 점수 합산 (0 나눗셈 포함) | Task 3 |
| §3.6 절대질문 하드필터 | Task 3 |
| §4.1 이월 보너스 | Task 5·7 |
| §4.2 대학 가중치 | **3단계로 미룸** — `UNIVERSITY_BONUS = 0` 상수만 (스펙 §10이 그렇게 지시) |
| §4.3 게임 보정·보장 충돌 | Task 6·7 |
| §4.4 게임 대상 식별 | Task 6 (`_identity_resolver`) |
| §5.1~§5.5 짝짓기·결정론·성비·재매칭·멱등 | Task 4·7 |
| §6.1 데이터 모델 | Task 1 |
| §6.2 매칭 자격 | Task 5 |
| §7 `POST .../run` | Task 8 |
| §7.1 `GET /me/match` | **4단계로 미룸** |
| §8 관리자 실행 버튼 | Task 9 |
| §8 홈 매칭 결과 카드 | **4단계로 미룸** |
| §11 테스트 전략 | 각 태스크 (그리디 반례·결정론성·카탈로그 정합성 포함) |

**타입 일관성** — `pair_key`가 만드는 `(작은 id, 큰 id)` 튜플이 `past_pairs`·`game_signals`·`resolve_guarantees`·`optimal_pairs` 반환값·`Match` 저장까지 한 형태로 흐른다. `satisfaction`은 값 두 개가 아니라 **responses 딕셔너리 두 개**를 받는다 — 거주지 규칙이 "내 거주지"까지 필요하기 때문이며, Task 2의 시그니처를 Task 3이 그대로 쓴다.

**알려진 위험 3가지**

1. **`_MATCH_BONUS` 가 최적해를 아주 조금 바꾼다.** 간선마다 +1(=0.001점)을 얹어 0점 페어도 매칭되게 했다. 그 부작용으로 "총점이 0.001점 낮아도 한 쌍 더 붙는 조합"이 이긴다. 최소 점수 컷이 없다는 설계 의도와 같은 방향이라 의도적으로 둔다.
2. **`Match.score`는 보정 전 궁합 점수다.** 이월·게임 보너스가 빠진 값이라 "왜 이 짝이 됐나"를 점수만으로 역산할 수 없다. 카테고리 가중치 튜닝 근거로 쓰려면 보정 전 값이 맞다(§6.1의 목적).
3. **실행 중 서버가 죽으면 라운드가 `running`에 멈춘다.** 관리자가 인지하도록 한 설계(§5.5)지만, 되돌리는 UI가 없다 — 현재는 DB를 직접 고쳐야 한다. 운영 투입 전 "running → pending 되돌리기" 버튼이 필요할 수 있다. 지금 범위에는 넣지 않는다.
