# 관리자 학생증 심사 UI 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자가 `/admin`에서 pending 학생증을 이름·대학과 대조하며 승인/반려하는 화면을 만든다.

**Architecture:** 백엔드는 admin 목록 응답에 심사용 신원정보(name·university)를 담는 전용 스키마를 추가한다. 프론트는 blob fetch로 인증 이미지를 로드하고, `ProtectedRoute`에 admin 게이트를 더한 뒤 Admin 페이지를 붙인다.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (백엔드), React + Vite + TypeScript + Vitest + Testing Library (프론트).

**Spec:** `docs/superpowers/specs/2026-07-13-admin-verification-review-design.md`

## Global Constraints

- 백엔드: 엔드포인트마다 Pydantic 스키마 사용, dict 반환 금지. 입력≠응답 스키마 분리. `require_admin`(core.deps) 게이트. (`backend/CLAUDE.md`)
- 프론트: API URL은 `VITE_API_URL`만. 색상은 크림 `#FFF5E6`·코랄 `#FF7F5C`·오렌지 `#FF9472`만, 임의 색상 금지. max-width 390px 모바일 우선. 페이지 단위 폴더(`src/pages/`). (`frontend/CLAUDE.md`)
- 본인용 `VerificationOut`(`GET /me/verification`)은 절대 변경하지 않는다 — 신원정보 최소노출.
- 커밋 형식: `<prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- TDD: 실패 테스트 → 최소 구현 → 통과 → 커밋.

## File Structure

| 파일 | 책임 | 작업 |
|------|------|------|
| `backend/app/schemas/verification.py` | `AdminVerificationOut` 추가 | Modify |
| `backend/app/api/verification.py` | 목록 엔드포인트 응답 확장 | Modify |
| `backend/tests/test_verification.py` | 목록 name·university 테스트 | Modify |
| `frontend/src/lib/types.ts` | `AdminVerificationOut` 타입 | Modify |
| `frontend/src/lib/api.ts` | 3개 API 함수 | Modify |
| `frontend/src/lib/api.verification.test.ts` | API 함수 테스트 | Modify |
| `frontend/src/components/ProtectedRoute.tsx` | `requireAdmin` 게이트 | Modify |
| `frontend/src/components/ProtectedRoute.test.tsx` | 게이트 테스트 | Create |
| `frontend/src/App.tsx` | `/admin` 라우트 | Modify |
| `frontend/src/pages/Admin/Admin.tsx` | 심사 페이지 | Create |
| `frontend/src/pages/Admin/Admin.module.css` | 페이지 스타일 | Create |
| `frontend/src/pages/Admin/Admin.test.tsx` | 페이지 테스트 | Create |

---

## Task 1: 백엔드 — AdminVerificationOut 스키마 + 목록 엔드포인트 확장

**Files:**
- Modify: `backend/app/schemas/verification.py`
- Modify: `backend/app/api/verification.py:77-86`
- Test: `backend/tests/test_verification.py`

**Interfaces:**
- Consumes: `StudentVerification.user` relationship (models/verification.py:35), `User.name`·`User.university`.
- Produces: `AdminVerificationOut(id, user_id, status, reviewed_at, created_at, name, university)`. `GET /admin/verifications` → `list[AdminVerificationOut]`.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_verification.py`의 기존 `test_admin_list_verifications` 아래에 추가:

```python
def test_admin_list_includes_name_and_university(admin_client: TestClient):
    admin_client.post("/auth/register", json={
        "email": "namestudent@test.com",
        "password": "password123",
        "name": "김학생",
        "university": "연세대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "namestudent@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    response = admin_client.get("/admin/verifications")
    assert response.status_code == 200
    entry = next(e for e in response.json() if e["name"] == "김학생")
    assert entry["university"] == "연세대학교"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_verification.py::test_admin_list_includes_name_and_university -v`
Expected: FAIL — `KeyError: 'name'` (응답에 name 없음).

- [ ] **Step 3: 스키마 추가**

`backend/app/schemas/verification.py`의 `VerificationOut` 클래스 아래에 추가:

```python
class AdminVerificationOut(BaseModel):
    id: int
    user_id: int
    status: VerificationStatus
    reviewed_at: datetime | None
    created_at: datetime
    name: str
    university: str
```

- [ ] **Step 4: 목록 엔드포인트 수정**

`backend/app/api/verification.py` 상단 import에 `AdminVerificationOut` 추가:

```python
from app.schemas.verification import (
    AdminVerificationOut,
    VerificationAction,
    VerificationOut,
)
```

`list_pending_verifications`(77-86행)를 교체:

