# 설문 카탈로그 백엔드 이전 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 45문항 설문 카탈로그를 프론트엔드에서 백엔드로 옮기고, 프론트는 `GET /survey/questions`로 받아 렌더하게 한다.

**Architecture:** 백엔드에 `app/survey/catalog.py`(순수 데이터, DB·HTTP 모름)를 두고 Pydantic 스키마로 직렬화해 노출한다. 프론트의 `questions.ts`·`faceTypes.ts`는 삭제하고 API 응답을 그대로 사용한다. 문항 정의가 두 벌 존재하는 상태를 만들지 않는 것이 이 단계의 유일한 목적이다.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Pydantic v2 · pytest / React 19 · Vite · vitest · Testing Library

**Spec:** `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§2.1 모듈 경계, §3 점수 계산, §7 API, §10 작업 분할 1단계)

## Global Constraints

- 백엔드 테스트: `cd backend; uv run pytest -q` — 현재 139개 전부 통과 상태를 유지한다.
- 프론트 테스트: `cd frontend; npx vitest run` — 현재 156개 전부 통과 상태를 유지한다.
- 프론트 린트: `cd frontend; npm run lint` — 경고 0 유지.
- 엔드포인트는 Pydantic 스키마로 응답한다. dict 반환 금지 (`backend/CLAUDE.md`).
- 입력 스키마와 응답 스키마를 분리한다 (`backend/CLAUDE.md`).
- 프론트 API 주소는 `VITE_API_URL` 환경변수만 사용. 하드코딩 금지 (`frontend/CLAUDE.md`).
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + 본문 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 커밋은 각 Task 끝에서 한 번. push는 하지 않는다 (허락 필요).
- 이 단계에서 매칭 점수 계산 로직은 작성하지 않는다. 카탈로그 이전만 한다.

---

## File Structure

**생성 (백엔드)**

| 파일 | 책임 |
|---|---|
| `backend/app/survey/__init__.py` | 패키지 선언 (빈 파일) |
| `backend/app/survey/catalog.py` | 45문항 정의 + 얼굴상 목록. 순수 데이터. DB·HTTP 모름 |
| `backend/app/api/survey.py` | `GET /survey/questions` 라우터 |
| `backend/tests/test_survey_catalog.py` | 카탈로그 정합성 + 엔드포인트 테스트 |

**수정 (백엔드)**

| 파일 | 변경 |
|---|---|
| `backend/app/schemas/survey.py` | 카탈로그 응답 스키마 추가 |
| `backend/app/api/router.py` | `survey.router` 등록 |

**수정 (프론트)**

| 파일 | 변경 |
|---|---|
| `frontend/src/lib/types.ts` | 카탈로그 타입 추가 |
| `frontend/src/lib/api.ts` | `getSurveyCatalog()` 추가 |
| `frontend/src/pages/Survey/types.ts` | 문항 타입은 `lib/types`에서 재수출, UI 로컬 타입만 유지 |
| `frontend/src/pages/Survey/QuestionField.tsx` | 얼굴상 목록을 props로 받음 |
| `frontend/src/pages/Survey/QuestionField.test.tsx` | props 변경 반영 |
| `frontend/src/pages/Survey/Survey.tsx` | 마운트 시 카탈로그 fetch |
| `frontend/src/pages/Survey/Survey.test.tsx` | `getSurveyCatalog` mock 추가 |

**삭제 (프론트)**

`questions.ts` · `questions.test.ts` · `faceTypes.ts` · `faceTypes.test.ts`
→ 카탈로그 정본이 백엔드로 가므로 남기면 두 벌이 된다. 이 파일들의 테스트는 백엔드 `test_survey_catalog.py`가 대체한다.

---

## 카테고리 배정표

`catalog.py`의 각 문항에 붙일 `category` 값이다. 매칭 점수 계산(2단계)에서 카테고리별 가중치를 적용하기 위한 것이며, 이 단계에서는 데이터만 넣고 쓰지 않는다.

| 카테고리 상수 | 소속 문항 id | 개수 |
|---|---|---|
| `APPEARANCE` | `height_self` `height_pref` `face_self` `face_pref` `style_self` `style_pref` `tattoo_self` `tattoo_pref` `piercing_self` `piercing_pref` `grooming_self` | 11 |
| `VALUES` | `politics_self` `politics_pref` `religion_self` `religion_pref` | 4 |
| `RELATIONSHIP` | `contact_freq_self` `contact_freq_pref` `date_freq_self` `date_freq_pref` `alone_time_self` `alone_time_pref` `affection_self` `affection_pref` `conflict_style_self` `conflict_style_pref` `priority_rank_self` `priority_rank_pref` | 12 |
| `LIFESTYLE` | `date_budget_self` `date_budget_pref` `cost_share_self` `cost_share_pref` `smoking_self` `smoking_pref` `drinking_self` `drinking_pref` `exercise_self` `exercise_pref` `sleep_self` `sleep_pref` `hobby_self` `hobby_pref` `residence_self` `residence_pref` `living_self` `living_pref` | 18 |

합계 45.

---

### Task 1: 백엔드 카탈로그 데이터

`frontend/src/pages/Survey/questions.ts`와 `faceTypes.ts`의 내용을 파이썬으로 옮긴다. **문항 id·라벨·선택지 id·선택지 라벨·순서를 한 글자도 바꾸지 않는다.** 기존에 저장된 설문 응답(`Survey.answers`의 키가 문항 id)과 어긋나면 데이터가 깨진다.

**Files:**
- Create: `backend/app/survey/__init__.py`
- Create: `backend/app/survey/catalog.py`
- Test: `backend/tests/test_survey_catalog.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `Category` (StrEnum): `APPEARANCE` / `VALUES` / `RELATIONSHIP` / `LIFESTYLE`
  - `Choice` (dataclass): `id: str`, `label: str`
  - `FaceType` (dataclass): `id: str`, `label: str`, `image: str`
  - `Question` (dataclass): `id: str`, `section: str`, `label: str`, `type: str`, `category: Category`, `choices: list[Choice] | None`, `face: bool`, `rank_items: list[Choice] | None`, `scale_labels: tuple[str, str] | None`, `unit: str | None`, `male_only: bool`, `no_pref_id: str | None`
  - `QUESTIONS: list[Question]` (45개)
  - `FACE_TYPES: list[FaceType]` (4개)
  - `FACE_ANY_ID: str` = `"any"`
  - `SIDO: list[Choice]` (17개 시·도)

