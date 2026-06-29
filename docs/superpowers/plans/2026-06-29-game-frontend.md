# Game 프론트엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** active 유저용 game 화면(오작교·붉은실 2탭)과 화면 도달용 상단 고정 네비게이션을 구현한다.

**Architecture:** 공용 레이아웃 래퍼(`MainLayout` + `TopNav`)가 `/home`·`/game`·`/mypage`를 감싸 상단 네비를 1곳에서 관리한다. `/game`은 단일 라우트 안에서 컴포넌트 state로 2탭(오작교/붉은실)을 전환한다. API 호출은 기존 `apiFetch`/`ApiError` 패턴을 따른다.

**Tech Stack:** React 18 + Vite + TypeScript, react-router-dom, vitest + @testing-library/react.

## Global Constraints

- API URL은 `import.meta.env.VITE_API_URL` 사용. 하드코딩 금지.
- 대학 입력은 자유 텍스트(드롭다운 금지 — CLAUDE.md 미결 항목).
- 디자인 토큰만 사용: 크림 `#FFF5E6`, 코랄 `#FF7F5C`, 오렌지 `#FF9472`. 임의 색상 금지.
- 페이지/컴포넌트는 폴더 단위 (`src/pages/<Name>/` 또는 `src/components/<Name>/`), `.tsx` + `.module.css`.
- 에러 메시지는 `ApiError.message`(백엔드 detail이 담김)를 그대로 표시. 추가 매핑 없음.
- 테스트 실행: `cd frontend && npm run test`. 타입체크/빌드: `cd frontend && npm run build`.
- 선행 조건: game 백엔드(`feat/game-endpoints`)가 `main`에 병합된 뒤 구현 시작 (이 계획은 그 전에 작성 가능).

---

### Task 1: game 타입 + API 함수

**Files:**
- Modify: `frontend/src/lib/types.ts` (끝에 추가)
- Modify: `frontend/src/lib/api.ts` (끝에 추가)

**Interfaces:**
- Consumes: 기존 `apiFetch<T>` (api.ts).
- Produces:
  - 타입: `OjakgyoOut`, `OjakgyoCreate`, `RedThreadTarget`, `RedThreadOut`, `RedThreadReceived`
  - 함수: `postOjakgyo(payload: OjakgyoCreate): Promise<OjakgyoOut>`, `postRedThread(targets: RedThreadTarget[]): Promise<RedThreadOut>`, `getRedThread(): Promise<RedThreadOut>`, `getRedThreadReceived(): Promise<RedThreadReceived>`

> 참고: API 함수는 `apiFetch`를 감싸는 얇은 래퍼다. 기존 api.ts 함수들(`registerUser` 등)도 단위 테스트가 없으므로 이 Task는 TDD 대신 `npm run build`(tsc) 타입체크로 검증한다.

- [ ] **Step 1: 타입 추가**

`frontend/src/lib/types.ts` 끝에 추가:

```ts
export interface OjakgyoCreate {
  person_a_name: string;
  person_a_university: string;
  person_b_name: string;
  person_b_university: string;
}

export interface OjakgyoOut extends OjakgyoCreate {
  id: number;
  recommender_id: number;
  created_at: string;
}

export interface RedThreadTarget {
  target_name: string;
  target_university: string;
}

export interface RedThreadOut {
  targets: RedThreadTarget[];
}

export interface RedThreadReceived {
  count: number;
}
```

- [ ] **Step 2: API 함수 추가**

`frontend/src/lib/api.ts` 맨 위 import에 타입 추가하고(기존 `import type { TokenResponse, UserOut, RegisterPayload } from "./types";` 를 아래로 교체):

```ts
import type {
  TokenResponse,
  UserOut,
  RegisterPayload,
  OjakgyoCreate,
  OjakgyoOut,
  RedThreadTarget,
  RedThreadOut,
  RedThreadReceived,
} from "./types";
```

파일 끝에 함수 추가:

