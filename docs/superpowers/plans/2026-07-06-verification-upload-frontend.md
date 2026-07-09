# 학생증 인증 업로드 프론트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 가입 후 pending 유저가 `/pending` 화면에서 학생증을 올리고 심사 상태(안올림/심사중/반려)를 확인하며, 승인 시 홈으로 이동한다.

**Architecture:** 백엔드에 본인 인증 상태 조회 `GET /me/verification`(없으면 null) 1개 추가. 프론트는 타입 2개 + api 함수 2개 추가, 재사용 업로드 폼 컴포넌트(파일선택·미리보기·클라검증) 신설, 기존 `Pending` 화면을 마운트 조회 기반 상태기계로 개조.

**Tech Stack:** 백엔드 FastAPI + SQLAlchemy + pytest. 프론트 React + Vite + vitest + @testing-library/react.

## Global Constraints

- 백엔드 스키마 규칙: 엔드포인트마다 Pydantic 스키마, dict 반환 금지. 인증 = `get_current_user` (core.deps).
- 파일 규칙(백엔드 기존): content-type ∈ {image/jpeg, image/png, image/webp}, 용량 ≤ 10MB(=`10 * 1024 * 1024`).
- 프론트 API URL = `VITE_API_URL` 환경변수 (하드코딩 금지). 색상 = 디자인토큰(코랄 `#FF7F5C`) + 승인된 중립색(에러 `#d33`, 안내 `#666`)만.
- 프론트 파일 업로드는 `FormData` 사용 — `apiFetch`가 body=FormData면 Content-Type 자동 생략(검증 완료). 선례: `uploadProfilePhoto`.
- 반응형 max-width 390px 모바일 우선.
- 커밋 형식: `<prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- 스코프 밖: 관리자 심사 UI, `image_url` 서버경로 노출 개선, 폴링(마운트 1회 조회만).

---

### Task 1: 백엔드 `GET /me/verification`

**Files:**
- Modify: `backend/app/api/me.py` (import 추가 + 엔드포인트 추가)
- Test: `backend/tests/test_verification.py` (테스트 3개 추가)

**Interfaces:**
- Produces: `GET /me/verification` → 200 `VerificationOut | None`. 인증 필요. 본인 레코드 없으면 `null`.
- Consumes: 기존 `StudentVerification` 모델(이미 me.py에 import됨), `VerificationOut` 스키마(`app.schemas.verification`).

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_verification.py` 파일 끝에 추가 (파일 상단에 `import io`, `_register_and_get_headers` 헬퍼 이미 존재):

```python
def test_get_my_verification_none(client):
    headers = _register_and_get_headers(client, "noverif@test.com")
    res = client.get("/me/verification", headers=headers)
    assert res.status_code == 200
    assert res.json() is None


def test_get_my_verification_after_upload(client):
    headers = _register_and_get_headers(client, "hasverif@test.com")
    client.post(
        "/verification/upload",
        files={"file": ("s.jpg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    )
    res = client.get("/me/verification", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_get_my_verification_unauthenticated(client):
    res = client.get("/me/verification")
    assert res.status_code == 401
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/test_verification.py -v`
Expected: FAIL — 3개 신규 테스트 404/오류 (엔드포인트 없음)

- [ ] **Step 3: 최소 구현** — `backend/app/api/me.py` 상단 import 블록에 `VerificationOut` 추가:

```python
from app.schemas.verification import VerificationOut
```

그리고 기존 `get_survey` 엔드포인트 위/아래 아무 곳(라우터 정의부)에 추가:

```python
@router.get("/verification", response_model=VerificationOut | None)
def get_my_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(StudentVerification)
        .filter(StudentVerification.user_id == current_user.id)
        .first()
    )
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/test_verification.py -v`
Expected: PASS — 전체(기존 + 신규 3개)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/me.py backend/tests/test_verification.py
git commit -m "feat(backend): 본인 학생증 인증 상태 조회 GET /me/verification

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: 프론트 타입 + api 함수