- [ ] **Step 1: 정합성 테스트를 먼저 작성한다**

`backend/tests/test_survey_catalog.py` 생성:

```python
from app.survey.catalog import (
    FACE_ANY_ID,
    FACE_TYPES,
    QUESTIONS,
    Category,
)

QUESTION_BY_ID = {q.id: q for q in QUESTIONS}


def test_총_45문항():
    assert len(QUESTIONS) == 45


def test_id_중복_없음():
    ids = [q.id for q in QUESTIONS]
    assert len(set(ids)) == len(ids)


def test_single_multi_문항은_choices_보유():
    for q in QUESTIONS:
        if q.type in ("single", "multi"):
            assert q.choices, f"{q.id}에 choices가 없다"


def test_ranking_문항은_rank_items_보유():
    for q in QUESTIONS:
        if q.type == "ranking":
            assert q.rank_items, f"{q.id}에 rank_items가 없다"


def test_scale_문항은_scale_labels_보유():
    for q in QUESTIONS:
        if q.type == "scale":
            assert q.scale_labels and len(q.scale_labels) == 2


def test_no_pref_id는_partner_문항에만():
    for q in QUESTIONS:
        if q.no_pref_id:
            assert q.section == "partner", f"{q.id}는 self인데 no_pref_id가 있다"


def test_no_pref_id가_choices에_실재한다_비face():
    for q in QUESTIONS:
        if q.no_pref_id and not q.face:
            assert any(c.id == q.no_pref_id for c in q.choices or [])


def test_face_문항의_no_pref_id는_FACE_ANY_ID():
    for q in QUESTIONS:
        if q.face and q.no_pref_id:
            assert q.no_pref_id == FACE_ANY_ID


def test_grooming_self만_male_only():
    assert [q.id for q in QUESTIONS if q.male_only] == ["grooming_self"]


def test_모든_문항이_카테고리를_갖는다():
    for q in QUESTIONS:
        assert isinstance(q.category, Category)


def test_카테고리별_문항수():
    counts = {c: 0 for c in Category}
    for q in QUESTIONS:
        counts[q.category] += 1
    assert counts == {
        Category.APPEARANCE: 11,
        Category.VALUES: 4,
        Category.RELATIONSHIP: 12,
        Category.LIFESTYLE: 18,
    }


def test_모든_pref_문항은_짝이_되는_self_문항을_갖는다():
    """매칭 점수는 `X_pref` ↔ `X_self` 명명 규칙으로 짝을 찾는다.
    이 규칙이 깨지면 2단계 점수 계산이 조용히 그 문항을 건너뛴다."""
    for q in QUESTIONS:
        if q.id.endswith("_pref"):
            mate = q.id[: -len("_pref")] + "_self"
            assert mate in QUESTION_BY_ID, f"{q.id}의 짝 {mate}가 없다"


def test_짝없는_self는_grooming_self뿐():
    orphans = [
        q.id
        for q in QUESTIONS
        if q.id.endswith("_self")
        and (q.id[: -len("_self")] + "_pref") not in QUESTION_BY_ID
    ]
    assert orphans == ["grooming_self"]


def test_pref와_self는_같은_카테고리():
    for q in QUESTIONS:
        if q.id.endswith("_pref"):
            mate = QUESTION_BY_ID[q.id[: -len("_pref")] + "_self"]
            assert q.category == mate.category, f"{q.id}와 {mate.id}의 카테고리가 다르다"


def test_얼굴상_목록():
    assert len(FACE_TYPES) >= 2
    for f in FACE_TYPES:
        assert f.id and f.label and f.image


def test_FACE_ANY_ID는_얼굴상_목록과_겹치지_않는다():
    assert not any(f.id == FACE_ANY_ID for f in FACE_TYPES)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_survey_catalog.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.survey'`

