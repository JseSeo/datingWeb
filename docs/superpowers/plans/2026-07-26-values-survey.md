# 가치관 설문 (Values Survey) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프론트 `/survey` 페이지를 구축한다 — self(본인)/partner(상대 선호) 45문항 카탈로그, 절대질문(최대 2), 부분저장. 백엔드는 `User.gender` 추가 + `PUT /me/survey` 얕은 구조 검증.

**Architecture:** 질문 카탈로그는 프론트 코드에만 정적 정의(`frontend/src/pages/Survey/questions.ts` = 단일 진실원). 백엔드 `Survey.answers`는 제네릭 JSON 유지, 구조 규칙만 얕게 검증. 매칭은 `A.self ↔ B.partner` 양방향 비교 전제이나 **매칭 로직은 범위 밖(보류)** — 이 플랜은 데이터 구조/입력 UI만 만든다.

**Tech Stack:** Backend = FastAPI + SQLAlchemy 2.0 + Alembic + pytest. Frontend = React(Vite) + react-router + Vitest + @testing-library/react + TypeScript.

## Global Constraints

- **매칭 알고리즘 구현 금지.** "매칭 알고리즘 설계 시작해" 명령 전까지 절대 금지. 설문은 데이터/UI만.
- **데이터 shape 고정:** `answers = { "responses": { "<id>": <값> }, "absolute": ["<id>", ...] }`.
- **absolute 규칙:** 최대 2개 · partner 문항 id만 · "상관없음" 값 문항 불가 · 모든 id가 `responses` key에 존재.
- **카탈로그는 프론트에만.** 백엔드는 문항 id/값 타입/완료 여부/self·partner/남자국한을 검증하지 않는다(카탈로그 사본 없음).
- **User.gender = "male" | "female" 2개만** (기타/거부 없음). 가입 시 필수 수집.
- **grooming_self = 남자국한** (`gender==="male"`만 노출·집계). 여성은 이 문항을 응답가능 분모에서 제외.
- **얼굴상(face) 목록·이미지 = TBD 플레이스홀더.** 운영 전 교체. `faceTypes.ts`에 placeholder 3~4개 + 에셋경로 문자열.
- **디자인 토큰:** 배경 `#FFF5E6`, 코랄 `#FF7F5C`, 오렌지 `#FF9472`, max-width 390px 모바일 우선. 임의 색상 금지.
- **API URL:** `VITE_API_URL` 환경변수만. 하드코딩 금지.
- **커밋 형식:** `<prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **테스트 명령:** 백 `cd backend && uv run pytest -v` · 프론트 `cd frontend && npm run test`, `npx tsc --noEmit`, `npm run build`.
- **git 커밋/푸시/PR = 사용자 허락 후만.** 각 Task의 커밋 스텝은 허락 전제하에 실행.

**참고 — 현재 코드 사실(구현 기준선):**
- Alembic HEAD = `8ed1fb6913e1` (initial schema, 유일 revision). 새 revision은 이 위에.
- `User` 모델: `backend/app/models/user.py` — gender 컬럼 없음. `Enum` import는 `from sqlalchemy import ... Enum ...` 이미 존재.
- `RegisterRequest`: `backend/app/schemas/auth.py` — email/password/name/university/agreed_terms/agreed_privacy/agreed_age_14.
- `register()`: `backend/app/api/auth.py:15-38`.
- `UserOut`: `backend/app/schemas/user.py:6-21`.
- `Survey` 모델: `backend/app/models/survey.py` (answers JSON). `SurveySubmit`/`SurveyOut`: `backend/app/schemas/survey.py`. 엔드포인트: `backend/app/api/me.py:156-181`.
- 프론트 타입: `frontend/src/lib/types.ts`. API: `frontend/src/lib/api.ts`. 라우팅: `frontend/src/App.tsx`. 보호: `frontend/src/components/ProtectedRoute.tsx`.
- **register 호출 테스트 파일(9개, gender 필수화 시 전부 수정):** `test_auth.py`, `test_survey.py`, `test_me.py`, `test_verification.py`, `test_withdraw.py`, `test_reports.py`, `test_profile_photo.py`, `test_game.py`, `conftest.py(admin_client)`.

---

## Task 1: `User.gender` 컬럼 + register 반영 + 기존 테스트 그린 유지

**Files:**
- Modify: `backend/app/models/user.py` (gender 컬럼 추가)
- Modify: `backend/app/schemas/auth.py` (RegisterRequest.gender)
- Modify: `backend/app/schemas/user.py` (UserOut.gender)
- Modify: `backend/app/api/auth.py:28-34` (register가 gender 저장)
- Modify(테스트 payload에 gender 추가): `backend/tests/test_auth.py`, `test_survey.py`, `test_me.py`, `test_verification.py`, `test_withdraw.py`, `test_reports.py`, `test_profile_photo.py`, `test_game.py`, `conftest.py`
- Test: `backend/tests/test_auth.py` (신규 gender 검증 테스트)

**Interfaces:**
- Produces: `RegisterRequest.gender: Literal["male","female"]` (필수). `User.gender` 컬럼. `UserOut.gender: str`. 프론트/후속 Task가 `/me` 응답에서 `gender`를 읽어 grooming_self 노출 판단.

> **⚠️ 주의:** gender를 `nullable=False`로 추가하고 register가 값을 넣지 않으면 모든 register 호출이 NOT NULL 위반으로 즉시 실패한다. 그래서 모델·스키마·엔드포인트·기존 테스트 payload를 **한 Task 안에서 같이** 수정해 그린을 유지한다. conftest는 `create_all`로 테이블을 만들므로(마이그레이션 미사용) 이 Task에서 마이그레이션은 불필요 — 마이그레이션은 Task 2.

- [ ] **Step 1: 신규 실패 테스트 작성** — `backend/tests/test_auth.py` 하단에 추가

```python
def test_register_persists_gender(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "gender@korea.ac.kr",
        "password": "password123",
        "name": "김성별",
        "university": "고려대학교",
        "gender": "female",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    assert res.status_code == 201
    assert res.json()["gender"] == "female"


def test_register_rejects_missing_gender(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "nogender@korea.ac.kr",
        "password": "password123",
        "name": "김무성별",
        "university": "고려대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    assert res.status_code == 422


def test_register_rejects_invalid_gender(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "badgender@korea.ac.kr",
        "password": "password123",
        "name": "김잘못",
        "university": "고려대학교",
        "gender": "other",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    assert res.status_code == 422
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: 신규 3개 FAIL (gender 미지원 → 422 안 나거나 응답에 gender 없음), 그리고 기존 테스트도 아직 그린.

- [ ] **Step 3: 모델·스키마·엔드포인트 구현**

`backend/app/models/user.py` — UserStatus enum 아래에 GenderEnum 추가하고 User에 컬럼 추가:

```python
class Gender(str, enum.Enum):
    male = "male"
    female = "female"
```

User 클래스 안, `university` 컬럼 바로 아래에 추가:

```python
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender"), nullable=False
    )
```

`backend/app/schemas/auth.py` — 상단 import에 `Literal` 추가하고 RegisterRequest에 필드 추가:

```python
from typing import Literal
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    university: str
    gender: Literal["male", "female"]
    agreed_terms: bool
    agreed_privacy: bool
    agreed_age_14: bool
    # (기존 field_validator 유지)
```

`backend/app/schemas/user.py` — UserOut에 `university` 아래 추가:

```python
    gender: str
```

`backend/app/api/auth.py` — register의 User 생성에 gender 추가:

```python
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        university=payload.university,
        gender=payload.gender,
        terms_agreed_at=datetime.utcnow(),
    )
```

- [ ] **Step 4: 기존 테스트 payload에 gender 추가 (9개 파일)**

각 파일에서 `/auth/register` 로 보내는 모든 json payload에 `"gender": "male",` 한 줄을 추가한다(값은 male 고정, 이 테스트들은 gender를 검증하지 않음). 대상:
- `test_auth.py`: `test_register_new_user`, `test_register_duplicate_email`, `test_register_weak_password`, `test_login_success`, `test_login_wrong_password`, `_full_payload` 의 base dict.
- `test_survey.py`: `_register_and_get_headers` 의 payload.
- `conftest.py`: `admin_client` 의 register payload.
- `test_me.py`, `test_verification.py`, `test_withdraw.py`, `test_reports.py`, `test_profile_photo.py`, `test_game.py`: 각 파일의 모든 register payload (register 헬퍼가 있으면 그 한 곳만).

확인 명령(누락 잡기): 아래가 **빈 결과여야** 함(= gender 없는 register payload 없음). Grep 도구로 `/auth/register` 호출 블록을 열어 `gender` 누락 여부 육안 확인. (register 라인 수와 gender 라인 수 비교)

- [ ] **Step 5: 전체 백엔드 테스트 그린 확인**

Run: `cd backend && uv run pytest -v`
Expected: 전부 PASS (신규 gender 3개 포함, 기존 전부 그린).

- [ ] **Step 6: 커밋**

```bash
git add backend/app/models/user.py backend/app/schemas/auth.py backend/app/schemas/user.py backend/app/api/auth.py backend/tests
git commit -m "feat(backend): User.gender 추가 (가입 시 필수 수집, male/female)"
```

---

## Task 2: gender 컬럼 Alembic 마이그레이션

**Files:**
- Create: `backend/alembic/versions/<new_rev>_add_user_gender.py`

**Interfaces:**
- Consumes: Task 1의 `User.gender` 모델 컬럼.
- Produces: HEAD가 `8ed1fb6913e1` → 새 revision으로 이동. `users.gender` NOT NULL 컬럼 + `gender` enum 타입.

> **주의:** 기존 dev DB에 users 행이 있으면 NOT NULL 컬럼 추가가 실패한다. autogenerate 결과를 손봐 `server_default="male"` 를 붙여 안전하게 적용한다(운영 전이라 값은 무의미, 이후 신규 가입은 endpoint가 항상 채움). 테스트는 마이그레이션을 쓰지 않으므로(conftest `create_all`) 이 Task는 pytest 영향 없음.

- [ ] **Step 1: 마이그레이션 자동생성**

Run: `cd backend && uv run alembic revision --autogenerate -m "add user gender"`
Expected: `backend/alembic/versions/`에 새 파일 생성. `down_revision = "8ed1fb6913e1"` 확인.

- [ ] **Step 2: 생성 파일 손보기**

`upgrade()` 의 gender 컬럼 add에 `server_default` 추가(존재 행 안전 적용):

```python
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "gender",
            sa.Enum("male", "female", name="gender"),
            nullable=False,
            server_default="male",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "gender")
    sa.Enum(name="gender").drop(op.get_bind(), checkfirst=True)
```

(autogenerate가 이미 만든 형태가 위와 다르면 위 내용으로 정리. enum 타입 drop 라인은 Postgres용 — SQLite면 무해.)

- [ ] **Step 3: 마이그레이션 적용 확인**

Run: `cd backend && uv run alembic upgrade head`
Expected: 에러 없이 적용. `uv run alembic current` 가 새 revision 표시.

- [ ] **Step 4: 커밋**

```bash
git add backend/alembic/versions
git commit -m "feat(backend): gender 컬럼 alembic revision"
```

---

## Task 3: `PUT /me/survey` 얕은 구조 검증 + 기존 survey 테스트 신 shape 전환

**Files:**
- Modify: `backend/app/api/me.py:167-181` (`save_survey` 검증 추가)
- Test: `backend/tests/test_survey.py` (기존 6개 payload를 신 shape로 재작성 + 검증 실패 케이스 추가)

**Interfaces:**
- Consumes: 없음(기존 Survey 모델/스키마 재사용).
- Produces: `PUT /me/survey`가 `answers` 구조 위반 시 `400`. 규칙: 최상위 `{responses: dict, absolute: list}`, `absolute` 원소는 str, `len(absolute) ≤ 2`, `absolute` 의 모든 id가 `responses` key에 존재.

> **⚠️ 계약 변경:** 기존 `test_survey.py`는 평면 `{"answers": {"q1": 3}}` 를 보낸다. 새 검증은 `{responses, absolute}` 를 강제하므로 기존 6개 테스트를 신 shape로 재작성한다(이건 스펙이 정한 계약이라 정상). 검증은 pydantic이 아니라 **엔드포인트 안에서** 수행해야 400을 반환한다(pydantic 실패는 422).

- [ ] **Step 1: 테스트 신 shape로 재작성 + 검증 케이스 추가**

`backend/tests/test_survey.py`의 본문 테스트를 아래로 교체(헬퍼 `_register_and_get_headers`는 Task 1에서 gender 추가된 상태 유지):

```python
def _valid_answers(**overrides):
    ans = {"responses": {"height_self": 175, "height_pref": "175_185"},
           "absolute": []}
    ans.update(overrides)
    return ans


def test_save_survey(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"]["responses"]["height_self"] == 175
    assert data["updated_at"] is not None


def test_get_survey_after_save(client: TestClient):
    headers = _register_and_get_headers(client, "get@test.com")
    client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"]["responses"]["height_pref"] == "175_185"


def test_get_survey_empty_when_none(client: TestClient):
    headers = _register_and_get_headers(client, "empty@test.com")
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {}


def test_update_survey_overwrites(client: TestClient):
    headers = _register_and_get_headers(client, "update@test.com")
    client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    response = client.put("/me/survey", json={
        "answers": _valid_answers(responses={"height_self": 180}, absolute=[])
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"]["responses"] == {"height_self": 180}


def test_put_survey_unauthorized(client: TestClient):
    response = client.put("/me/survey", json={"answers": _valid_answers()})
    assert response.status_code == 401


def test_get_survey_unauthorized(client: TestClient):
    response = client.get("/me/survey")
    assert response.status_code == 401


def test_reject_missing_responses(client: TestClient):
    headers = _register_and_get_headers(client, "r1@test.com")
    res = client.put("/me/survey", json={"answers": {"absolute": []}}, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_not_list(client: TestClient):
    headers = _register_and_get_headers(client, "r2@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1}, "absolute": "nope"}
    }, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_too_many(client: TestClient):
    headers = _register_and_get_headers(client, "r3@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1, "b": 2, "c": 3},
                    "absolute": ["a", "b", "c"]}
    }, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_unknown_id(client: TestClient):
    headers = _register_and_get_headers(client, "r4@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1}, "absolute": ["ghost"]}
    }, headers=headers)
    assert res.status_code == 400
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_survey.py -v`
Expected: 검증 4개(reject_*) FAIL (아직 200 반환).

- [ ] **Step 3: 검증 구현** — `backend/app/api/me.py` `save_survey` 함수 상단에 구조 검증 추가

```python
@router.put("/survey", response_model=SurveyOut)
def save_survey(
    payload: SurveySubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_answers(payload.answers)
    survey = db.query(Survey).filter(Survey.user_id == current_user.id).first()
    if survey:
        survey.answers = payload.answers
    else:
        survey = Survey(user_id=current_user.id, answers=payload.answers)
        db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey
```

같은 파일에 헬퍼 추가(라우터 정의 위, 상수 아래):

```python
def _validate_answers(answers: dict) -> None:
    responses = answers.get("responses")
    absolute = answers.get("absolute")
    if not isinstance(responses, dict) or not isinstance(absolute, list):
        raise HTTPException(status_code=400, detail="설문 형식이 올바르지 않습니다")
    if not all(isinstance(x, str) for x in absolute):
        raise HTTPException(status_code=400, detail="절대질문 형식이 올바르지 않습니다")
    if len(absolute) > 2:
        raise HTTPException(status_code=400, detail="절대질문은 최대 2개입니다")
    if any(qid not in responses for qid in absolute):
        raise HTTPException(status_code=400, detail="절대질문은 응답한 문항만 가능합니다")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_survey.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 백엔드 회귀 확인**

Run: `cd backend && uv run pytest -v`
Expected: 전부 PASS.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/me.py backend/tests/test_survey.py
git commit -m "feat(backend): PUT /me/survey 얕은 구조 검증 (responses/absolute)"
```

---

## Task 4: 프론트 회원가입 성별 라디오

**Files:**
- Modify: `frontend/src/lib/types.ts` (RegisterPayload.gender, UserOut.gender)
- Modify: `frontend/src/pages/Register/Register.tsx` (성별 라디오)
- Modify: `frontend/src/pages/Register/Register.test.tsx` (성별 선택 테스트)

**Interfaces:**
- Produces: `RegisterPayload.gender: "male" | "female"`. `UserOut.gender: "male" | "female"` (후속 Survey가 `useAuth().user.gender` 로 grooming_self 노출 판단).

- [ ] **Step 1: 실패 테스트 작성** — `Register.test.tsx`에 추가(기존 render 헬퍼 패턴 재사용)

```tsx
it("성별 미선택이면 제출 불가", () => {
  render(<Register />, { wrapper: Wrapper });
  fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "a@b.com" } });
  fireEvent.change(screen.getByLabelText(/비밀번호/), { target: { value: "password123" } });
  fireEvent.change(screen.getByLabelText("이름"), { target: { value: "홍길동" } });
  fireEvent.change(screen.getByLabelText("학교"), { target: { value: "서울대" } });
  // 전체 동의
  fireEvent.click(screen.getByLabelText("전체 동의"));
  expect(screen.getByRole("button", { name: /가입하기/ })).toBeDisabled();
});

it("성별 라디오가 렌더된다", () => {
  render(<Register />, { wrapper: Wrapper });
  expect(screen.getByLabelText("남")).toBeInTheDocument();
  expect(screen.getByLabelText("여")).toBeInTheDocument();
});
```

(기존 테스트에 `Wrapper`/render 방식이 있으면 그걸 따르고, 없으면 `<MemoryRouter>`로 감싼다. 기존 파일 상단 import 패턴 유지.)

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- Register`
Expected: 성별 테스트 FAIL (라디오 없음), 버튼 disabled 조건 미반영.

- [ ] **Step 3: 타입 + 폼 구현**

`frontend/src/lib/types.ts`:

```ts
export interface UserOut {
  // ...기존 필드...
  university: string;
  gender: "male" | "female";
  status: UserStatus;
  // ...
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  university: string;
  gender: "male" | "female";
  agreed_terms: boolean;
  agreed_privacy: boolean;
  agreed_age_14: boolean;
}
```

`Register.tsx` — 상태 추가, 라디오 렌더, 제출 payload/검증/disabled 반영:

```tsx
const [gender, setGender] = useState<"male" | "female" | "">("");
```

`validate()` 에 추가:

```tsx
    if (!gender) return "성별을 선택하세요";
```

학교 Input 아래에 라디오 삽입:

```tsx
        <fieldset className={styles.gender}>
          <legend>성별</legend>
          <label>
            <input type="radio" name="gender" checked={gender === "male"}
              onChange={() => setGender("male")} /> 남
          </label>
          <label>
            <input type="radio" name="gender" checked={gender === "female"}
              onChange={() => setGender("female")} /> 여
          </label>
        </fieldset>
```

`registerUser({...})` 호출에 `gender` 추가(타입이 `"male"|"female"`로 좁혀지도록 제출 전 `validate()` 통과 보장 — validate가 빈값 막음. 호출부에서 `gender as "male" | "female"`):

```tsx
      await registerUser({
        email, password, name: name.trim(), university: university.trim(),
        gender: gender as "male" | "female",
        agreed_terms: agreedTerms, agreed_privacy: agreedPrivacy, agreed_age_14: agreedAge,
      });
```

제출 버튼 disabled 조건에 gender 포함:

```tsx
        <Button type="submit" disabled={submitting || !allAgreed || !gender}>
```

- [ ] **Step 4: 테스트 통과 + 타입체크**

Run: `cd frontend && npm run test -- Register`
Expected: PASS.
Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/pages/Register
git commit -m "feat(frontend): 회원가입 성별 라디오 (남/여)"
```

---

## Task 5: Survey 도메인 타입 + 얼굴상 placeholder + API 함수

**Files:**
- Create: `frontend/src/pages/Survey/types.ts`
- Create: `frontend/src/pages/Survey/faceTypes.ts`
- Modify: `frontend/src/lib/types.ts` (SurveyData 타입)
- Modify: `frontend/src/lib/api.ts` (getSurvey, saveSurvey)
- Test: `frontend/src/pages/Survey/faceTypes.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `QuestionType`, `Section`, `Choice`, `FaceChoice`, `Question`, `SurveyResponses`, `AnswerValue`.
  - `SurveyData` (lib/types): `{ responses: Record<string, unknown>; absolute: string[] }`.
  - `getSurvey(): Promise<{ answers: SurveyData | Record<string, never> }>`, `saveSurvey(answers: SurveyData): Promise<{ answers: SurveyData }>`.
  - `FACE_TYPES: FaceChoice[]`, `FACE_ANY_ID = "any"`.

> **범위 밖 타입:** `range` 타입은 45문항 카탈로그에서 쓰이지 않으므로 정의/구현하지 않는다(YAGNI).

- [ ] **Step 1: 실패 테스트 작성** — `frontend/src/pages/Survey/faceTypes.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { FACE_TYPES, FACE_ANY_ID } from "./faceTypes";

describe("faceTypes placeholder", () => {
  it("최소 2개 이상 얼굴상 + 각 항목 id/label/image 보유", () => {
    expect(FACE_TYPES.length).toBeGreaterThanOrEqual(2);
    for (const f of FACE_TYPES) {
      expect(f.id).toBeTruthy();
      expect(f.label).toBeTruthy();
      expect(f.image).toBeTruthy();
    }
  });
  it("상관없음 id가 얼굴상 목록과 겹치지 않는다", () => {
    expect(FACE_TYPES.some((f) => f.id === FACE_ANY_ID)).toBe(false);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- faceTypes`
Expected: FAIL (모듈 없음).

- [ ] **Step 3: types.ts 작성** — `frontend/src/pages/Survey/types.ts`

```ts
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
  image: string; // 에셋경로 (placeholder, 운영 전 교체)
}

export interface Question {
  id: string;
  section: Section;
  label: string;
  type: QuestionType;
  choices?: Choice[];          // single | multi
  face?: boolean;              // image-single | image-multi → FACE_TYPES 사용
  rankItems?: Choice[];        // ranking
  scaleLabels?: [string, string]; // scale 양끝 라벨 [1, 5]
  unit?: string;               // number (예: "cm")
  maleOnly?: boolean;          // grooming_self
  noPrefId?: string;           // 이 값이면 절대질문 불가 ("상관없음" 선택지 id)
}

export type AnswerValue = number | string | string[];
export type SurveyResponses = Record<string, AnswerValue>;
```

- [ ] **Step 4: faceTypes.ts 작성** — `frontend/src/pages/Survey/faceTypes.ts`

```ts
import type { FaceChoice } from "./types";

// TODO(운영 전 교체): 얼굴상 목록·이미지 미확정(TBD, 에셋 의존).
// 실제 AI생성/실사진 확정 시 교체. 이미지 경로도 실제 에셋으로.
export const FACE_ANY_ID = "any";

export const FACE_TYPES: FaceChoice[] = [
  { id: "type_a", label: "강아지상", image: "/faces/placeholder-a.png" },
  { id: "type_b", label: "고양이상", image: "/faces/placeholder-b.png" },
  { id: "type_c", label: "곰상", image: "/faces/placeholder-c.png" },
  { id: "type_d", label: "여우상", image: "/faces/placeholder-d.png" },
];
```

- [ ] **Step 5: lib/types.ts + lib/api.ts 확장**

`frontend/src/lib/types.ts` 하단에:

```ts
export interface SurveyData {
  responses: Record<string, unknown>;
  absolute: string[];
}

export interface SurveyOut {
  answers: SurveyData | Record<string, never>;
  updated_at: string | null;
}
```

`frontend/src/lib/api.ts` — import에 `SurveyData, SurveyOut` 추가하고 함수 추가:

```ts
export function getSurvey(): Promise<SurveyOut> {
  return apiFetch<SurveyOut>("/me/survey", { method: "GET" });
}

export function saveSurvey(answers: SurveyData): Promise<SurveyOut> {
  return apiFetch<SurveyOut>("/me/survey", {
    method: "PUT",
    body: JSON.stringify({ answers }),
  });
}
```

- [ ] **Step 6: 테스트 + 타입체크 통과**

Run: `cd frontend && npm run test -- faceTypes`
Expected: PASS.
Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/pages/Survey/types.ts frontend/src/pages/Survey/faceTypes.ts frontend/src/pages/Survey/faceTypes.test.ts frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): Survey 도메인 타입 + 얼굴상 placeholder + survey API"
```

---

## Task 6: 질문 카탈로그 `questions.ts` (45문항) + 구조 테스트

**Files:**
- Create: `frontend/src/pages/Survey/questions.ts`
- Test: `frontend/src/pages/Survey/questions.test.ts`

**Interfaces:**
- Consumes: `Question`, `Choice` (types.ts), `FACE_TYPES` (faceTypes.ts).
- Produces: `QUESTIONS: Question[]` (45개). 후속 Task(QuestionField, Survey 페이지)가 이 배열을 렌더/집계.

- [ ] **Step 1: 구조 테스트 작성** — `frontend/src/pages/Survey/questions.test.ts`

```ts
import { describe, it, expect } from "vitest";
import { QUESTIONS } from "./questions";

describe("questions catalog", () => {
  it("총 45문항", () => {
    expect(QUESTIONS.length).toBe(45);
  });
  it("id 중복 없음", () => {
    const ids = QUESTIONS.map((q) => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it("single/multi 문항은 choices 보유", () => {
    for (const q of QUESTIONS) {
      if (q.type === "single" || q.type === "multi") {
        expect(q.choices && q.choices.length > 0).toBe(true);
      }
    }
  });
  it("ranking 문항은 rankItems 보유", () => {
    for (const q of QUESTIONS.filter((q) => q.type === "ranking")) {
      expect(q.rankItems && q.rankItems.length > 0).toBe(true);
    }
  });
  it("noPrefId는 partner 문항에만 존재", () => {
    for (const q of QUESTIONS) {
      if (q.noPrefId) expect(q.section).toBe("partner");
    }
  });
  it("noPrefId가 있으면 해당 id가 choices에 존재(비-face)", () => {
    for (const q of QUESTIONS) {
      if (q.noPrefId && !q.face) {
        expect(q.choices?.some((c) => c.id === q.noPrefId)).toBe(true);
      }
    }
  });
  it("grooming_self만 maleOnly", () => {
    const maleOnly = QUESTIONS.filter((q) => q.maleOnly).map((q) => q.id);
    expect(maleOnly).toEqual(["grooming_self"]);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- questions`
Expected: FAIL (모듈 없음).

- [ ] **Step 3: 카탈로그 작성** — `frontend/src/pages/Survey/questions.ts`

```ts
import type { Question } from "./types";
import { FACE_ANY_ID } from "./faceTypes";

// 단일 진실원(§6 design doc, 45문항). 백엔드는 이 카탈로그를 모른다.
// 시/도 17개 (행정표준). 운영 전 팀 대학목록과 별개.
const SIDO = [
  "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
  "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
].map((s) => ({ id: s, label: s }));

export const QUESTIONS: Question[] = [
  // ── 6.1 외모·스타일 ──
  { id: "height_self", section: "self", label: "내 키", type: "number", unit: "cm" },
  { id: "height_pref", section: "partner", label: "원하는 상대 키", type: "single",
    choices: [
      { id: "u165", label: "~165" }, { id: "165_175", label: "165~175" },
      { id: "175_185", label: "175~185" }, { id: "o185", label: "185↑" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "face_self", section: "self", label: "내 얼굴상", type: "image-single", face: true },
  { id: "face_pref", section: "partner", label: "원하는 상대 얼굴상", type: "image-multi",
    face: true, noPrefId: FACE_ANY_ID },
  { id: "style_self", section: "self", label: "내 스타일", type: "multi",
    choices: [
      { id: "casual", label: "캐주얼" }, { id: "formal", label: "포멀" },
      { id: "street", label: "스트릿" }, { id: "minimal", label: "미니멀" },
      { id: "vintage", label: "빈티지" },
    ] },
  { id: "style_pref", section: "partner", label: "원하는 상대 스타일", type: "multi",
    choices: [
      { id: "casual", label: "캐주얼" }, { id: "formal", label: "포멀" },
      { id: "street", label: "스트릿" }, { id: "minimal", label: "미니멀" },
      { id: "vintage", label: "빈티지" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "tattoo_self", section: "self", label: "내 문신 여부", type: "single",
    choices: [{ id: "yes", label: "있음" }, { id: "no", label: "없음" }] },
  { id: "tattoo_pref", section: "partner", label: "문신 선호", type: "single",
    choices: [
      { id: "ok", label: "있어도됨" }, { id: "none", label: "없었으면" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "piercing_self", section: "self", label: "내 피어싱 여부", type: "single",
    choices: [{ id: "yes", label: "있음" }, { id: "no", label: "없음" }] },
  { id: "piercing_pref", section: "partner", label: "피어싱 선호", type: "single",
    choices: [
      { id: "ok", label: "있어도됨" }, { id: "none", label: "없었으면" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "grooming_self", section: "self", label: "외모관리 습관", type: "multi", maleOnly: true,
    choices: [
      { id: "lotion", label: "로션" }, { id: "sunscreen", label: "썬크림" },
      { id: "hair", label: "머리손질" }, { id: "makeup", label: "화장" },
      { id: "nails", label: "손톱관리" },
    ] },

  // ── 6.2 가치관·신념 ──
  { id: "politics_self", section: "self", label: "정치 성향", type: "single",
    choices: [
      { id: "progressive", label: "진보" }, { id: "moderate", label: "중도" },
      { id: "conservative", label: "보수" }, { id: "unknown", label: "모름" },
    ] },
  { id: "politics_pref", section: "partner", label: "상대 정치 성향", type: "single",
    choices: [
      { id: "progressive", label: "진보" }, { id: "moderate", label: "중도" },
      { id: "conservative", label: "보수" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "religion_self", section: "self", label: "종교", type: "single",
    choices: [
      { id: "none", label: "무교" }, { id: "christian", label: "기독교" },
      { id: "catholic", label: "천주교" }, { id: "buddhist", label: "불교" },
      { id: "other", label: "기타" },
    ] },
  { id: "religion_pref", section: "partner", label: "상대 종교", type: "multi",
    choices: [
      { id: "christian", label: "기독교" }, { id: "catholic", label: "천주교" },
      { id: "buddhist", label: "불교" }, { id: "none", label: "무교" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },

  // ── 6.3 관계·감정 ──
  { id: "contact_freq_self", section: "self", label: "내 연락 빈도 성향", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "contact_freq_pref", section: "partner", label: "원하는 상대 연락 빈도", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "date_freq_self", section: "self", label: "내 데이트 빈도 성향", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "date_freq_pref", section: "partner", label: "원하는 상대 데이트 빈도", type: "scale",
    scaleLabels: ["가끔", "자주"] },
  { id: "alone_time_self", section: "self", label: "내 개인시간 필요 정도", type: "scale",
    scaleLabels: ["적음", "많음"] },
  { id: "alone_time_pref", section: "partner", label: "원하는 상대 개인시간 필요 정도", type: "scale",
    scaleLabels: ["적음", "많음"] },
  { id: "affection_self", section: "self", label: "내 애정표현 정도", type: "scale",
    scaleLabels: ["은은", "적극"] },
  { id: "affection_pref", section: "partner", label: "원하는 상대 애정표현 정도", type: "scale",
    scaleLabels: ["은은", "적극"] },
  { id: "conflict_style_self", section: "self", label: "내 갈등 시 반응", type: "single",
    choices: [
      { id: "immediate", label: "즉시품" }, { id: "later", label: "시간두고" },
      { id: "alone", label: "혼자삭힘" },
    ] },
  { id: "conflict_style_pref", section: "partner", label: "원하는 상대 갈등 반응", type: "single",
    choices: [
      { id: "immediate", label: "즉시품" }, { id: "later", label: "시간두고" },
      { id: "alone", label: "혼자삭힘" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "priority_rank_self", section: "self", label: "내 인생 우선순위", type: "ranking",
    rankItems: [
      { id: "lover", label: "연인" }, { id: "friend", label: "친구" },
      { id: "self_dev", label: "자기개발" }, { id: "family", label: "가족" },
    ] },
  { id: "priority_rank_pref", section: "partner", label: "원하는 상대 우선순위", type: "ranking",
    rankItems: [
      { id: "lover", label: "연인" }, { id: "friend", label: "친구" },
      { id: "self_dev", label: "자기개발" }, { id: "family", label: "가족" },
    ] },

  // ── 6.4 경제·생활·건강 ──
  { id: "date_budget_self", section: "self", label: "내 1회 데이트 예산", type: "single",
    choices: [
      { id: "u5", label: "5만↓" }, { id: "5_10", label: "5~10" },
      { id: "10_20", label: "10~20" }, { id: "20_30", label: "20~30" },
      { id: "o30", label: "30↑" },
    ] },
  { id: "date_budget_pref", section: "partner", label: "원하는 상대 예산", type: "single",
    choices: [
      { id: "u5", label: "5만↓" }, { id: "5_10", label: "5~10" },
      { id: "10_20", label: "10~20" }, { id: "20_30", label: "20~30" },
      { id: "o30", label: "30↑" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "cost_share_self", section: "self", label: "내 비용부담 선호", type: "single",
    choices: [
      { id: "dutch", label: "더치" }, { id: "alternate", label: "번갈아" },
      { id: "richer", label: "여유쪽더" }, { id: "me", label: "내가전담" },
    ] },
  { id: "cost_share_pref", section: "partner", label: "원하는 상대 비용부담", type: "single",
    choices: [
      { id: "dutch", label: "더치" }, { id: "alternate", label: "번갈아" },
      { id: "richer", label: "여유쪽더" }, { id: "partner", label: "상대전담" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "smoking_self", section: "self", label: "내 흡연", type: "single",
    choices: [
      { id: "none", label: "비흡연" }, { id: "sometimes", label: "가끔" },
      { id: "yes", label: "흡연" },
    ] },
  { id: "smoking_pref", section: "partner", label: "상대 흡연 선호", type: "single",
    choices: [
      { id: "none_only", label: "비흡연만" }, { id: "sometimes_ok", label: "가끔OK" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "drinking_self", section: "self", label: "내 음주 빈도", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "sometimes", label: "가끔" },
      { id: "often", label: "자주" },
    ] },
  { id: "drinking_pref", section: "partner", label: "상대 음주 선호", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "sometimes_ok", label: "가끔OK" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "exercise_self", section: "self", label: "내 운동 빈도", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "w1_2", label: "주1~2" },
      { id: "w3", label: "주3↑" },
    ] },
  { id: "exercise_pref", section: "partner", label: "상대 운동 선호", type: "single",
    choices: [
      { id: "none", label: "안함" }, { id: "w1_2", label: "주1~2" },
      { id: "w3", label: "주3↑" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "sleep_self", section: "self", label: "내 수면 패턴", type: "single",
    choices: [
      { id: "morning", label: "아침형" }, { id: "night", label: "올빼미" },
      { id: "irregular", label: "불규칙" },
    ] },
  { id: "sleep_pref", section: "partner", label: "상대 수면 선호", type: "single",
    choices: [
      { id: "morning", label: "아침형" }, { id: "night", label: "올빼미" },
      { id: "irregular", label: "불규칙" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "hobby_self", section: "self", label: "내 취미 성향", type: "single",
    choices: [
      { id: "indoor", label: "실내" }, { id: "outdoor", label: "실외" },
      { id: "both", label: "둘다" },
    ] },
  { id: "hobby_pref", section: "partner", label: "상대 취미 선호", type: "single",
    choices: [
      { id: "indoor", label: "실내" }, { id: "outdoor", label: "실외" },
      { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "residence_self", section: "self", label: "내 거주지", type: "single", choices: SIDO },
  { id: "residence_pref", section: "partner", label: "허용 이동거리", type: "single",
    choices: [
      { id: "h1", label: "차로 1시간↓" }, { id: "h2", label: "2시간↓" },
      { id: "h3", label: "3시간↓" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
  { id: "living_self", section: "self", label: "내 자취 여부", type: "single",
    choices: [
      { id: "independent", label: "자취" }, { id: "home", label: "본가" },
      { id: "dorm", label: "기숙사" },
    ] },
  { id: "living_pref", section: "partner", label: "상대 자취 선호", type: "single",
    choices: [
      { id: "prefer_independent", label: "자취선호" }, { id: "any", label: "상관없음" },
    ], noPrefId: "any" },
];
```

- [ ] **Step 4: 테스트 통과 + 타입체크**

Run: `cd frontend && npm run test -- questions`
Expected: PASS (45문항, 규칙 전부).
Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Survey/questions.ts frontend/src/pages/Survey/questions.test.ts
git commit -m "feat(frontend): 가치관 설문 문항 카탈로그 45문항"
```

---

## Task 7: `QuestionField` 렌더러 (타입별 입력 위젯)

**Files:**
- Create: `frontend/src/pages/Survey/QuestionField.tsx`
- Create: `frontend/src/pages/Survey/QuestionField.module.css`
- Test: `frontend/src/pages/Survey/QuestionField.test.tsx`

**Interfaces:**
- Consumes: `Question`, `AnswerValue` (types.ts), `FACE_TYPES` (faceTypes.ts).
- Produces: `QuestionField` 컴포넌트.

```ts
interface QuestionFieldProps {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
}
```

렌더 규칙:
- `single`: 라디오(choices). 선택 시 `onChange(choiceId)`.
- `multi`: 체크박스(choices) + "복수 선택 가능" 안내문. 값=선택 id 배열. 토글 시 배열 갱신.
- `scale`: 1~5 라디오/버튼, 양끝에 `scaleLabels[0]`, `scaleLabels[1]`. 값=정수.
- `number`: number input + `unit`. 값=정수(빈값이면 onChange 안 함).
- `ranking`: `rankItems` 목록, ▲/▼ 버튼으로 순서 변경. 값=id 순서 배열(초기 표시는 value 있으면 그 순서, 없으면 rankItems 순서).
- `image-single`: `FACE_TYPES` 썸네일 라디오. 값=faceId.
- `image-multi`: `FACE_TYPES` + "상관없음"(FACE_ANY_ID) 썸네일 체크박스 + "복수 선택 가능" 안내문. 값=id 배열.

- [ ] **Step 1: 실패 테스트 작성** — `QuestionField.test.tsx`

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuestionField } from "./QuestionField";
import type { Question } from "./types";

const single: Question = {
  id: "q_single", section: "self", label: "단일", type: "single",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};
const multi: Question = {
  id: "q_multi", section: "self", label: "복수", type: "multi",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};

describe("QuestionField", () => {
  it("single: 선택 시 choiceId onChange", () => {
    const onChange = vi.fn();
    render(<QuestionField question={single} value={undefined} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("A"));
    expect(onChange).toHaveBeenCalledWith("a");
  });

  it("multi: 복수 선택 가능 안내문 표시 + 배열 갱신", () => {
    const onChange = vi.fn();
    render(<QuestionField question={multi} value={["a"]} onChange={onChange} />);
    expect(screen.getByText("복수 선택 가능")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("B"));
    expect(onChange).toHaveBeenCalledWith(["a", "b"]);
  });

  it("scale: 1~5 + 양끝 라벨", () => {
    const onChange = vi.fn();
    const scale: Question = {
      id: "q_scale", section: "self", label: "척도", type: "scale",
      scaleLabels: ["낮음", "높음"],
    };
    render(<QuestionField question={scale} value={undefined} onChange={onChange} />);
    expect(screen.getByText("낮음")).toBeInTheDocument();
    expect(screen.getByText("높음")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "3" }));
    expect(onChange).toHaveBeenCalledWith(3);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- QuestionField`
Expected: FAIL (모듈 없음).

- [ ] **Step 3: QuestionField 구현** — `QuestionField.tsx`

```tsx
import type { Question, AnswerValue } from "./types";
import { FACE_TYPES, FACE_ANY_ID } from "./faceTypes";
import styles from "./QuestionField.module.css";

interface Props {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
}

function toggle(arr: string[], id: string): string[] {
  return arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id];
}

export function QuestionField({ question: q, value, onChange }: Props) {
  if (q.type === "single") {
    return (
      <div className={styles.field}>
        {q.choices!.map((c) => (
          <label key={c.id} className={styles.choice}>
            <input type="radio" name={q.id} checked={value === c.id}
              onChange={() => onChange(c.id)} />
            {c.label}
          </label>
        ))}
      </div>
    );
  }

  if (q.type === "multi") {
    const arr = Array.isArray(value) ? value : [];
    return (
      <div className={styles.field}>
        <p className={styles.hint}>복수 선택 가능</p>
        {q.choices!.map((c) => (
          <label key={c.id} className={styles.choice}>
            <input type="checkbox" checked={arr.includes(c.id)}
              onChange={() => onChange(toggle(arr, c.id))} />
            {c.label}
          </label>
        ))}
      </div>
    );
  }

  if (q.type === "scale") {
    return (
      <div className={styles.field}>
        <div className={styles.scaleRow}>
          <span className={styles.scaleEnd}>{q.scaleLabels?.[0]}</span>
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n} className={styles.scaleItem}>
              <input type="radio" name={q.id} aria-label={String(n)}
                checked={value === n} onChange={() => onChange(n)} />
              {n}
            </label>
          ))}
          <span className={styles.scaleEnd}>{q.scaleLabels?.[1]}</span>
        </div>
      </div>
    );
  }

  if (q.type === "number") {
    return (
      <div className={styles.field}>
        <input type="number" className={styles.number}
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            const v = e.target.value;
            if (v !== "") onChange(parseInt(v, 10));
          }} />
        {q.unit && <span className={styles.unit}>{q.unit}</span>}
      </div>
    );
  }

  if (q.type === "ranking") {
    const order = Array.isArray(value) && value.length
      ? value
      : q.rankItems!.map((i) => i.id);
    const labelOf = (id: string) => q.rankItems!.find((i) => i.id === id)?.label ?? id;
    const move = (idx: number, dir: -1 | 1) => {
      const next = [...order];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return;
      [next[idx], next[j]] = [next[j], next[idx]];
      onChange(next);
    };
    return (
      <ol className={styles.ranking}>
        {order.map((id, idx) => (
          <li key={id} className={styles.rankItem}>
            <span>{labelOf(id)}</span>
            <span>
              <button type="button" aria-label={`${labelOf(id)} 위로`}
                onClick={() => move(idx, -1)}>▲</button>
              <button type="button" aria-label={`${labelOf(id)} 아래로`}
                onClick={() => move(idx, 1)}>▼</button>
            </span>
          </li>
        ))}
      </ol>
    );
  }

  // image-single | image-multi
  const isMulti = q.type === "image-multi";
  const arr = Array.isArray(value) ? value : [];
  const faceOptions = isMulti
    ? [...FACE_TYPES, { id: FACE_ANY_ID, label: "상관없음", image: "" }]
    : FACE_TYPES;
  return (
    <div className={styles.field}>
      {isMulti && <p className={styles.hint}>복수 선택 가능</p>}
      <div className={styles.faceGrid}>
        {faceOptions.map((f) => {
          const selected = isMulti ? arr.includes(f.id) : value === f.id;
          return (
            <label key={f.id} className={styles.faceCell} data-selected={selected}>
              <input
                type={isMulti ? "checkbox" : "radio"}
                name={q.id}
                aria-label={f.label}
                checked={selected}
                onChange={() => onChange(isMulti ? toggle(arr, f.id) : f.id)}
              />
              {f.image && <img src={f.image} alt={f.label} className={styles.faceImg} />}
              <span>{f.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
```

`QuestionField.module.css` — 디자인 토큰 사용. 최소 스타일:

```css
.field { display: flex; flex-direction: column; gap: 8px; }
.choice { display: flex; align-items: center; gap: 8px; }
.hint { font-size: 12px; color: #FF7F5C; margin: 0; }
.scaleRow { display: flex; align-items: center; gap: 8px; }
.scaleItem { display: flex; flex-direction: column; align-items: center; font-size: 12px; }
.scaleEnd { font-size: 12px; color: #555; }
.number { width: 100px; padding: 6px; }
.unit { margin-left: 6px; }
.ranking { list-style: decimal inside; padding: 0; margin: 0; }
.rankItem { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
.faceGrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.faceCell { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.faceCell[data-selected="true"] { outline: 2px solid #FF7F5C; border-radius: 8px; }
.faceImg { width: 100%; max-width: 100px; aspect-ratio: 1; object-fit: cover; border-radius: 8px; }
```

- [ ] **Step 4: 테스트 통과 + 타입체크**

Run: `cd frontend && npm run test -- QuestionField`
Expected: PASS.
Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Survey/QuestionField.tsx frontend/src/pages/Survey/QuestionField.module.css frontend/src/pages/Survey/QuestionField.test.tsx
git commit -m "feat(frontend): QuestionField 타입별 입력 렌더러"
```

---

## Task 8: Survey 페이지 (섹션·진행률·절대질문·부분저장)

**Files:**
- Create: `frontend/src/pages/Survey/Survey.tsx`
- Create: `frontend/src/pages/Survey/Survey.module.css`
- Test: `frontend/src/pages/Survey/Survey.test.tsx`

**Interfaces:**
- Consumes: `QUESTIONS` (questions.ts), `QuestionField` (Task 7), `getSurvey`/`saveSurvey` (api.ts), `useAuth` (lib/auth) — `user.gender`.
- Produces: `Survey` 기본 export 컴포넌트 (Task 9가 라우팅).

페이지 동작:
1. 마운트 시 `getSurvey()` 로 기존 응답 로드 → `responses`/`absolute` state 초기화. 응답 없으면 빈 값.
2. **응답가능 문항** = `QUESTIONS` 중 `maleOnly && user.gender!=="male"` 이면 제외.
3. self 섹션 → partner 섹션 순으로 렌더(섹션 헤더 2개). 각 문항 = 라벨 + `<QuestionField>`.
4. **절대질문 토글**: partner 문항에만 ★ 버튼. 규칙 — (a) 아직 응답 안 한 문항 비활성, (b) 값이 `noPrefId`(상관없음)면 비활성, (c) 이미 2개 선택 && 본인 미선택이면 비활성. 선택 시 `absolute` 배열 토글.
5. **진행률**: 응답가능 문항 대비 응답 완료 수. (multi/image-multi는 배열 length>0, number는 숫자 존재, single/scale/ranking은 값 존재 시 완료.)
6. **저장**: "저장" 버튼 → `saveSurvey({responses, absolute})`. 부분저장 허용(전 문항 필수 아님, 통째 교체). 성공 시 안내.

- [ ] **Step 1: 실패 테스트 작성** — `Survey.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import Survey from "./Survey";

vi.mock("../../lib/api", () => ({
  getSurvey: vi.fn().mockResolvedValue({ answers: {}, updated_at: null }),
  saveSurvey: vi.fn().mockResolvedValue({ answers: { responses: {}, absolute: [] }, updated_at: "x" }),
}));
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user: { gender: "male" }, loading: false }),
}));

import { getSurvey, saveSurvey } from "../../lib/api";

describe("Survey page", () => {
  beforeEach(() => vi.clearAllMocks());

  it("마운트 시 기존 설문 로드", async () => {
    render(<Survey />);
    await waitFor(() => expect(getSurvey).toHaveBeenCalled());
  });

  it("남성이면 grooming_self(외모관리 습관) 노출", async () => {
    render(<Survey />);
    await waitFor(() =>
      expect(screen.getByText("외모관리 습관")).toBeInTheDocument());
  });

  it("저장 버튼 클릭 시 saveSurvey 호출", async () => {
    render(<Survey />);
    await waitFor(() => screen.getByText("외모관리 습관"));
    fireEvent.click(screen.getByRole("button", { name: /저장/ }));
    await waitFor(() => expect(saveSurvey).toHaveBeenCalled());
  });
});
```

여성 제외 테스트(별도 mock):

```tsx
describe("Survey page - female", () => {
  it("여성이면 grooming_self 미노출", async () => {
    vi.resetModules();
    vi.doMock("../../lib/auth", () => ({
      useAuth: () => ({ user: { gender: "female" }, loading: false }),
    }));
    vi.doMock("../../lib/api", () => ({
      getSurvey: vi.fn().mockResolvedValue({ answers: {}, updated_at: null }),
      saveSurvey: vi.fn(),
    }));
    const { default: SurveyF } = await import("./Survey");
    render(<SurveyF />);
    await waitFor(() => screen.getByText("내 키"));
    expect(screen.queryByText("외모관리 습관")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- Survey`
Expected: FAIL (모듈 없음).

- [ ] **Step 3: Survey 구현** — `Survey.tsx`

```tsx
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../lib/auth";
import { getSurvey, saveSurvey } from "../../lib/api";
import { QUESTIONS } from "./questions";
import { QuestionField } from "./QuestionField";
import type { AnswerValue, Question, SurveyResponses } from "./types";
import styles from "./Survey.module.css";

function isAnswered(q: Question, v: AnswerValue | undefined): boolean {
  if (v === undefined) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "string") return v !== "";
  return true; // number
}

export default function Survey() {
  const { user } = useAuth();
  const [responses, setResponses] = useState<SurveyResponses>({});
  const [absolute, setAbsolute] = useState<string[]>([]);
  const [status, setStatus] = useState<"" | "saving" | "saved" | "error">("");

  const visible = useMemo(
    () => QUESTIONS.filter((q) => !(q.maleOnly && user?.gender !== "male")),
    [user?.gender],
  );

  useEffect(() => {
    getSurvey().then((res) => {
      const a = res.answers as { responses?: SurveyResponses; absolute?: string[] };
      if (a && a.responses) {
        setResponses(a.responses);
        setAbsolute(a.absolute ?? []);
      }
    });
  }, []);

  const answeredCount = visible.filter((q) => isAnswered(q, responses[q.id])).length;

  function setValue(id: string, v: AnswerValue) {
    setResponses((prev) => ({ ...prev, [id]: v }));
  }

  function canToggleAbsolute(q: Question): boolean {
    if (q.section !== "partner") return false;
    const v = responses[q.id];
    if (!isAnswered(q, v)) return false;
    if (q.noPrefId) {
      if (v === q.noPrefId) return false;
      if (Array.isArray(v) && v.includes(q.noPrefId)) return false;
    }
    if (absolute.length >= 2 && !absolute.includes(q.id)) return false;
    return true;
  }

  function toggleAbsolute(id: string) {
    setAbsolute((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  async function handleSave() {
    setStatus("saving");
    try {
      // 상관없음이 됐거나 미응답/숨김이 된 문항은 absolute에서 정리
      const cleaned = absolute.filter((id) => {
        const q = visible.find((x) => x.id === id);
        if (!q) return false;
        const v = responses[id];
        if (!isAnswered(q, v)) return false;
        if (q.noPrefId) {
          if (v === q.noPrefId) return false;
          if (Array.isArray(v) && v.includes(q.noPrefId)) return false;
        }
        return true;
      });
      await saveSurvey({ responses, absolute: cleaned });
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }

  const sections: { key: "self" | "partner"; title: string }[] = [
    { key: "self", title: "나에 대해" },
    { key: "partner", title: "원하는 상대" },
  ];

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>가치관 설문</h1>
      <p className={styles.progress}>{answeredCount} / {visible.length} 응답</p>

      {sections.map((sec) => (
        <section key={sec.key}>
          <h2 className={styles.section}>{sec.title}</h2>
          {visible.filter((q) => q.section === sec.key).map((q) => (
            <div key={q.id} className={styles.question}>
              <div className={styles.qHead}>
                <span className={styles.qLabel}>{q.label}</span>
                {q.section === "partner" && (
                  <button type="button" className={styles.star}
                    aria-label={`${q.label} 절대질문`}
                    aria-pressed={absolute.includes(q.id)}
                    disabled={!canToggleAbsolute(q) && !absolute.includes(q.id)}
                    onClick={() => toggleAbsolute(q.id)}>
                    {absolute.includes(q.id) ? "★" : "☆"}
                  </button>
                )}
              </div>
              <QuestionField question={q} value={responses[q.id]}
                onChange={(v) => setValue(q.id, v)} />
            </div>
          ))}
        </section>
      ))}

      <p className={styles.absInfo}>절대질문 {absolute.length} / 2</p>
      {status === "saved" && <p className={styles.ok}>저장되었습니다</p>}
      {status === "error" && <p className={styles.err}>저장에 실패했습니다</p>}
      <button type="button" className={styles.save}
        disabled={status === "saving"} onClick={handleSave}>
        {status === "saving" ? "저장 중..." : "저장"}
      </button>
    </div>
  );
}
```

`Survey.module.css` — 디자인 토큰:

```css
.wrap { max-width: 390px; margin: 0 auto; padding: 16px; background: #FFF5E6; }
.title { font-size: 22px; margin-bottom: 4px; }
.progress { color: #FF7F5C; font-weight: 600; margin: 0 0 16px; }
.section { font-size: 18px; border-bottom: 2px solid #FF9472; padding-bottom: 4px; margin: 24px 0 12px; }
.question { padding: 12px 0; border-bottom: 1px solid #f0e0cc; }
.qHead { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.qLabel { font-weight: 600; }
.star { background: none; border: none; font-size: 20px; color: #FF7F5C; cursor: pointer; }
.star:disabled { color: #ccc; cursor: default; }
.absInfo { color: #555; font-size: 13px; margin-top: 16px; }
.save { width: 100%; padding: 12px; background: #FF7F5C; color: #fff; border: none; border-radius: 8px; font-size: 16px; margin-top: 8px; }
.save:disabled { opacity: 0.6; }
.ok { color: #2a8; }
.err { color: #c33; }
```

- [ ] **Step 4: 테스트 통과 + 타입체크**

Run: `cd frontend && npm run test -- Survey`
Expected: PASS (로드/남성노출/저장/여성제외).
Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Survey/Survey.tsx frontend/src/pages/Survey/Survey.module.css frontend/src/pages/Survey/Survey.test.tsx
git commit -m "feat(frontend): 설문 페이지 (섹션·진행률·절대질문·부분저장)"
```

---

## Task 9: `/survey` 라우트 연결 (active 유저)

**Files:**
- Modify: `frontend/src/App.tsx` (라우트 추가)
- Test: `frontend/src/App.test.tsx` (있으면 추가; 없으면 생략하고 수동 확인)

**Interfaces:**
- Consumes: `Survey` (Task 8), `ProtectedRoute`.
- Produces: `/survey` 경로, `requireStatus="active"`, `MainLayout` 하위.

- [ ] **Step 1: 라우트 추가** — `frontend/src/App.tsx`

import 추가:

```tsx
import Survey from "./pages/Survey/Survey";
```

`MainLayout` 자식 블록 안(`/game` 라우트 아래)에 추가:

```tsx
        <Route
          path="/survey"
          element={
            <ProtectedRoute requireStatus="active">
              <Survey />
            </ProtectedRoute>
          }
        />
```

- [ ] **Step 2: 타입체크 + 빌드 + 전체 테스트**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음.
Run: `cd frontend && npm run build`
Expected: 빌드 성공.
Run: `cd frontend && npm run test`
Expected: 전부 PASS.

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): /survey 라우트 (active 유저)"
```

---

## 최종 검증 (전체 완료 후)

- [ ] 백엔드 전체: `cd backend && uv run pytest -v` → 전부 PASS
- [ ] 프론트 전체: `cd frontend && npm run test` → 전부 PASS
- [ ] 타입: `cd frontend && npx tsc --noEmit` → 에러 없음
- [ ] 빌드: `cd frontend && npm run build` → 성공
- [ ] 마이그레이션: `cd backend && uv run alembic upgrade head` → 적용됨
- [ ] RESUME-survey.md 갱신(상태 = 구현 완료), design doc §11 미결(얼굴상 TBD)·CLAUDE.md 운영전교체 항목 확인
- [ ] 브랜치 `feat/values-survey` → 사용자에게 머지/PR 방식 확인 (finishing-a-development-branch)

## 미결·주의 (구현 후에도 유지)

- **얼굴상 목록·이미지 = placeholder.** `faceTypes.ts` TODO. 운영 전 실제 에셋 교체 필수.
- **매칭 로직 미구현.** absolute/self/partner는 데이터로만 저장. "매칭 알고리즘 설계 시작해" 전까지 매칭 사용 금지.
- **완료 판정(매칭 참여용)은 미구현.** 부분저장 허용 상태. 매칭 시점 별도 판정은 매칭 플랜에서.