**Files:**
- Modify: `frontend/src/lib/types.ts` (타입 2개 추가)
- Modify: `frontend/src/lib/api.ts` (함수 2개 추가, import 갱신)
- Test: `frontend/src/lib/api.verification.test.ts` (신규)

**Interfaces:**
- Produces:
  - `type VerificationStatus = "pending" | "approved" | "rejected"`
  - `interface VerificationOut { id, user_id, image_url, status, reviewed_at, created_at }`
  - `getMyVerification(): Promise<VerificationOut | null>` → GET `/me/verification`
  - `uploadVerification(file: File): Promise<VerificationOut>` → POST `/verification/upload` (FormData)
- Consumes: 기존 `apiFetch`, `ApiError`(api.ts에서 export됨).

- [ ] **Step 1: 실패 테스트 작성** — `frontend/src/lib/api.verification.test.ts` 신규:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { getMyVerification, uploadVerification } from "./api";

beforeEach(() => vi.restoreAllMocks());

describe("verification api", () => {
  it("getMyVerification은 /me/verification GET, null 본문 그대로 반환", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("null", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    const result = await getMyVerification();
    expect(result).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/me/verification"),
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("uploadVerification은 FormData로 POST", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 1, user_id: 1, image_url: "x", status: "pending",
          reviewed_at: null, created_at: "2026-07-06",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    const file = new File(["x"], "id.jpg", { type: "image/jpeg" });
    const result = await uploadVerification(file);
    expect(result.status).toBe("pending");
    const opts = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(opts.body).toBeInstanceOf(FormData);
    expect(opts.method).toBe("POST");
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm run test -- api.verification`
Expected: FAIL — `getMyVerification`/`uploadVerification` export 없음

- [ ] **Step 3: 최소 구현**

`frontend/src/lib/types.ts` 파일 끝에 추가:

```ts
export type VerificationStatus = "pending" | "approved" | "rejected";

export interface VerificationOut {
  id: number;
  user_id: number;
  image_url: string;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
}
```

`frontend/src/lib/api.ts` — 상단 타입 import 목록에 `VerificationOut` 추가(기존 `import type { ... } from "./types"` 라인에 병합). 그리고 파일 내 다른 export 함수들 근처에 추가:

```ts
export function getMyVerification(): Promise<VerificationOut | null> {
  return apiFetch<VerificationOut | null>("/me/verification", { method: "GET" });
}

export function uploadVerification(file: File): Promise<VerificationOut> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<VerificationOut>("/verification/upload", {
    method: "POST",
    body: form,
  });
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm run test -- api.verification`
Expected: PASS (2개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/api.verification.test.ts
git commit -m "feat(frontend): verification 타입 + api 함수 (조회·업로드)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 업로드 폼 컴포넌트 (UploadForm)

**Files:**
- Create: `frontend/src/pages/Pending/UploadForm.tsx`
- Modify: `frontend/src/pages/Pending/Pending.module.css` (`.form` `.preview` `.error` 추가)
- Test: `frontend/src/pages/Pending/UploadForm.test.tsx` (신규)

**Interfaces:**
- Produces: `UploadForm` 기본 export. Props `{ onUploaded: (v: VerificationOut) => void }`. 파일 선택 시 클라 검증(타입/용량) + 미리보기, 제출 시 `uploadVerification` 호출 후 성공하면 `onUploaded(v)`.
- Consumes: `uploadVerification`, `ApiError`(api.ts), `VerificationOut`(types), 기존 `Button` 컴포넌트.

- [ ] **Step 1: 실패 테스트 작성** — `frontend/src/pages/Pending/UploadForm.test.tsx` 신규:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UploadForm from "./UploadForm";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:mock");
});

function makeFile(type: string, size = 100): File {
  const file = new File(["x"], "id", { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function selectFile(file: File) {
  fireEvent.change(screen.getByLabelText("학생증 파일"), { target: { files: [file] } });
}

const okVerif = {
  id: 1, user_id: 1, image_url: "x", status: "pending" as const,
  reviewed_at: null, created_at: "2026-07-06",
};

describe("UploadForm", () => {
  it("잘못된 타입은 에러 + 제출 안 감", () => {
    const spy = vi.spyOn(api, "uploadVerification");
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("application/pdf"));
    expect(screen.getByText("JPG, PNG, WEBP 파일만 올릴 수 있어요")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    expect(spy).not.toHaveBeenCalled();
  });

  it("10MB 초과 거부", () => {
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("image/jpeg", 11 * 1024 * 1024));
    expect(screen.getByText("파일 크기는 10MB 이하여야 해요")).toBeInTheDocument();
  });

  it("유효 파일 제출 → onUploaded 호출", async () => {
    const onUploaded = vi.fn();
    vi.spyOn(api, "uploadVerification").mockResolvedValue(okVerif);
    render(<UploadForm onUploaded={onUploaded} />);
    selectFile(makeFile("image/jpeg"));
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(okVerif));
  });

  it("백엔드 에러 메시지 표시", async () => {
    vi.spyOn(api, "uploadVerification").mockRejectedValue(
      new api.ApiError(400, "파일 크기는 10MB 이하여야 합니다"),
    );
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("image/jpeg"));
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    await waitFor(() =>
      expect(screen.getByText("파일 크기는 10MB 이하여야 합니다")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm run test -- UploadForm`
Expected: FAIL — `UploadForm` 모듈 없음

- [ ] **Step 3: 최소 구현** — `frontend/src/pages/Pending/UploadForm.tsx`:

```tsx
import { useState } from "react";
import { uploadVerification, ApiError } from "../../lib/api";
import type { VerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Pending.module.css";

const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 10 * 1024 * 1024;

export default function UploadForm({
  onUploaded,
}: {
  onUploaded: (v: VerificationOut) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleSelect(e: React.ChangeEvent<HTMLInputElement>) {
    setError("");
    const f = e.target.files?.[0];
    if (!f) return;
    if (!ALLOWED.includes(f.type)) {
      setError("JPG, PNG, WEBP 파일만 올릴 수 있어요");
      setFile(null);
      setPreview(null);
      return;
    }
    if (f.size > MAX_SIZE) {
      setError("파일 크기는 10MB 이하여야 해요");
      setFile(null);
      setPreview(null);
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleSubmit() {
    if (!file) {
      setError("파일을 선택해주세요");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const v = await uploadVerification(file);
      onUploaded(v);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "업로드에 실패했어요");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.form}>
      <input
        aria-label="학생증 파일"
        type="file"
        accept="image/*"
        onChange={handleSelect}
      />
      {preview && <img className={styles.preview} src={preview} alt="미리보기" />}
      {error && <p className={styles.error}>{error}</p>}
      <Button onClick={handleSubmit} disabled={submitting}>
        {submitting ? "제출 중…" : "제출"}
      </Button>
    </div>
  );
}
```

`frontend/src/pages/Pending/Pending.module.css` 끝에 추가:

```css
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  align-items: center;
}

.preview {
  max-width: 100%;
  border-radius: 8px;
}

.error {
  color: #d33;
  font-size: 14px;
  margin: 0;
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm run test -- UploadForm`
Expected: PASS (4개)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/pages/Pending/UploadForm.tsx frontend/src/pages/Pending/UploadForm.test.tsx frontend/src/pages/Pending/Pending.module.css
git commit -m "feat(frontend): 학생증 업로드 폼 (미리보기·클라검증·에러표시)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Pending 화면 상태기계 개조

**Files:**
- Modify: `frontend/src/pages/Pending/Pending.tsx` (전면 개조)
- Test: `frontend/src/pages/Pending/Pending.test.tsx` (신규)

**Interfaces:**
- Consumes: `fetchMe`(status 확인), `getMyVerification`, `UploadForm`(Task 3), 기존 `useAuth().logout`, `useNavigate`.
- 동작: 마운트 시 `fetchMe`+`getMyVerification` 병렬 조회 → active면 `/home` 이동, 아니면 verification 상태별 안내 + 업로드 폼(항상 노출: 심사중에도 재업로드 허용). 업로드 성공 시 verification state 갱신.

- [ ] **Step 1: 실패 테스트 작성** — `frontend/src/pages/Pending/Pending.test.tsx` 신규:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Pending from "./Pending";
import * as api from "../../lib/api";

const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => navigate,
}));
vi.mock("../../lib/auth", () => ({ useAuth: () => ({ logout: vi.fn() }) }));

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:mock");
});