- [ ] **Step 3: 패키지와 카탈로그 골격 작성**

`backend/app/survey/__init__.py` — 빈 파일로 생성.

`backend/app/survey/catalog.py`:

```python
"""설문 문항 카탈로그 — 단일 진실원.

프론트엔드는 `GET /survey/questions`로 이 데이터를 받아 렌더한다.
문항 id는 `Survey.answers` JSON의 키로 그대로 저장되므로 **절대 바꾸지 않는다.**

명명 규칙: `X_pref`(원하는 상대) ↔ `X_self`(나) 로 짝을 이룬다.
매칭 점수 계산이 이 규칙으로 짝을 찾으므로 새 문항을 넣을 때 반드시 지킨다.
예외는 `grooming_self` 하나뿐이다 (짝 없음 → 매칭에 쓰지 않음).
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Category(StrEnum):
    """카테고리별 가중치를 매기는 단위. 값은 매칭 알고리즘 설계 §3.4 참조."""

    APPEARANCE = "appearance"
    VALUES = "values"
    RELATIONSHIP = "relationship"
    LIFESTYLE = "lifestyle"


@dataclass(frozen=True)
class Choice:
    id: str
    label: str


@dataclass(frozen=True)
class FaceType:
    id: str
    label: str
    image: str


@dataclass(frozen=True)
class Question:
    id: str
    section: str  # "self" | "partner"
    label: str
    type: str  # single | multi | scale | number | ranking | image-single | image-multi
    category: Category
    choices: list[Choice] | None = None
    face: bool = False
    rank_items: list[Choice] | None = None
    scale_labels: tuple[str, str] | None = None
    unit: str | None = None
    male_only: bool = False
    no_pref_id: str | None = None


# TODO(운영 전 교체): 얼굴상 목록·이미지 미확정(에셋 의존).
FACE_ANY_ID = "any"

FACE_TYPES: list[FaceType] = [
    FaceType(id="type_a", label="강아지상", image="/faces/placeholder-a.png"),
    FaceType(id="type_b", label="고양이상", image="/faces/placeholder-b.png"),
    FaceType(id="type_c", label="곰상", image="/faces/placeholder-c.png"),
    FaceType(id="type_d", label="여우상", image="/faces/placeholder-d.png"),
]

# 시/도 17개 (행정표준). 운영 전 팀 대학목록과 별개.
SIDO: list[Choice] = [
    Choice(id=s, label=s)
    for s in (
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    )
]

QUESTIONS: list[Question] = []
```

- [ ] **Step 4: 45문항을 옮긴다**

`frontend/src/pages/Survey/questions.ts`를 열어 **위에서 아래 순서 그대로** `QUESTIONS` 리스트를 채운다. `category`는 이 문서 상단의 "카테고리 배정표"를 따른다.

TypeScript → Python 필드명 변환:

| TS | Python |
|---|---|
| `rankItems` | `rank_items` |
| `scaleLabels` | `scale_labels` (튜플) |
| `maleOnly` | `male_only` |
| `noPrefId` | `no_pref_id` |
| `choices: SIDO` | `choices=SIDO` |
| `face: true` | `face=True` |
| `noPrefId: FACE_ANY_ID` | `no_pref_id=FACE_ANY_ID` |

처음 6개 문항 예시 (나머지 39개도 같은 형태로 이어 쓴다):

```python
QUESTIONS: list[Question] = [
    # ── 외모·스타일 ──
    Question(
        id="height_self", section="self", label="내 키", type="number",
        category=Category.APPEARANCE, unit="cm",
    ),
    Question(
        id="height_pref", section="partner", label="원하는 상대 키", type="single",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="u165", label="~165"),
            Choice(id="165_175", label="165~175"),
            Choice(id="175_185", label="175~185"),
            Choice(id="o185", label="185↑"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    Question(
        id="face_self", section="self", label="내 얼굴상", type="image-single",
        category=Category.APPEARANCE, face=True,
    ),
    Question(
        id="face_pref", section="partner", label="원하는 상대 얼굴상",
        type="image-multi", category=Category.APPEARANCE,
        face=True, no_pref_id=FACE_ANY_ID,
    ),
    Question(
        id="style_self", section="self", label="내 스타일", type="multi",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="casual", label="캐주얼"),
            Choice(id="formal", label="포멀"),
            Choice(id="street", label="스트릿"),
            Choice(id="minimal", label="미니멀"),
            Choice(id="vintage", label="빈티지"),
        ],
    ),
    Question(
        id="style_pref", section="partner", label="원하는 상대 스타일", type="multi",
        category=Category.APPEARANCE,
        choices=[
            Choice(id="casual", label="캐주얼"),
            Choice(id="formal", label="포멀"),
            Choice(id="street", label="스트릿"),
            Choice(id="minimal", label="미니멀"),
            Choice(id="vintage", label="빈티지"),
            Choice(id="any", label="상관없음"),
        ],
        no_pref_id="any",
    ),
    # ... questions.ts 순서대로 나머지 39문항 계속
]
```