```ts
export function postOjakgyo(payload: OjakgyoCreate): Promise<OjakgyoOut> {
  return apiFetch<OjakgyoOut>("/game/ojakgyo", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postRedThread(targets: RedThreadTarget[]): Promise<RedThreadOut> {
  return apiFetch<RedThreadOut>("/game/red-thread", {
    method: "POST",
    body: JSON.stringify({ targets }),
  });
}

export function getRedThread(): Promise<RedThreadOut> {
  return apiFetch<RedThreadOut>("/game/red-thread", { method: "GET" });
}

export function getRedThreadReceived(): Promise<RedThreadReceived> {
  return apiFetch<RedThreadReceived>("/game/red-thread/received", { method: "GET" });
}
```

- [ ] **Step 3: 타입체크 통과 확인**

Run: `cd frontend && npm run build`
Expected: tsc 에러 없이 빌드 성공.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): game API 타입·함수 추가 (오작교·붉은실)"
```

---

### Task 2: 상단 네비게이션 + 레이아웃 래퍼

**Files:**
- Create: `frontend/src/components/TopNav/TopNav.tsx`
- Create: `frontend/src/components/TopNav/TopNav.module.css`
- Create: `frontend/src/components/TopNav/TopNav.test.tsx`
- Create: `frontend/src/components/MainLayout/MainLayout.tsx`
- Create: `frontend/src/components/MainLayout/MainLayout.module.css`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: react-router-dom `NavLink`, `Outlet`.
- Produces: `TopNav` (default export), `MainLayout` (default export). `/home`·`/game`·`/mypage`가 `MainLayout` 자식 라우트로 묶임.

- [ ] **Step 1: TopNav 실패 테스트 작성**

`frontend/src/components/TopNav/TopNav.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TopNav from "./TopNav";

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <TopNav />
    </MemoryRouter>,
  );
}