const baseUser = {
  id: 1, email: "a@b.com", name: "테스터", university: "서울대학교",
  status: "pending" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-07-06",
};
const verifBase = {
  id: 1, user_id: 1, image_url: "x",
  reviewed_at: null, created_at: "2026-07-06",
};

function mock(userStatus: "pending" | "active", verif: unknown) {
  vi.spyOn(api, "fetchMe").mockResolvedValue({ ...baseUser, status: userStatus });
  vi.spyOn(api, "getMyVerification").mockResolvedValue(verif as never);
}

describe("Pending", () => {
  it("verification 없으면 업로드 안내 + 폼", async () => {
    mock("pending", null);
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/학생증을 올려/)).toBeInTheDocument());
    expect(screen.getByLabelText("학생증 파일")).toBeInTheDocument();
  });

  it("pending이면 검토 중 표시", async () => {
    mock("pending", { ...verifBase, status: "pending" });
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/검토 중/)).toBeInTheDocument());
  });

  it("rejected면 반려 안내", async () => {
    mock("pending", { ...verifBase, status: "rejected" });
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/반려/)).toBeInTheDocument());
  });

  it("active면 홈으로 이동", async () => {
    mock("active", null);
    render(<Pending />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/home"));
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npm run test -- Pending`
Expected: FAIL — 기존 Pending은 상태 조회/분기 없음

- [ ] **Step 3: 최소 구현** — `frontend/src/pages/Pending/Pending.tsx` 전면 교체:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { fetchMe, getMyVerification } from "../../lib/api";
import type { VerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import UploadForm from "./UploadForm";
import styles from "./Pending.module.css";

function messageFor(v: VerificationOut | null): string {
  if (v === null) return "학생증을 올려 인증을 완료해주세요.";
  if (v.status === "rejected") return "인증이 반려됐어요. 학생증을 다시 올려주세요.";
  return "학생증 인증이 검토 중입니다. 승인되면 매칭에 참여할 수 있어요.";
}

export default function Pending() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [verification, setVerification] = useState<VerificationOut | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      const [me, verif] = await Promise.all([fetchMe(), getMyVerification()]);
      if (!active) return;
      if (me.status === "active") {
        navigate("/home");
        return;
      }
      setVerification(verif);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [navigate]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <p className={styles.desc}>확인 중…</p>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>승인 대기 중</h1>
      <p className={styles.desc}>{messageFor(verification)}</p>
      <UploadForm onUploaded={(v) => setVerification(v)} />
      <Button onClick={handleLogout}>로그아웃</Button>
    </div>
  );
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend && npm run test -- Pending`
Expected: PASS (4개)

- [ ] **Step 5: 전체 프론트 테스트 + 빌드 확인**

Run: `cd frontend && npm run test && npm run build`
Expected: 전체 테스트 PASS, build clean

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/pages/Pending/Pending.tsx frontend/src/pages/Pending/Pending.test.tsx
git commit -m "feat(frontend): Pending 화면 상태기계 (조회·업로드폼·승인시 홈이동)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 최종 검증

- 백엔드: `cd backend && uv run pytest tests/test_verification.py -v` 전체 PASS
- 프론트: `cd frontend && npm run test` 전체 PASS + `npm run build` clean
- 수동: 가입 → `/pending`에서 파일 올림 → "검토 중" 표시 → (관리자 approve 시뮬레이션) → 재방문 시 `/home` 이동