```python
@router.get("/admin/verifications", response_model=list[AdminVerificationOut])
def list_pending_verifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    verifications = (
        db.query(StudentVerification)
        .filter(StudentVerification.status == VerificationStatus.pending)
        .all()
    )
    return [
        AdminVerificationOut(
            id=v.id,
            user_id=v.user_id,
            status=v.status,
            reviewed_at=v.reviewed_at,
            created_at=v.created_at,
            name=v.user.name,
            university=v.user.university,
        )
        for v in verifications
    ]
```

- [ ] **Step 5: 테스트 통과 확인 (회귀 포함)**

Run: `cd backend && uv run pytest tests/test_verification.py -v`
Expected: PASS — 신규 테스트 + 기존 verification 테스트 전부 통과.

- [ ] **Step 6: 전체 백엔드 회귀 확인**

Run: `cd backend && uv run pytest -v`
Expected: PASS — 기존 78 + 신규 1 = 79 전부 통과.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/schemas/verification.py backend/app/api/verification.py backend/tests/test_verification.py
git commit -m "$(cat <<'EOF'
feat(backend): 관리자 학생증 목록에 name·university 포함 (AdminVerificationOut)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 프론트 — 타입 + API 함수 3개

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.verification.test.ts`

**Interfaces:**
- Consumes: `apiFetch`, `getToken`, `clearToken`, `ApiError`, `BASE` (api.ts 내부).
- Produces:
  - `AdminVerificationOut` 타입 (types.ts).
  - `listPendingVerifications(): Promise<AdminVerificationOut[]>`
  - `reviewVerification(id: number, action: "approve"|"reject"): Promise<AdminVerificationOut>`
  - `fetchVerificationImage(id: number): Promise<string>` (objectURL 반환).

- [ ] **Step 1: 타입 추가**

`frontend/src/lib/types.ts` 끝(`VerificationOut` 아래)에 추가:

```ts
export interface AdminVerificationOut {
  id: number;
  user_id: number;
  status: VerificationStatus;
  reviewed_at: string | null;
  created_at: string;
  name: string;
  university: string;
}
```

- [ ] **Step 2: 실패 테스트 작성**

`frontend/src/lib/api.verification.test.ts` 상단 import에 신규 함수 추가하고, `describe` 블록 안에 테스트 추가:

```ts
import {
  getMyVerification,
  uploadVerification,
  listPendingVerifications,
  reviewVerification,
  fetchVerificationImage,
} from "./api";
```

```ts
  it("listPendingVerifications는 /admin/verifications GET", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 1, user_id: 2, status: "pending", reviewed_at: null,
            created_at: "2026-07-06", name: "김학생", university: "연세대학교" },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const result = await listPendingVerifications();
    expect(result[0].name).toBe("김학생");
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/verifications"),
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("reviewVerification은 action 본문으로 POST", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ id: 1, user_id: 2, status: "approved", reviewed_at: null,
          created_at: "2026-07-06", name: "김학생", university: "연세대학교" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const result = await reviewVerification(1, "approve");
    expect(result.status).toBe("approved");
    const opts = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body as string)).toEqual({ action: "approve" });
  });

  it("fetchVerificationImage는 blob을 objectURL로 변환", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(new Blob([new Uint8Array([1, 2, 3])]), { status: 200 }),
    );
    const createSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:mock-url");
    const url = await fetchVerificationImage(7);
    expect(url).toBe("blob:mock-url");
    expect(createSpy).toHaveBeenCalledOnce();
  });

  it("fetchVerificationImage는 실패 시 ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 404 }));
    await expect(fetchVerificationImage(9)).rejects.toBeInstanceOf(ApiError);
  });
```

`ApiError`를 import에 추가:
```ts
import { /* ...기존... */, ApiError } from "./api";
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd frontend && npm run test -- api.verification`
Expected: FAIL — `listPendingVerifications is not a function` 등.

- [ ] **Step 4: API 함수 구현**

`frontend/src/lib/api.ts` 상단 타입 import에 `AdminVerificationOut` 추가:

```ts
import type {
  // ...기존...
  VerificationOut,
  AdminVerificationOut,
} from "./types";
```

파일 끝(`uploadVerification` 아래)에 추가:

```ts
export function listPendingVerifications(): Promise<AdminVerificationOut[]> {
  return apiFetch<AdminVerificationOut[]>("/admin/verifications", { method: "GET" });
}