describe("TopNav", () => {
  it("3개 링크 렌더", () => {
    renderAt("/home");
    expect(screen.getByRole("link", { name: "홈" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "게임" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "마이페이지" })).toBeInTheDocument();
  });

  it("현재 경로 링크에 active 표시 (aria-current)", () => {
    renderAt("/game");
    expect(screen.getByRole("link", { name: "게임" })).toHaveAttribute("aria-current", "page");
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- TopNav`
Expected: FAIL — `Cannot find module './TopNav'`.

- [ ] **Step 3: TopNav 구현**

`frontend/src/components/TopNav/TopNav.tsx`:

```tsx
import { NavLink } from "react-router-dom";
import styles from "./TopNav.module.css";

const links = [
  { to: "/home", label: "홈" },
  { to: "/game", label: "게임" },
  { to: "/mypage", label: "마이페이지" },
];

export default function TopNav() {
  return (
    <nav className={styles.nav}>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            isActive ? `${styles.link} ${styles.active}` : styles.link
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
```

`frontend/src/components/TopNav/TopNav.module.css`:

```css
.nav {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 390px;
  display: flex;
  justify-content: space-around;
  background: #fff5e6;
  border-bottom: 1px solid #ff9472;
  padding: 12px 0;
  z-index: 10;
}

.link {
  color: #999;
  text-decoration: none;
  font-weight: 600;
}

.active {
  color: #ff7f5c;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test -- TopNav`
Expected: PASS (2 tests).

- [ ] **Step 5: MainLayout 구현**

`frontend/src/components/MainLayout/MainLayout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import TopNav from "../TopNav/TopNav";
import styles from "./MainLayout.module.css";

export default function MainLayout() {
  return (
    <>
      <TopNav />
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  );
}
```

`frontend/src/components/MainLayout/MainLayout.module.css`:

```css
.main {
  max-width: 390px;
  margin: 0 auto;
  padding-top: 60px;
}
```

- [ ] **Step 6: App.tsx에 래퍼 라우트 적용**

`frontend/src/App.tsx`를 아래로 교체 (import에 `MainLayout`, `Game` 추가 — Game은 Task 5에서 생성하므로 이 Step에서는 `/game`을 아직 넣지 않는다. `/home`·`/mypage`만 래퍼로 묶는다):

```tsx
import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing/Landing";
import Register from "./pages/Register/Register";
import Login from "./pages/Login/Login";
import Pending from "./pages/Pending/Pending";
import Home from "./pages/Home/Home";
import MyPage from "./pages/MyPage/MyPage";
import Profile from "./pages/Profile/Profile";
import MainLayout from "./components/MainLayout/MainLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/pending"
        element={
          <ProtectedRoute requireStatus="pending">
            <Pending />
          </ProtectedRoute>
        }
      />
      <Route element={<MainLayout />}>
        <Route
          path="/home"
          element={
            <ProtectedRoute requireStatus="active">
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/mypage"
          element={
            <ProtectedRoute>
              <MyPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

- [ ] **Step 7: 빌드 + 전체 테스트 통과 확인**

Run: `cd frontend && npm run build && npm run test`
Expected: 빌드 성공, 모든 테스트 PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/TopNav frontend/src/components/MainLayout frontend/src/App.tsx
git commit -m "feat(frontend): 상단 네비 + MainLayout 래퍼 (/home·/mypage 적용)"
```

---

### Task 3: 오작교 탭

**Files:**
- Create: `frontend/src/pages/Game/OjakgyoTab.tsx`
- Create: `frontend/src/pages/Game/Game.module.css` (오작교·붉은실·탭 공용 스타일)
- Create: `frontend/src/pages/Game/OjakgyoTab.test.tsx`

**Interfaces:**
- Consumes: `postOjakgyo`, `ApiError` (api.ts), `Input`, `Button` 컴포넌트.
- Produces: `OjakgyoTab` (default export, props 없음).

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/pages/Game/OjakgyoTab.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OjakgyoTab from "./OjakgyoTab";
import * as api from "../../lib/api";
import { ApiError } from "../../lib/api";

beforeEach(() => vi.clearAllMocks());

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("OjakgyoTab", () => {
  it("두 사람이 같으면 제출 막고 에러 표시", async () => {
    const spy = vi.spyOn(api, "postOjakgyo");
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "김철수");
    fill("사람2 학교", "서울대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("두 사람이 같아요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("성공 시 완료 메시지 표시 + 폼 리셋", async () => {
    vi.spyOn(api, "postOjakgyo").mockResolvedValue({
      id: 1, recommender_id: 1,
      person_a_name: "김철수", person_a_university: "서울대학교",
      person_b_name: "이영희", person_b_university: "연세대학교",
      created_at: "2026-01-01",
    });
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "이영희");
    fill("사람2 학교", "연세대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("중매 완료!")).toBeInTheDocument(),
    );
    expect((screen.getByLabelText("사람1 이름") as HTMLInputElement).value).toBe("");
  });

  it("백엔드 에러 detail 표시", async () => {
    vi.spyOn(api, "postOjakgyo").mockRejectedValue(
      new ApiError(409, "이미 지목한 쌍입니다"),
    );
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "이영희");
    fill("사람2 학교", "연세대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("이미 지목한 쌍입니다")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- OjakgyoTab`
Expected: FAIL — `Cannot find module './OjakgyoTab'`.

- [ ] **Step 3: 구현**

`frontend/src/pages/Game/OjakgyoTab.tsx`:

```tsx
import { useState, type FormEvent } from "react";
import { postOjakgyo, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Game.module.css";

export default function OjakgyoTab() {
  const [aName, setAName] = useState("");
  const [aUniv, setAUniv] = useState("");
  const [bName, setBName] = useState("");
  const [bUniv, setBUniv] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setAName(""); setAUniv(""); setBName(""); setBUniv("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    const a = [aName.trim(), aUniv.trim()];
    const b = [bName.trim(), bUniv.trim()];
    if (a[0] === b[0] && a[1] === b[1]) {
      setError("두 사람이 같아요");
      return;
    }
    setSubmitting(true);
    try {
      await postOjakgyo({
        person_a_name: aName,
        person_a_university: aUniv,
        person_b_name: bName,
        person_b_university: bUniv,
      });
      setMessage("중매 완료!");
      reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "중매에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <p className={styles.hint}>마음이 잘 맞을 것 같은 두 사람을 이어주세요.</p>
      <Input id="a-name" label="사람1 이름" value={aName}
        onChange={(e) => setAName(e.target.value)} />
      <Input id="a-univ" label="사람1 학교" value={aUniv}
        onChange={(e) => setAUniv(e.target.value)} />
      <Input id="b-name" label="사람2 이름" value={bName}
        onChange={(e) => setBName(e.target.value)} />
      <Input id="b-univ" label="사람2 학교" value={bUniv}
        onChange={(e) => setBUniv(e.target.value)} />
      {error && <p className={styles.error}>{error}</p>}
      {message && <p className={styles.success}>{message}</p>}
      <Button type="submit" disabled={submitting}>
        {submitting ? "처리 중..." : "중매하기"}
      </Button>
    </form>
  );
}
```

`frontend/src/pages/Game/Game.module.css`:

```css
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  color: #999;
  font-weight: 600;
  cursor: pointer;
}

.tabActive {
  color: #ff7f5c;
  border-bottom-color: #ff7f5c;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hint {
  color: #666;
  font-size: 14px;
}

.error {
  color: #d33;
  font-size: 14px;
}

.success {
  color: #ff7f5c;
  font-size: 14px;
  font-weight: 600;
}

.received {
  color: #666;
  font-size: 14px;
  margin-bottom: 12px;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test -- OjakgyoTab`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Game/OjakgyoTab.tsx frontend/src/pages/Game/OjakgyoTab.test.tsx frontend/src/pages/Game/Game.module.css
git commit -m "feat(frontend): 오작교 탭 (중매 폼·자체검증·에러표시)"
```

---

### Task 4: 붉은실 탭

**Files:**
- Create: `frontend/src/pages/Game/RedThreadTab.tsx`
- Create: `frontend/src/pages/Game/RedThreadTab.test.tsx`
- (Game.module.css는 Task 3에서 생성됨 — 재사용)

**Interfaces:**
- Consumes: `getRedThread`, `getRedThreadReceived`, `postRedThread`, `ApiError` (api.ts), `Input`, `Button`.
- Produces: `RedThreadTab` (default export, props 없음).

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/pages/Game/RedThreadTab.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RedThreadTab from "./RedThreadTab";
import * as api from "../../lib/api";
import { ApiError } from "../../lib/api";

beforeEach(() => vi.clearAllMocks());

function mockLoad(targets: { target_name: string; target_university: string }[], count: number) {
  vi.spyOn(api, "getRedThread").mockResolvedValue({ targets });
  vi.spyOn(api, "getRedThreadReceived").mockResolvedValue({ count });
}

describe("RedThreadTab", () => {
  it("마운트 시 기존 지목 prefill + 받은 인원수 표시", async () => {
    mockLoad([{ target_name: "이영희", target_university: "연세대학교" }], 3);
    render(<RedThreadTab />);
    await waitFor(() =>
      expect((screen.getByLabelText("상대1 이름") as HTMLInputElement).value).toBe("이영희"),
    );
    expect(screen.getByText("나를 3명이 지목했어요")).toBeInTheDocument();
  });

  it("받은 인원 0명이면 안내 문구", async () => {
    mockLoad([], 0);
    render(<RedThreadTab />);
    await waitFor(() =>
      expect(screen.getByText("아직 나를 지목한 사람이 없어요")).toBeInTheDocument(),
    );
  });

  it("두 슬롯이 같으면 제출 막고 에러", async () => {
    mockLoad([], 0);
    const spy = vi.spyOn(api, "postRedThread");
    render(<RedThreadTab />);
    await waitFor(() => screen.getByLabelText("상대1 이름"));
    fireEvent.change(screen.getByLabelText("상대1 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대1 학교"), { target: { value: "연세대학교" } });
    fireEvent.change(screen.getByLabelText("상대2 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대2 학교"), { target: { value: "연세대학교" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("같은 사람을 두 번 넣을 수 없어요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("저장 성공 시 메시지 표시", async () => {
    mockLoad([], 0);
    vi.spyOn(api, "postRedThread").mockResolvedValue({
      targets: [{ target_name: "이영희", target_university: "연세대학교" }],
    });
    render(<RedThreadTab />);
    await waitFor(() => screen.getByLabelText("상대1 이름"));
    fireEvent.change(screen.getByLabelText("상대1 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대1 학교"), { target: { value: "연세대학교" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("저장됐어요")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- RedThreadTab`
Expected: FAIL — `Cannot find module './RedThreadTab'`.

- [ ] **Step 3: 구현**

`frontend/src/pages/Game/RedThreadTab.tsx`:

```tsx
import { useState, useEffect, type FormEvent } from "react";
import {
  getRedThread,
  getRedThreadReceived,
  postRedThread,
  ApiError,
} from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Game.module.css";

export default function RedThreadTab() {
  const [name1, setName1] = useState("");
  const [univ1, setUniv1] = useState("");
  const [name2, setName2] = useState("");
  const [univ2, setUniv2] = useState("");
  const [received, setReceived] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([getRedThread(), getRedThreadReceived()])
      .then(([thread, recv]) => {
        const [t1, t2] = thread.targets;
        if (t1) { setName1(t1.target_name); setUniv1(t1.target_university); }
        if (t2) { setName2(t2.target_name); setUniv2(t2.target_university); }
        setReceived(recv.count);
      })
      .catch(() => {
        /* 초기 로드 실패 시 빈 폼 유지 */
      });
  }, []);

  function buildTargets() {
    const out: { target_name: string; target_university: string }[] = [];
    if (name1.trim() && univ1.trim()) {
      out.push({ target_name: name1.trim(), target_university: univ1.trim() });
    }
    if (name2.trim() && univ2.trim()) {
      out.push({ target_name: name2.trim(), target_university: univ2.trim() });
    }
    return out;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    const targets = buildTargets();
    if (
      targets.length === 2 &&
      targets[0].target_name === targets[1].target_name &&
      targets[0].target_university === targets[1].target_university
    ) {
      setError("같은 사람을 두 번 넣을 수 없어요");
      return;
    }
    setSubmitting(true);
    try {
      const result = await postRedThread(targets);
      const [t1, t2] = result.targets;
      setName1(t1?.target_name ?? "");
      setUniv1(t1?.target_university ?? "");
      setName2(t2?.target_name ?? "");
      setUniv2(t2?.target_university ?? "");
      setMessage("저장됐어요");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = buildTargets().length >= 1;

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <p className={styles.received}>
        {received > 0 ? `나를 ${received}명이 지목했어요` : "아직 나를 지목한 사람이 없어요"}
      </p>
      <p className={styles.hint}>마음에 둔 상대를 최대 2명까지 적어주세요. (최소 1명)</p>
      <Input id="rt-name1" label="상대1 이름" value={name1}
        onChange={(e) => setName1(e.target.value)} />
      <Input id="rt-univ1" label="상대1 학교" value={univ1}
        onChange={(e) => setUniv1(e.target.value)} />
      <Input id="rt-name2" label="상대2 이름" value={name2}
        onChange={(e) => setName2(e.target.value)} />
      <Input id="rt-univ2" label="상대2 학교" value={univ2}
        onChange={(e) => setUniv2(e.target.value)} />
      {error && <p className={styles.error}>{error}</p>}
      {message && <p className={styles.success}>{message}</p>}
      <Button type="submit" disabled={submitting || !canSubmit}>
        {submitting ? "저장 중..." : "저장"}
      </Button>
    </form>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test -- RedThreadTab`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Game/RedThreadTab.tsx frontend/src/pages/Game/RedThreadTab.test.tsx
git commit -m "feat(frontend): 붉은실 탭 (prefill·받은인원·덮어쓰기·자체검증)"
```

---

### Task 5: Game 페이지 셸 (탭 전환) + 라우트 연결

**Files:**
- Create: `frontend/src/pages/Game/Game.tsx`
- Create: `frontend/src/pages/Game/Game.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `OjakgyoTab`, `RedThreadTab` (Task 3·4), `MainLayout`·`ProtectedRoute`.
- Produces: `Game` (default export). `/game` 라우트가 `MainLayout` 그룹 안에 추가됨.

- [ ] **Step 1: 실패 테스트 작성**

`frontend/src/pages/Game/Game.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Game from "./Game";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  // 붉은실 탭 마운트 시 호출되는 로드 API stub
  vi.spyOn(api, "getRedThread").mockResolvedValue({ targets: [] });
  vi.spyOn(api, "getRedThreadReceived").mockResolvedValue({ count: 0 });
});

describe("Game", () => {
  it("기본은 오작교 탭 노출", () => {
    render(<Game />);
    expect(screen.getByRole("button", { name: "중매하기" })).toBeInTheDocument();
  });

  it("붉은실 탭 클릭 시 붉은실 화면으로 전환", async () => {
    render(<Game />);
    fireEvent.click(screen.getByRole("button", { name: "붉은실" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "저장" })).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npm run test -- Game.test`
Expected: FAIL — `Cannot find module './Game'`.

- [ ] **Step 3: Game 셸 구현**

`frontend/src/pages/Game/Game.tsx`:

```tsx
import { useState } from "react";
import OjakgyoTab from "./OjakgyoTab";
import RedThreadTab from "./RedThreadTab";
import styles from "./Game.module.css";

type Tab = "ojakgyo" | "redthread";

export default function Game() {
  const [tab, setTab] = useState<Tab>("ojakgyo");

  return (
    <div>
      <div className={styles.tabs}>
        <button
          type="button"
          className={tab === "ojakgyo" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("ojakgyo")}
        >
          오작교
        </button>
        <button
          type="button"
          className={tab === "redthread" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("redthread")}
        >
          붉은실
        </button>
      </div>
      {tab === "ojakgyo" ? <OjakgyoTab /> : <RedThreadTab />}
    </div>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test -- Game.test`
Expected: PASS (2 tests).

- [ ] **Step 5: App.tsx에 /game 라우트 추가**

`frontend/src/App.tsx` 상단 import에 추가:

```tsx
import Game from "./pages/Game/Game";
```

`MainLayout` 그룹 안 `/home` 라우트 아래에 추가:

```tsx
        <Route
          path="/game"
          element={
            <ProtectedRoute requireStatus="active">
              <Game />
            </ProtectedRoute>
          }
        />
```

- [ ] **Step 6: 빌드 + 전체 테스트 통과 확인**

Run: `cd frontend && npm run build && npm run test`
Expected: 빌드 성공, 전체 테스트 PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Game/Game.tsx frontend/src/pages/Game/Game.test.tsx frontend/src/App.tsx
git commit -m "feat(frontend): game 페이지 탭 셸 + /game 라우트 연결"
```

---

## 완료 기준

- `/home`·`/game`·`/mypage`에서 상단 네비 노출, 현재 탭 코랄 하이라이트.
- `/game`에서 오작교/붉은실 탭 전환 동작.
- 오작교: 4필드 입력 → 중매 제출 → 성공 메시지·폼 리셋, A==B 선차단, 백엔드 에러 표시.
- 붉은실: 마운트 prefill + 받은 인원수, 최대 2명 덮어쓰기 저장, 슬롯 중복 선차단.
- `cd frontend && npm run build && npm run test` 전부 통과.
