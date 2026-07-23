# 가입 동의 체크박스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 회원가입에 법적 필수 동의 3종(이용약관·개인정보처리방침·만14세)을 추가하고, 동의 시각을 서버 DB에 기록한다.

**Architecture:** 프론트에서 체크박스 게이트(가입 버튼 disable)로 1차 방어, 백엔드에서 3개 bool 검증 + `terms_agreed_at` 기록으로 2차 방어(개보법 §22 입증책임). 약관 문안은 placeholder 모달.

**Tech Stack:** 백엔드 FastAPI + SQLAlchemy 2.0 + Alembic + pytest / 프론트 React(Vite) + vitest + Testing Library.

## Global Constraints

- 근거 스펙: `docs/superpowers/specs/2026-07-17-signup-consent-design.md`
- 동의 3필드는 **필수 bool**. 하나라도 false → 백엔드 400 `"필수 약관에 동의해야 가입할 수 있습니다"`.
- `terms_agreed_at`은 **nullable** (기존 유저 NULL, 백필 안 함).
- 실제 약관/방침 **문안은 placeholder** — 팀/변호사 몫. 본 작업은 뼈대만.
- 마케팅/선택 동의·약관 버전관리 = 범위 밖 (YAGNI).
- 커밋 형식: `<prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **git commit은 각 Task 마지막 단계. push/PR은 사용자 허락 필수 — 계획에 없음.**
- 백엔드 테스트: `cd backend && uv run pytest -v` / 프론트: `cd frontend && npm run test`, `npx tsc --noEmit`, `npm run build`.

---

## File Structure

| 파일 | 책임 | 변경 |
|------|------|------|
| `backend/app/models/user.py` | User ORM | `terms_agreed_at` 컬럼 추가 |
| `backend/app/schemas/auth.py` | 가입 입력 스키마 | RegisterRequest 동의 3필드 |
| `backend/app/api/auth.py` | register 엔드포인트 | 동의 검증 + 기록 |
| `backend/alembic/versions/*` | 마이그레이션 | autogenerate 1개 |
| `backend/tests/test_auth.py` | 가입 테스트 | 동의 신규 테스트 + 기존 payload 수정 |
| `backend/tests/conftest.py` + 기타 7개 test 파일 | register 호출부 | payload에 동의 3필드 추가 (기계적) |
| `frontend/src/lib/types.ts` | RegisterPayload | 동의 3필드 |
| `frontend/src/pages/Register/Register.tsx` | 가입 폼 | 동의 UI + 게이트 + payload |
| `frontend/src/pages/Register/ConsentModal.tsx` | 약관/방침 모달 | 신규(placeholder) |
| `frontend/src/pages/Register/Register.test.tsx` | 폼 테스트 | 신규 |

---

## Task 1: 백엔드 — 동의 검증 + 기록 + 마이그레이션

**Files:**
- Modify: `backend/app/models/user.py:33-35` (created_at 뒤에 컬럼 추가)
- Modify: `backend/app/schemas/auth.py:4-8` (RegisterRequest 필드)
- Modify: `backend/app/api/auth.py:1-30` (import + register 검증/기록)
- Test: `backend/tests/test_auth.py` (신규 3개)
- Modify (기계적): `backend/tests/conftest.py`, `test_verification.py`, `test_withdraw.py`, `test_profile_photo.py`, `test_game.py`, `test_reports.py`, `test_survey.py`, `test_me.py` — 모든 `/auth/register` payload에 동의 3필드
- Migration: `backend/alembic/versions/*` (autogenerate)

**Interfaces:**
- Produces: `RegisterRequest`에 `agreed_terms: bool`, `agreed_privacy: bool`, `agreed_age_14: bool` (전부 필수). `User.terms_agreed_at: datetime | None`. register는 셋 다 true 아니면 400.

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_auth.py` 맨 아래 추가

```python
from tests.conftest import TestingSessionLocal
from app.models.user import User


def _full_payload(**overrides):
    base = {
        "email": "consent@korea.ac.kr",
        "password": "password123",
        "name": "김동의",
        "university": "고려대학교",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    }
    base.update(overrides)
    return base


def test_register_records_terms_agreed_at(client: TestClient):
    res = client.post("/auth/register", json=_full_payload())
    assert res.status_code == 201
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "consent@korea.ac.kr").first()
    assert user.terms_agreed_at is not None
    db.close()


def test_register_rejects_missing_consent(client: TestClient):
    res = client.post("/auth/register", json=_full_payload(agreed_terms=False))
    assert res.status_code == 400


def test_register_rejects_all_consent_false(client: TestClient):
    res = client.post("/auth/register", json=_full_payload(
        agreed_terms=False, agreed_privacy=False, agreed_age_14=False))
    assert res.status_code == 400
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_auth.py::test_register_records_terms_agreed_at tests/test_auth.py::test_register_rejects_missing_consent tests/test_auth.py::test_register_rejects_all_consent_false -v`
Expected: FAIL (모델에 `terms_agreed_at` 없음 / 스키마에 동의 필드 없어 무시됨 → 400 안 남)

- [ ] **Step 3: User 모델 컬럼 추가** — `backend/app/models/user.py`, `created_at` 정의 바로 뒤(35행 이후)에:

```python
    terms_agreed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

(`datetime`·`DateTime`은 이미 import됨 — 확인만)

- [ ] **Step 4: RegisterRequest 필드 추가** — `backend/app/schemas/auth.py`, `university: str` 아래에:

```python
    agreed_terms: bool
    agreed_privacy: bool
    agreed_age_14: bool
```

- [ ] **Step 5: register 검증 + 기록** — `backend/app/api/auth.py`

상단 import에 datetime 추가 (1행 근처):
```python
from datetime import datetime
```

`register` 함수에서 중복 이메일 체크 뒤, `user = User(...)` 앞에 동의 검증 삽입:
```python
    if not (payload.agreed_terms and payload.agreed_privacy and payload.agreed_age_14):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="필수 약관에 동의해야 가입할 수 있습니다",
        )
```

`User(...)` 생성에 `terms_agreed_at` 추가:
```python
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        university=payload.university,
        terms_agreed_at=datetime.utcnow(),
    )
```

- [ ] **Step 6: 신규 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: 신규 3개 PASS. **단, 기존 register 호출 테스트는 이제 422로 실패** (동의 필드 필수화 → 다음 단계에서 수정)

- [ ] **Step 7: 기존 register payload 전부 수정 (기계적)**

아래 8개 파일의 **모든** `/auth/register` json payload에 동의 3필드를 추가한다. 각 payload dict의 `"university": ...` 줄 뒤에:
```python
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
```
대상·개수: `conftest.py`(1), `test_auth.py`의 기존 6개, `test_verification.py`(6), `test_reports.py`(3), `test_withdraw.py`(1), `test_profile_photo.py`(1), `test_game.py`(1), `test_survey.py`(1), `test_me.py`(1). 헬퍼 함수(`_register_and_get_headers`, `_upload_as_student`, `_register_target` 등) 내부 payload도 포함.

- [ ] **Step 8: 전체 테스트 통과 확인**

Run: `cd backend && uv run pytest -v`
Expected: 전부 PASS (기존 + 신규 3개)

- [ ] **Step 9: 마이그레이션 생성·적용**

Run:
```bash
cd backend && uv run alembic revision --autogenerate -m "add terms_agreed_at to users" && uv run alembic upgrade head
```
Expected: `alembic/versions/`에 `terms_agreed_at` 컬럼 추가 마이그레이션 1개 생성. 생성 파일 열어 `op.add_column('users', ...terms_agreed_at...)`만 있고 무관한 변경(다른 테이블 drop 등) 없는지 확인.

- [ ] **Step 10: 커밋**

```bash
cd backend && git add app/models/user.py app/schemas/auth.py app/api/auth.py alembic/versions tests/
git commit -m "$(cat <<'EOF'
feat(backend): 가입 시 동의 3종 검증 + terms_agreed_at 기록

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 프론트 — 동의 체크박스 + 게이트 + 모달

**Files:**
- Modify: `frontend/src/lib/types.ts:24-29` (RegisterPayload)
- Create: `frontend/src/pages/Register/ConsentModal.tsx`
- Modify: `frontend/src/pages/Register/Register.tsx`
- Test: `frontend/src/pages/Register/Register.test.tsx` (신규)

**Interfaces:**
- Consumes: Task 1의 register API (`agreed_terms`, `agreed_privacy`, `agreed_age_14` 필수).
- Produces: `RegisterPayload`에 동의 3필드. `ConsentModal` 컴포넌트(`type`, `onClose` props).

- [ ] **Step 1: 실패 테스트 작성** — `frontend/src/pages/Register/Register.test.tsx`

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Register from "./Register";
import * as api from "../../lib/api";

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderRegister() {
  render(<MemoryRouter><Register /></MemoryRouter>);
}

function fillFields() {
  fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "a@b.com" } });
  fireEvent.change(screen.getByLabelText("비밀번호 (8자 이상)"), { target: { value: "password123" } });
  fireEvent.change(screen.getByLabelText("이름"), { target: { value: "김테스트" } });
  fireEvent.change(screen.getByLabelText("학교"), { target: { value: "서울대학교" } });
}

describe("Register 동의 게이트", () => {
  it("동의 전에는 가입 버튼 disabled", () => {
    renderRegister();
    expect(screen.getByRole("button", { name: "가입하기" })).toBeDisabled();
  });

  it("필수 3개 체크하면 버튼 활성", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText(/이용약관/));
    fireEvent.click(screen.getByLabelText(/개인정보처리방침/));
    fireEvent.click(screen.getByLabelText(/만 14세 이상/));
    expect(screen.getByRole("button", { name: "가입하기" })).toBeEnabled();
  });

  it("전체 동의 클릭하면 3개 일괄 체크", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    expect(screen.getByLabelText(/이용약관/)).toBeChecked();
    expect(screen.getByLabelText(/개인정보처리방침/)).toBeChecked();
    expect(screen.getByLabelText(/만 14세 이상/)).toBeChecked();
  });

  it("개별 하나 해제하면 전체 동의도 해제", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByLabelText(/이용약관/));
    expect(screen.getByLabelText("전체 동의")).not.toBeChecked();
  });

  it("제출 시 동의 필드 포함해 registerUser 호출", async () => {
    const spy = vi.spyOn(api, "registerUser").mockResolvedValue({} as never);
    renderRegister();
    fillFields();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByRole("button", { name: "가입하기" }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        agreed_terms: true, agreed_privacy: true, agreed_age_14: true,
      }),
    ));
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm run test -- Register.test`
Expected: FAIL (동의 UI 없음 — label 못 찾음, 버튼 항상 활성)

- [ ] **Step 3: RegisterPayload에 동의 필드** — `frontend/src/lib/types.ts`, `university: string;` 뒤:

```ts
  agreed_terms: boolean;
  agreed_privacy: boolean;
  agreed_age_14: boolean;
```

- [ ] **Step 4: ConsentModal 컴포넌트 생성** — `frontend/src/pages/Register/ConsentModal.tsx`

```tsx
type ConsentType = "terms" | "privacy";

const TITLES: Record<ConsentType, string> = {
  terms: "이용약관",
  privacy: "개인정보처리방침",
};

export function ConsentModal({ type, onClose }: { type: ConsentType; onClose: () => void }) {
  return (
    <div
      role="dialog"
      aria-label={TITLES[type]}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{ background: "#FFF5E6", borderRadius: 8, padding: 24, maxWidth: 340, maxHeight: "70vh", overflowY: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{TITLES[type]}</h2>
        <p>준비 중입니다 — 팀 문안 확정 후 교체 예정.</p>
        <button type="button" onClick={onClose}>닫기</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Register.tsx 동의 UI + 게이트 + payload** — `frontend/src/pages/Register/Register.tsx`

import 추가(상단):
```tsx
import { ConsentModal } from "./ConsentModal";
```

state 추가(`submitting` state 아래):
```tsx
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [agreedPrivacy, setAgreedPrivacy] = useState(false);
  const [agreedAge, setAgreedAge] = useState(false);
  const [modal, setModal] = useState<"terms" | "privacy" | null>(null);

  const allAgreed = agreedTerms && agreedPrivacy && agreedAge;

  function toggleAll() {
    const next = !allAgreed;
    setAgreedTerms(next);
    setAgreedPrivacy(next);
    setAgreedAge(next);
  }
```

`registerUser({...})` 호출에 동의 필드 추가:
```tsx
      await registerUser({
        email, password, name: name.trim(), university: university.trim(),
        agreed_terms: agreedTerms, agreed_privacy: agreedPrivacy, agreed_age_14: agreedAge,
      });
```

동의 블록을 `{error && ...}` 위에 삽입:
```tsx
        <fieldset className={styles.consent}>
          <label>
            <input type="checkbox" checked={allAgreed} onChange={toggleAll} />
            전체 동의
          </label>
          <div>
            <label>
              <input type="checkbox" checked={agreedTerms}
                onChange={(e) => setAgreedTerms(e.target.checked)} />
              이용약관 동의 (필수)
            </label>
            <button type="button" onClick={() => setModal("terms")}>보기</button>
          </div>
          <div>
            <label>
              <input type="checkbox" checked={agreedPrivacy}
                onChange={(e) => setAgreedPrivacy(e.target.checked)} />
              개인정보처리방침 동의 (필수)
            </label>
            <button type="button" onClick={() => setModal("privacy")}>보기</button>
          </div>
          <label>
            <input type="checkbox" checked={agreedAge}
              onChange={(e) => setAgreedAge(e.target.checked)} />
            만 14세 이상입니다 (필수)
          </label>
          <p className={styles.notice}>만 14세 미만은 가입할 수 없습니다</p>
        </fieldset>
```

가입 버튼 `disabled` 조건 수정:
```tsx
        <Button type="submit" disabled={submitting || !allAgreed}>
```

`</form>` 뒤(return 닫기 전)에 모달 렌더:
```tsx
      {modal && <ConsentModal type={modal} onClose={() => setModal(null)} />}
```

> 중요: 모달 트리거 `<button>`은 반드시 `<label>` **밖**에 둘 것. Testing Library는 label 텍스트 계산 시 중첩된 `<button>` 텍스트를 제거하므로, 트리거를 label 안에 넣으면 `getByLabelText(/이용약관/)`가 체크박스를 못 찾음. label엔 순수 텍스트("이용약관 동의 (필수)")만, 트리거는 형제 `<button>보기</button>`로 분리.

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd frontend && npm run test -- Register.test`
Expected: 5개 PASS

- [ ] **Step 7: 타입·빌드 확인**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 에러 없음

- [ ] **Step 8: 커밋**

```bash
cd frontend && git add src/lib/types.ts src/pages/Register/
git commit -m "$(cat <<'EOF'
feat(frontend): 가입 동의 체크박스 + 약관 모달 + 게이트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## 완료 후

- 두 Task 커밋 완료 후 `finishing-a-development-branch` 스킬로 PR 여부 결정. **git push/PR = 사용자 허락 필수.**
- 후속(비차단): 실제 약관/방침 문안 확정 시 ConsentModal placeholder 교체 + (필요 시) 약관 버전관리 마이그레이션.