export function reviewVerification(
  id: number,
  action: "approve" | "reject",
): Promise<AdminVerificationOut> {
  return apiFetch<AdminVerificationOut>(`/admin/verifications/${id}`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export async function fetchVerificationImage(id: number): Promise<string> {
  const token = getToken();
  const res = await fetch(`${BASE}/admin/verifications/${id}/image`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 401) clearToken();
  if (!res.ok) throw new ApiError(res.status, "이미지를 불러오지 못했습니다");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npm run test -- api.verification`
Expected: PASS — 신규 4개 + 기존 2개 통과.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/api.verification.test.ts
git commit -m "$(cat <<'EOF'
feat(frontend): 관리자 심사 API 함수 3개 + AdminVerificationOut 타입

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 프론트 — ProtectedRoute admin 게이트 + /admin 라우트

**Files:**
- Modify: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/ProtectedRoute.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useAuth()` → `{ user, loading }`, `user.is_admin: boolean`, `user.status`.
- Produces: `ProtectedRoute`에 `requireAdmin?: boolean` prop. `/admin` 라우트가 `Admin` 페이지(Task 4)를 렌더.

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/components/ProtectedRoute.test.tsx` 생성:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import * as auth from "../lib/auth";

const baseUser = {
  id: 1, email: "a@b.com", name: "테스터", university: "서울대학교",
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-07-06",
};

function renderAt(user: typeof baseUser | null) {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    user, loading: false,
    login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn(),
  });
  return render(
    <MemoryRouter initialEntries={["/admin"]}>
      <Routes>
        <Route path="/home" element={<p>홈</p>} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <p>관리자 화면</p>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute requireAdmin", () => {
  it("admin이면 통과", () => {
    renderAt({ ...baseUser, is_admin: true });
    expect(screen.getByText("관리자 화면")).toBeInTheDocument();
  });

  it("비admin active는 /home으로 redirect", () => {
    renderAt({ ...baseUser, is_admin: false });
    expect(screen.getByText("홈")).toBeInTheDocument();
    expect(screen.queryByText("관리자 화면")).toBeNull();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- ProtectedRoute`
Expected: FAIL — `requireAdmin`이 무시돼 비admin도 "관리자 화면"이 뜸.

- [ ] **Step 3: ProtectedRoute 수정**

`frontend/src/components/ProtectedRoute.tsx`를 교체:

```tsx
import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/auth";

interface Props {
  children: ReactNode;
  requireStatus?: "pending" | "active";
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireStatus, requireAdmin }: Props) {
  const { user, loading } = useAuth();

  if (loading) return <p>불러오는 중...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.status === "suspended") return <Navigate to="/login" replace />;

  if (requireAdmin && !user.is_admin) {
    return <Navigate to={user.status === "active" ? "/home" : "/pending"} replace />;
  }

  // 요구 status와 다르면 본인 status의 목적지로 보정
  if (requireStatus && user.status !== requireStatus) {
    return <Navigate to={user.status === "active" ? "/home" : "/pending"} replace />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test -- ProtectedRoute`
Expected: PASS — 2개 통과.

- [ ] **Step 5: App.tsx에 /admin 라우트 추가**

`frontend/src/App.tsx` import에 추가:

```tsx
import Admin from "./pages/Admin/Admin";
```

`</Route>`(MainLayout 닫힘) 뒤, `/profile` 라우트 옆에 추가:

```tsx
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireAdmin>
            <Admin />
          </ProtectedRoute>
        }
      />
```

> 주의: 이 단계는 Task 4의 `Admin` 컴포넌트가 있어야 빌드된다. Task 4까지 마친 뒤 빌드 검증한다. 지금은 커밋만.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/ProtectedRoute.tsx frontend/src/components/ProtectedRoute.test.tsx frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): ProtectedRoute requireAdmin 게이트 + /admin 라우트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 프론트 — Admin 심사 페이지

**Files:**
- Create: `frontend/src/pages/Admin/Admin.tsx`
- Create: `frontend/src/pages/Admin/Admin.module.css`
- Test: `frontend/src/pages/Admin/Admin.test.tsx`

**Interfaces:**
- Consumes: `listPendingVerifications`, `reviewVerification`, `fetchVerificationImage` (Task 2), `AdminVerificationOut` 타입, `Button` 컴포넌트.
- Produces: default export `Admin` (App.tsx가 렌더).

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/pages/Admin/Admin.test.tsx` 생성:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Admin from "./Admin";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

const entry = {
  id: 5, user_id: 2, status: "pending" as const,
  reviewed_at: null, created_at: "2026-07-06",
  name: "김학생", university: "연세대학교",
};

describe("Admin", () => {
  it("목록 로드 후 이름·대학 표시", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    render(<Admin />);
    await waitFor(() => expect(screen.getByText("김학생")).toBeInTheDocument());
    expect(screen.getByText(/연세대학교/)).toBeInTheDocument();
  });

  it("빈 목록이면 안내 문구", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
    render(<Admin />);
    await waitFor(() => expect(screen.getByText("심사 대기 없음")).toBeInTheDocument());
  });

  it("로드 실패면 에러 표시", async () => {
    vi.spyOn(api, "listPendingVerifications").mockRejectedValue(new Error("fail"));
    render(<Admin />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });

  it("학생증 보기 클릭 → 이미지 로드", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "fetchVerificationImage").mockResolvedValue("blob:mock-url");
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "학생증 보기" }));
    await waitFor(() =>
      expect(screen.getByAltText("김학생 학생증")).toHaveAttribute("src", "blob:mock-url"),
    );
    expect(api.fetchVerificationImage).toHaveBeenCalledWith(5);
  });

  it("승인 클릭 → reviewVerification 호출 후 카드 제거", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "reviewVerification").mockResolvedValue({ ...entry, status: "approved" });
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "승인" }));
    await waitFor(() => expect(screen.queryByText("김학생")).toBeNull());
    expect(api.reviewVerification).toHaveBeenCalledWith(5, "approve");
  });

  it("반려 클릭 → reject 액션", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "reviewVerification").mockResolvedValue({ ...entry, status: "rejected" });
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "반려" }));
    await waitFor(() => expect(api.reviewVerification).toHaveBeenCalledWith(5, "reject"));
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- Admin`
Expected: FAIL — `Admin.tsx` 모듈 없음(import 에러).

- [ ] **Step 3: 스타일 생성**

`frontend/src/pages/Admin/Admin.module.css` 생성:

```css
.wrap {
  max-width: 390px;
  margin: 0 auto;
  padding: 24px 16px;
  background: #FFF5E6;
  min-height: 100vh;
}
.title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}
.card {
  border: 1px solid #FF9472;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}
.name {
  font-size: 16px;
  font-weight: 700;
}
.university {
  color: #FF7F5C;
  margin: 4px 0 12px;
}
.image {
  max-width: 100%;
  border-radius: 6px;
  margin: 8px 0;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.error {
  color: #FF7F5C;
}
```

- [ ] **Step 4: Admin 컴포넌트 구현**

`frontend/src/pages/Admin/Admin.tsx` 생성:

```tsx
import { useEffect, useState } from "react";
import {
  listPendingVerifications,
  reviewVerification,
  fetchVerificationImage,
} from "../../lib/api";
import type { AdminVerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

function Card({
  item,
  onReviewed,
}: {
  item: AdminVerificationOut;
  onReviewed: (id: number) => void;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);

  async function showImage() {
    setImageError("");
    try {
      const url = await fetchVerificationImage(item.id);
      setImageUrl(url);
    } catch {
      setImageError("이미지를 불러오지 못했어요.");
    }
  }

  async function review(action: "approve" | "reject") {
    setBusy(true);
    try {
      await reviewVerification(item.id, action);
      onReviewed(item.id);
    } catch {
      setImageError("처리에 실패했어요. 다시 시도해주세요.");
      setBusy(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.name}>{item.name}</div>
      <div className={styles.university}>{item.university}</div>
      {imageUrl ? (
        <img className={styles.image} src={imageUrl} alt={`${item.name} 학생증`} />
      ) : (
        <Button onClick={showImage}>학생증 보기</Button>
      )}
      {imageError && <p className={styles.error}>{imageError}</p>}
      <div className={styles.actions}>
        <Button onClick={() => review("approve")} disabled={busy}>
          승인
        </Button>
        <Button onClick={() => review("reject")} disabled={busy}>
          반려
        </Button>
      </div>
    </div>
  );
}

export default function Admin() {
  const [items, setItems] = useState<AdminVerificationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listPendingVerifications()
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

  function removeItem(id: number) {
    setItems((prev) => prev.filter((v) => v.id !== id));
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>학생증 심사</h1>
      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>심사 대기 없음</p>}
      {items.map((item) => (
        <Card key={item.id} item={item} onReviewed={removeItem} />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npm run test -- Admin`
Expected: PASS — 6개 통과.

- [ ] **Step 6: 전체 프론트 회귀 + 빌드 확인**

Run: `cd frontend && npm run test`
Expected: PASS — 기존 41 + 신규(api 4 + ProtectedRoute 2 + Admin 6 = 12) 통과.

Run: `cd frontend && npm run build`
Expected: 빌드 성공 (Task 3의 `/admin` 라우트가 이제 `Admin`을 정상 참조).

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/pages/Admin/
git commit -m "$(cat <<'EOF'
feat(frontend): 관리자 학생증 심사 페이지 (클릭 이미지 로드·승인/반려)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## 최종 검증

- [ ] `cd backend && uv run pytest -v` — 79 pass.
- [ ] `cd frontend && npm run test` — 전부 pass.
- [ ] `cd frontend && npm run build` — 성공.
- [ ] 수동: admin 계정으로 `/admin` 접근 → pending 카드에 이름·대학 표시, "학생증 보기" 시 이미지, 승인/반려 시 카드 제거 확인.
- [ ] 수동: 비admin 계정으로 `/admin` 접근 → `/home` redirect 확인.

## 범위 밖 (YAGNI)
- approved/rejected 이력 화면.
- admin 진입 네비 링크(숨김 경로 유지).
- 매칭 알고리즘.