척도형 예시 (`scale_labels`는 튜플):

```python
    Question(
        id="contact_freq_self", section="self", label="내 연락 빈도 성향",
        type="scale", category=Category.RELATIONSHIP,
        scale_labels=("가끔", "자주"),
    ),
```

순위형 예시:

```python
    Question(
        id="priority_rank_self", section="self", label="내 인생 우선순위",
        type="ranking", category=Category.RELATIONSHIP,
        rank_items=[
            Choice(id="lover", label="연인"),
            Choice(id="friend", label="친구"),
            Choice(id="self_dev", label="자기개발"),
            Choice(id="family", label="가족"),
        ],
    ),
```

`male_only` 예시:

```python
    Question(
        id="grooming_self", section="self", label="외모관리 습관", type="multi",
        category=Category.APPEARANCE, male_only=True,
        choices=[
            Choice(id="lotion", label="로션"),
            Choice(id="sunscreen", label="썬크림"),
            Choice(id="hair", label="머리손질"),
            Choice(id="makeup", label="화장"),
            Choice(id="nails", label="손톱관리"),
        ],
    ),
```

거주지 예시 (`SIDO` 재사용):

```python
    Question(
        id="residence_self", section="self", label="내 거주지", type="single",
        category=Category.LIFESTYLE, choices=SIDO,
    ),
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_survey_catalog.py -q`
Expected: PASS (16개)

실패하면 대개 개수 불일치다. `test_카테고리별_문항수`가 실패하면 배정표를 다시 대조하고, `test_총_45문항`이 실패하면 빠뜨린 문항을 찾는다.

- [ ] **Step 6: 전체 테스트로 회귀 없음 확인**

Run: `cd backend; uv run pytest -q`
Expected: PASS — 139 + 16 = 155개

- [ ] **Step 7: 커밋**

```bash
git add backend/app/survey backend/tests/test_survey_catalog.py
git commit -m "$(cat <<'EOF'
feat(backend): 설문 문항 카탈로그 45문항 + 카테고리 배정

프론트 questions.ts를 백엔드로 이전. 문항 id·라벨·선택지 전부 동일하게 유지
(Survey.answers JSON 키와 어긋나면 기존 응답이 깨진다).

매칭 점수 계산용 category 필드 추가. pref↔self 명명 규칙을 테스트로 고정.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `GET /survey/questions` 엔드포인트

**Files:**
- Modify: `backend/app/schemas/survey.py`
- Create: `backend/app/api/survey.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_survey_catalog.py` (Task 1 파일에 이어붙임)

**Interfaces:**
- Consumes: `app.survey.catalog`의 `QUESTIONS`, `FACE_TYPES`, `FACE_ANY_ID`
- Produces:
  - `GET /survey/questions` → `SurveyCatalogOut`
  - `SurveyCatalogOut`: `questions: list[QuestionOut]`, `face_types: list[FaceTypeOut]`, `face_any_id: str`
  - `QuestionOut` 필드: `id` `section` `label` `type` `choices` `face` `rank_items` `scale_labels` `unit` `male_only` `no_pref_id`
    (`category`는 내부 전용이라 응답에 넣지 않는다 — 프론트가 쓰지 않는다)

- [ ] **Step 1: 엔드포인트 테스트 작성**

`backend/tests/test_survey_catalog.py`의 **맨 위 import 블록**에 추가:

```python
from fastapi.testclient import TestClient
```

파일 맨 아래에 헬퍼와 테스트를 추가한다 (다른 테스트 파일의 헬퍼를 import하지 않는다 — 테스트 간 결합을 만들지 않기 위해 이 파일 안에 둔다):

```python
def _headers(client: TestClient, email: str = "catalog@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김카탈",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_카탈로그_조회는_로그인_필요(client: TestClient):
    res = client.get("/survey/questions")
    assert res.status_code == 401


def test_카탈로그_45문항_반환(client: TestClient):
    res = client.get("/survey/questions", headers=_headers(client))
    assert res.status_code == 200
    body = res.json()
    assert len(body["questions"]) == 45


def test_카탈로그_응답에_얼굴상_포함(client: TestClient):
    body = client.get("/survey/questions", headers=_headers(client)).json()
    assert len(body["face_types"]) == 4
    assert body["face_any_id"] == "any"
    assert body["face_types"][0]["image"].startswith("/faces/")


def test_카탈로그_문항_필드_형태(client: TestClient):
    body = client.get("/survey/questions", headers=_headers(client)).json()
    by_id = {q["id"]: q for q in body["questions"]}

    height = by_id["height_self"]
    assert height["type"] == "number"
    assert height["unit"] == "cm"
    assert height["section"] == "self"

    pref = by_id["height_pref"]
    assert pref["no_pref_id"] == "any"
    assert [c["id"] for c in pref["choices"]][0] == "u165"

    scale = by_id["contact_freq_self"]
    assert scale["scale_labels"] == ["가끔", "자주"]

    ranking = by_id["priority_rank_self"]
    assert [i["id"] for i in ranking["rank_items"]] == [
        "lover", "friend", "self_dev", "family",
    ]

    assert by_id["grooming_self"]["male_only"] is True
    assert by_id["face_pref"]["face"] is True


def test_카탈로그_응답에_category는_노출하지_않는다(client: TestClient):
    """카테고리 가중치는 내부 매칭 로직 전용이다. 프론트에 흘리지 않는다."""
    body = client.get("/survey/questions", headers=_headers(client)).json()
    assert "category" not in body["questions"][0]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend; uv run pytest tests/test_survey_catalog.py -q -k 카탈로그`
Expected: FAIL — 404 (라우터 없음)

- [ ] **Step 3: 응답 스키마 추가**

`backend/app/schemas/survey.py` 맨 아래에 추가:

```python
class ChoiceOut(BaseModel):
    id: str
    label: str

    model_config = ConfigDict(from_attributes=True)


class FaceTypeOut(BaseModel):
    id: str
    label: str
    image: str

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    """카탈로그 응답 전용. `category`는 매칭 내부 전용이라 의도적으로 뺐다."""

    id: str
    section: str
    label: str
    type: str
    choices: list[ChoiceOut] | None = None
    face: bool = False
    rank_items: list[ChoiceOut] | None = None
    scale_labels: tuple[str, str] | None = None
    unit: str | None = None
    male_only: bool = False
    no_pref_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SurveyCatalogOut(BaseModel):
    questions: list[QuestionOut]
    face_types: list[FaceTypeOut]
    face_any_id: str
```

> 파일 상단 import에 `ConfigDict`가 없으면 `from pydantic import BaseModel, ConfigDict`로 고친다.

- [ ] **Step 4: 라우터 작성**

`backend/app/api/survey.py` 생성:

```python
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.survey import SurveyCatalogOut
from app.survey.catalog import FACE_ANY_ID, FACE_TYPES, QUESTIONS

router = APIRouter(prefix="/survey", tags=["survey"])


@router.get("/questions", response_model=SurveyCatalogOut)
def get_catalog(_: User = Depends(get_current_user)):
    """설문 문항 카탈로그. 프론트는 이걸 받아 설문 화면을 렌더한다.

    로그인을 요구하는 이유: 문항 전체가 공개되면 서비스 설문 설계가 그대로 노출된다.
    설문 화면 자체도 active 유저만 들어오므로 접근 범위가 어긋나지 않는다.
    """
    return SurveyCatalogOut(
        questions=QUESTIONS,
        face_types=FACE_TYPES,
        face_any_id=FACE_ANY_ID,
    )
```

- [ ] **Step 5: 라우터 등록**

`backend/app/api/router.py` 수정:

```python
from fastapi import APIRouter
from app.api import auth, game, me, reports, rounds, survey, verification

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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend; uv run pytest tests/test_survey_catalog.py -q`
Expected: PASS

`scale_labels`가 튜플이라 JSON에서는 배열로 나온다 — 테스트가 `["가끔", "자주"]`로 비교하는 것이 맞다.

- [ ] **Step 7: 전체 테스트**

Run: `cd backend; uv run pytest -q`
Expected: PASS (160개 = 기존 139 + Task 1의 16 + 이번 5)

- [ ] **Step 8: 커밋**

```bash
git add backend/app/api/survey.py backend/app/api/router.py backend/app/schemas/survey.py backend/tests/test_survey_catalog.py
git commit -m "$(cat <<'EOF'
feat(backend): GET /survey/questions — 설문 카탈로그 조회

프론트가 문항 정의를 받아가는 엔드포인트. 로그인 필요.
category는 매칭 내부 전용이라 응답에서 제외한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 프론트 타입 + API 함수

화면은 아직 건드리지 않는다. 타입과 fetch 함수만 준비한다.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Survey/types.ts`

**Interfaces:**
- Consumes: Task 2의 `GET /survey/questions` 응답 형태
- Produces:
  - `lib/types.ts`: `Section`, `QuestionType`, `Choice`, `FaceChoice`, `Question`, `SurveyCatalog`
  - `lib/api.ts`: `getSurveyCatalog(): Promise<SurveyCatalog>`
  - `pages/Survey/types.ts`: `AnswerValue`, `SurveyResponses` 유지 + 위 타입 재수출

- [ ] **Step 1: `lib/types.ts`에 카탈로그 타입 추가**

파일 맨 아래에 추가한다. 필드명은 백엔드 응답과 동일한 snake_case다 — 변환 계층을 두지 않는다(이 프로젝트의 다른 타입들도 `kakao_id`, `scheduled_at`처럼 snake_case를 그대로 쓴다).

```typescript
export type Section = "self" | "partner";

export type QuestionType =
  | "single"
  | "multi"
  | "scale"
  | "number"
  | "ranking"
  | "image-single"
  | "image-multi";

export interface Choice {
  id: string;
  label: string;
}

export interface FaceChoice {
  id: string;
  label: string;
  image: string;
}

export interface Question {
  id: string;
  section: Section;
  label: string;
  type: QuestionType;
  choices?: Choice[] | null;
  face?: boolean;
  rank_items?: Choice[] | null;
  scale_labels?: [string, string] | null;
  unit?: string | null;
  male_only?: boolean;
  no_pref_id?: string | null;
}

export interface SurveyCatalog {
  questions: Question[];
  face_types: FaceChoice[];
  face_any_id: string;
}
```

- [ ] **Step 2: `lib/api.ts`에 fetch 함수 추가**

import 목록에 `SurveyCatalog`를 넣고, `getSurvey` 근처에 함수를 추가한다:

```typescript
export function getSurveyCatalog(): Promise<SurveyCatalog> {
  return apiFetch<SurveyCatalog>("/survey/questions", { method: "GET" });
}
```

- [ ] **Step 3: `pages/Survey/types.ts` 정리**

파일 전체를 아래로 교체한다. 문항 타입의 정본은 `lib/types.ts`이고, 이 파일은 설문 화면 로컬 타입만 갖는다.

```typescript
export type {
  Section,
  QuestionType,
  Choice,
  FaceChoice,
  Question,
  SurveyCatalog,
} from "../../lib/types";

export type AnswerValue = number | string | string[];
export type SurveyResponses = Record<string, AnswerValue>;
```

- [ ] **Step 4: 타입 검사**

Run: `cd frontend; npx tsc --noEmit`
Expected: `questions.ts`·`faceTypes.ts`·`QuestionField.tsx`가 아직 옛 필드명(`rankItems`, `noPrefId`, `maleOnly`, `scaleLabels`)을 쓰고 있어 **에러가 난다.** 정상이다 — Task 4·5에서 고친다.

에러가 그 파일들 밖에서 나면 멈추고 원인을 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Survey/types.ts
git commit -m "$(cat <<'EOF'
feat(frontend): 설문 카탈로그 타입 + getSurveyCatalog

문항 타입 정본을 lib/types.ts로 이동. 백엔드 응답과 필드명(snake_case) 일치.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `QuestionField`가 얼굴상 목록을 props로 받게

지금은 `faceTypes.ts`를 직접 import한다. 카탈로그가 API에서 오므로 부모가 내려주도록 바꾼다.

**Files:**
- Modify: `frontend/src/pages/Survey/QuestionField.tsx`
- Test: `frontend/src/pages/Survey/QuestionField.test.tsx`

**Interfaces:**
- Consumes: `lib/types`의 `Question`, `FaceChoice`; Task 3의 필드명(`rank_items`, `scale_labels`, `no_pref_id`)
- Produces: `QuestionField` props — `{ question, value, onChange, faceTypes: FaceChoice[], faceAnyId: string }`

- [ ] **Step 1: 테스트를 새 props에 맞게 고친다**

`QuestionField.test.tsx` 상단을 수정한다. `./faceTypes` import를 지우고 테스트용 상수를 파일 안에 둔다:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuestionField } from "./QuestionField";
import type { FaceChoice, Question } from "./types";

const FACE_TYPES: FaceChoice[] = [
  { id: "type_a", label: "강아지상", image: "/faces/placeholder-a.png" },
  { id: "type_b", label: "고양이상", image: "/faces/placeholder-b.png" },
  { id: "type_c", label: "곰상", image: "/faces/placeholder-c.png" },
  { id: "type_d", label: "여우상", image: "/faces/placeholder-d.png" },
];
const FACE_ANY_ID = "any";
```

`ranking` 테스트 픽스처의 `rankItems`를 `rank_items`로, `scale` 픽스처가 있으면 `scaleLabels`를 `scale_labels`로 바꾼다.

파일 안의 모든 `<QuestionField ... />` 렌더 호출에 props 두 개를 더한다:

```typescript
<QuestionField
  question={imageMulti}
  value={undefined}
  onChange={onChange}
  faceTypes={FACE_TYPES}
  faceAnyId={FACE_ANY_ID}
/>
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend; npx vitest run src/pages/Survey/QuestionField.test.tsx`
Expected: FAIL — 타입 에러 또는 얼굴상이 렌더되지 않음

- [ ] **Step 3: 컴포넌트 수정**

`QuestionField.tsx` 상단:

```typescript
import type { FaceChoice, Question, AnswerValue } from "./types";
import styles from "./QuestionField.module.css";

interface Props {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
  faceTypes: FaceChoice[];
  faceAnyId: string;
}

export function QuestionField({
  question: q,
  value,
  onChange,
  faceTypes,
  faceAnyId,
}: Props) {
```

`./faceTypes` import 줄은 삭제한다.

필드명 변경 반영:
- `q.scaleLabels?.[0]` → `q.scale_labels?.[0]`
- `q.scaleLabels?.[1]` → `q.scale_labels?.[1]`
- `q.rankItems!` → `q.rank_items!` (3곳: `order` 기본값, `labelOf`)

파일 맨 아래 얼굴상 블록:

```typescript
  const faceOptions = isMulti
    ? [...faceTypes, { id: faceAnyId, label: "상관없음", image: "" }]
    : faceTypes;
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; npx vitest run src/pages/Survey/QuestionField.test.tsx`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Survey/QuestionField.tsx frontend/src/pages/Survey/QuestionField.test.tsx
git commit -m "$(cat <<'EOF'
refactor(frontend): QuestionField 얼굴상 목록을 props로 주입

카탈로그가 API에서 오므로 컴포넌트가 직접 import하지 않는다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `Survey.tsx`가 카탈로그를 fetch + 구 파일 삭제

**Files:**
- Modify: `frontend/src/pages/Survey/Survey.tsx`
- Test: `frontend/src/pages/Survey/Survey.test.tsx`
- Delete: `frontend/src/pages/Survey/questions.ts`
- Delete: `frontend/src/pages/Survey/questions.test.ts`
- Delete: `frontend/src/pages/Survey/faceTypes.ts`
- Delete: `frontend/src/pages/Survey/faceTypes.test.ts`

**Interfaces:**
- Consumes: `getSurveyCatalog` (Task 3), `QuestionField`의 새 props (Task 4)
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: 테스트에 카탈로그 mock 추가**

`Survey.test.tsx`의 `vi.mock("../../lib/api", ...)` 블록을 교체한다. 실제 문항 45개를 mock에 넣을 필요는 없다 — 화면 동작 검증에 필요한 최소 문항만 둔다.

```typescript
const CATALOG = {
  questions: [
    {
      id: "grooming_self", section: "self", label: "외모관리 습관", type: "multi",
      male_only: true,
      choices: [{ id: "lotion", label: "로션" }, { id: "hair", label: "머리손질" }],
    },
    {
      id: "smoking_self", section: "self", label: "내 흡연", type: "single",
      choices: [{ id: "none", label: "비흡연" }, { id: "yes", label: "흡연" }],
    },
    {
      id: "smoking_pref", section: "partner", label: "상대 흡연 선호", type: "single",
      choices: [
        { id: "none_only", label: "비흡연만" },
        { id: "any", label: "상관없음" },
      ],
      no_pref_id: "any",
    },
  ],
  face_types: [
    { id: "type_a", label: "강아지상", image: "/faces/placeholder-a.png" },
  ],
  face_any_id: "any",
};

vi.mock("../../lib/api", () => ({
  getSurveyCatalog: vi.fn().mockResolvedValue(CATALOG),
  getSurvey: vi.fn().mockResolvedValue({ answers: {}, updated_at: null }),
  saveSurvey: vi.fn().mockResolvedValue({
    answers: { responses: {}, absolute: [] }, updated_at: "x",
  }),
}));
```

파일 상단 import에 `getSurveyCatalog`를 추가한다.

기존 테스트 중 45문항 전체를 전제로 한 것(예: 특정 문항 라벨 검색)이 있으면 위 `CATALOG`에 그 문항을 추가하거나 테스트를 mock 내용에 맞게 고친다. `"외모관리 습관"`을 찾는 기존 테스트는 그대로 통과한다.

아래 테스트를 추가한다:

```typescript
it("마운트 시 카탈로그를 API에서 받아온다", async () => {
  render(<Survey />);
  await waitFor(() => expect(getSurveyCatalog).toHaveBeenCalled());
});

it("여성이면 grooming_self(외모관리 습관)를 숨긴다", async () => {
  authState.gender = "female";
  render(<Survey />);
  await waitFor(() => screen.getByText("내 흡연"));
  expect(screen.queryByText("외모관리 습관")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend; npx vitest run src/pages/Survey/Survey.test.tsx`
Expected: FAIL — `getSurveyCatalog is not a function` 또는 호출되지 않음

- [ ] **Step 3: `Survey.tsx` 수정**

import 교체 — `./questions` 줄을 삭제하고 `getSurveyCatalog`를 가져온다:

```typescript
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../lib/auth";
import { getSurvey, getSurveyCatalog, saveSurvey } from "../../lib/api";
import { QuestionField } from "./QuestionField";
import type {
  AnswerValue,
  FaceChoice,
  Question,
  SurveyResponses,
} from "./types";
import styles from "./Survey.module.css";
```

상태 추가 (기존 `status` 선언 아래):

```typescript
  const [questions, setQuestions] = useState<Question[]>([]);
  const [faceTypes, setFaceTypes] = useState<FaceChoice[]>([]);
  const [faceAnyId, setFaceAnyId] = useState("any");
  const [catalogFailed, setCatalogFailed] = useState(false);
```

`visible` 계산을 상태 기반으로 바꾼다 (`QUESTIONS` → `questions`, `maleOnly` → `male_only`):

```typescript
  const visible = useMemo(
    () => questions.filter((q) => !(q.male_only && user?.gender !== "male")),
    [questions, user?.gender],
  );
```

카탈로그 로드 effect를 기존 `getSurvey` effect **위에** 추가한다:

```typescript
  useEffect(() => {
    getSurveyCatalog()
      .then((c) => {
        setQuestions(c.questions);
        setFaceTypes(c.face_types);
        setFaceAnyId(c.face_any_id);
      })
      .catch(() => setCatalogFailed(true));
  }, []);
```

`canToggleAbsolute`와 `handleSave` 안의 `q.noPrefId` → `q.no_pref_id`로 전부 교체한다 (4곳).

`QuestionField` 렌더에 props 두 개를 넘긴다:

```typescript
              <QuestionField question={q} value={responses[q.id]}
                onChange={(v) => setValue(q.id, v)}
                faceTypes={faceTypes} faceAnyId={faceAnyId} />
```

로딩·실패 처리를 `return` 맨 앞에 넣는다:

```typescript
  if (catalogFailed) {
    return (
      <div className={styles.wrap}>
        <h1 className={styles.title}>가치관 설문</h1>
        <p className={styles.err}>설문을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className={styles.wrap}>
        <h1 className={styles.title}>가치관 설문</h1>
        <p className={styles.progress}>불러오는 중...</p>
      </div>
    );
  }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend; npx vitest run src/pages/Survey/Survey.test.tsx`
Expected: PASS

- [ ] **Step 5: 구 카탈로그 파일 삭제**

```bash
git rm frontend/src/pages/Survey/questions.ts frontend/src/pages/Survey/questions.test.ts frontend/src/pages/Survey/faceTypes.ts frontend/src/pages/Survey/faceTypes.test.ts
```

- [ ] **Step 6: 남은 참조 확인**

Run: `cd frontend; grep -rn "from \"./questions\"\|from \"./faceTypes\"\|QUESTIONS\|FACE_TYPES\|FACE_ANY_ID" src/`
Expected: 결과 없음 (테스트 파일 안에 로컬 선언한 `FACE_TYPES`는 예외 — `QuestionField.test.tsx` 안의 const 선언만 나와야 한다)

- [ ] **Step 7: 타입 검사 + 전체 테스트 + 린트**

```bash
cd frontend
npx tsc --noEmit
npx vitest run
npm run lint
```

Expected: 타입 에러 0 / 테스트 전부 통과 / 린트 경고 0

프론트 테스트 총계는 156에서 줄어든다 (`questions.test.ts` 7개 + `faceTypes.test.ts` 2개 삭제, Survey 테스트 2개 추가 → 149개 내외). 백엔드 `test_survey_catalog.py`가 그 검증을 넘겨받았으므로 정상이다.

- [ ] **Step 8: 백엔드 전체 테스트 재확인**

Run: `cd backend; uv run pytest -q`
Expected: PASS (160개)

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/pages/Survey/Survey.tsx frontend/src/pages/Survey/Survey.test.tsx
git commit -m "$(cat <<'EOF'
refactor(frontend): 설문 카탈로그를 API에서 로드

questions.ts·faceTypes.ts 삭제. 문항 정본은 백엔드 app/survey/catalog.py.
로딩·실패 상태 처리 추가.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## 수동 검증

자동 테스트가 잡지 못하는 부분이다. Task 5 이후 한 번 확인한다.

- [ ] 백엔드 실행: `cd backend; uv run uvicorn app.main:app --reload`
- [ ] 프론트 실행: `cd frontend; npm run dev`
- [ ] active 유저로 로그인 후 `/survey` 진입
- [ ] 45문항이 "나에 대해" / "원하는 상대" 두 섹션으로 나뉘어 모두 보이는지
- [ ] 얼굴상 문항에 이미지 칸 4개 + (원하는 상대 쪽엔) "상관없음"이 보이는지
- [ ] 남성 계정에서 "외모관리 습관"이 보이고, 여성 계정에서는 안 보이는지
- [ ] 절대질문 ★ 토글이 2개까지만 켜지는지, "상관없음" 선택 시 꺼지는지
- [ ] 저장 후 새로고침했을 때 응답과 절대질문이 그대로 복원되는지 ← **가장 중요.** 문항 id가 바뀌었다면 여기서 응답이 사라진다

---

## Self-Review 결과

**스펙 커버리지** — 이 계획은 스펙 §10의 1단계만 다룬다. §3 점수 계산·§4 보정·§5 짝짓기는 2단계 계획에서 다룬다. 1단계가 스펙에서 담당하는 것은 §2.1의 `app/survey/catalog.py`와 §7의 `GET /survey/questions` 두 항목이며, 각각 Task 1과 Task 2가 구현한다. `category` 필드는 §3.4 카테고리 가중치의 전제라서 지금 넣는다.

**타입 일관성** — 백엔드 dataclass 필드명(`rank_items`·`scale_labels`·`male_only`·`no_pref_id`)이 Pydantic 스키마, 프론트 `Question` 인터페이스, `QuestionField`·`Survey.tsx` 사용처까지 동일하게 snake_case로 유지된다. 프론트 기존 코드는 camelCase(`rankItems` 등)를 쓰고 있었으므로 Task 4·5에서 전부 교체한다 — 교체 지점을 각 스텝에 명시했다.

**알려진 위험** — 문항 id가 하나라도 달라지면 기존 유저의 저장된 응답이 조용히 사라진다. Task 1 Step 4에서 "한 글자도 바꾸지 않는다"를 명시했고, 수동 검증 마지막 항목이 이를 잡는다.
