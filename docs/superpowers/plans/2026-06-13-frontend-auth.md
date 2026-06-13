# 프론트엔드 인증 플로우 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 빈 `frontend/`에 Vite+React+TS 프로젝트를 세우고 백엔드 auth와 연동되는 인증 플로우 4화면(랜딩/회원가입/로그인/인증대기)을 구현한다.

**Architecture:** SPA. react-router-dom 라우팅, AuthContext가 토큰/유저 상태 보유, `lib/api.ts` fetch 래퍼가 VITE_API_URL 베이스 + Bearer 자동첨부 + 에러파싱 담당. 순수 로직(api/auth/라우팅헬퍼)은 vitest 유닛테스트, UI는 수동 확인.

**Tech Stack:** React 18, TypeScript, Vite 5, react-router-dom 6, CSS Modules, vitest 2 + @testing-library/react + jsdom.

**Spec:** `docs/superpowers/specs/2026-06-13-frontend-auth-design.md`

---

## 파일 구조

```
frontend/
  package.json          # 의존성 + 스크립트
  tsconfig.json         # TS 설정 (앱)
  tsconfig.node.json    # TS 설정 (vite config용)
  vite.config.ts        # Vite + vitest 설정
  index.html            # 진입 HTML
  .env.example          # VITE_API_URL 템플릿 (커밋)
  .env                  # 로컬 전용 (gitignore, 커밋금지)
  src/
    main.tsx            # ReactDOM 렌더 + Router + AuthProvider
    App.tsx             # 라우트 정의
    vite-env.d.ts       # import.meta.env 타입
    test/setup.ts       # jest-dom matcher 등록
    styles/
      tokens.css        # 디자인토큰 CSS변수
      global.css        # reset + 모바일 컨테이너
    lib/
      types.ts          # API 타입 (UserOut, TokenResponse...)
      api.ts            # fetch 래퍼 + auth API 함수 + 토큰 storage
      routing.ts        # destinationFor(status) 헬퍼
      auth.tsx          # AuthContext / AuthProvider / useAuth
    components/
      Button/Button.tsx + Button.module.css
      Input/Input.tsx + Input.module.css
      ProtectedRoute.tsx
    pages/
      Landing/Landing.tsx + Landing.module.css
      Register/Register.tsx + Register.module.css
      Login/Login.tsx + Login.module.css
      Pending/Pending.tsx + Pending.module.css
      Home/Home.tsx      # placeholder (라우트보호 검증용)
  tests/
    api.test.ts
    auth.test.tsx
    routing.test.ts
```

---

## Task 1: 프로젝트 스캐폴드 + 디자인 토큰

빈 디렉토리(.gitkeep, CLAUDE.md만 있음)에 Vite 프로젝트를 수동 구성한다. `npm create vite`는 기존 파일과 충돌하므로 파일을 직접 만든다.

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/.env.example`, `frontend/.env`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/vite-env.d.ts`, `frontend/src/test/setup.ts`, `frontend/src/styles/tokens.css`, `frontend/src/styles/global.css`

- [ ] **Step 1: package.json 작성**

`frontend/package.json`:
```json
{
  "name": "datedrop-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.6",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^24.1.1",
    "typescript": "^5.5.3",
    "vite": "^5.4.1",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: tsconfig 작성**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "tests"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: vite.config.ts 작성** (vitest 설정 포함)

`frontend/vite.config.ts`:
```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
```

- [ ] **Step 4: index.html + env + 타입선언 작성**

`frontend/index.html`:
```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DateDrop Korea</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/.env.example`:
```
VITE_API_URL=http://localhost:8000
```

`frontend/.env` (로컬 전용 — 루트 .gitignore가 이미 무시):
```
VITE_API_URL=http://localhost:8000
```

`frontend/src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 5: 디자인 토큰 + 글로벌 CSS 작성**

`frontend/src/styles/tokens.css`:
```css
:root {
  --color-bg: #FFF5E6;
  --color-primary: #FF7F5C;
  --color-secondary: #FF9472;
  --color-text: #2B2B2B;
  --color-error: #D64545;
  --container-max: 390px;
  --radius: 8px;
  --space: 16px;
}
```

`frontend/src/styles/global.css`:
```css
@import "./tokens.css";

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5;
}

#root {
  max-width: var(--container-max);
  margin: 0 auto;
  min-height: 100vh;
  padding: var(--space);
}

a { color: var(--color-primary); }
```

- [ ] **Step 6: main.tsx + 임시 App.tsx 작성**

`frontend/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

`frontend/src/App.tsx` (임시 — Task 8에서 라우트 채움):
```tsx
export default function App() {
  return <h1>DateDrop Korea</h1>;
}
```

- [ ] **Step 7: 설치 + 부팅 확인**

Run: `cd frontend; npm install`
Expected: 의존성 설치 성공, 에러 없음.

Run: `cd frontend; npm run build`
Expected: tsc + vite build 성공, `dist/` 생성.

- [ ] **Step 8: 보안체크 후 커밋**

`.env`가 추적되지 않는지 확인:
Run: `git status --short frontend/`
Expected: `frontend/.env`는 목록에 없음 (gitignore됨). `frontend/.env.example`은 있음.

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/.env.example frontend/src
git commit -m "feat(frontend): Vite+React+TS 스캐폴드 + 디자인 토큰"
```

> `package-lock.json`도 함께 add (`git add frontend/package-lock.json`).

---

## Task 2: API 타입 + fetch 래퍼 (TDD)

**Files:**
- Create: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`
- Test: `frontend/tests/api.test.ts`

- [ ] **Step 1: 타입 정의 작성**

`frontend/src/lib/types.ts`:
```ts
export type UserStatus = "pending" | "active" | "suspended";

export interface UserOut {
  id: number;
  email: string;
  name: string;
  university: string;
  status: UserStatus;
  profile_photo: string | null;
  bio: string | null;
  instagram: string | null;
  kakao_id: string | null;
  phone: string | null;
  matching_paused: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  university: string;
}
```

- [ ] **Step 2: 실패 테스트 작성**

`frontend/tests/api.test.ts`:
```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, ApiError, getToken, setToken, clearToken } from "../src/lib/api";

describe("token storage", () => {
  beforeEach(() => localStorage.clear());

  it("set/get/clear 토큰", () => {
    expect(getToken()).toBeNull();
    setToken("abc");
    expect(getToken()).toBe("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  function mockFetch(status: number, body: unknown) {
    return vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }

  it("토큰 있으면 Authorization 헤더 첨부", async () => {
    setToken("tok123");
    const spy = mockFetch(200, { ok: true });
    await apiFetch("/me");
    const init = spy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok123");
  });

  it("성공 시 JSON 반환", async () => {
    mockFetch(200, { id: 1 });
    const data = await apiFetch<{ id: number }>("/me");
    expect(data.id).toBe(1);
  });

  it("non-2xx 시 detail 문자열로 ApiError throw", async () => {
    mockFetch(409, { detail: "이미 사용 중인 이메일입니다" });
    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      status: 409,
      message: "이미 사용 중인 이메일입니다",
    });
  });

  it("422 detail 배열이면 첫 msg 추출", async () => {
    mockFetch(422, { detail: [{ msg: "비밀번호는 8자 이상이어야 합니다", loc: ["body", "password"] }] });
    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      message: "비밀번호는 8자 이상이어야 합니다",
    });
  });

  it("401 시 토큰 삭제", async () => {
    setToken("tok");
    mockFetch(401, { detail: "unauthorized" });
    await expect(apiFetch("/me")).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
  });
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd frontend; npx vitest run tests/api.test.ts`
Expected: FAIL — `api.ts` 모듈 없음.

- [ ] **Step 4: api.ts 구현**

`frontend/src/lib/api.ts`:
```ts
import type { TokenResponse, UserOut, RegisterPayload } from "./types";

const BASE = import.meta.env.VITE_API_URL;
const TOKEN_KEY = "datedrop_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function parseDetail(body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length && typeof detail[0]?.msg === "string") {
    return detail[0].msg;
  }
  return "요청 처리 중 오류가 발생했습니다";
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "서버 연결에 실패했습니다");
  }

  if (res.status === 401) clearToken();

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* 본문 없음 */
    }
    throw new ApiError(res.status, parseDetail(body));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function registerUser(payload: RegisterPayload): Promise<UserOut> {
  return apiFetch<UserOut>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginRequest(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchMe(): Promise<UserOut> {
  return apiFetch<UserOut>("/me", { method: "GET" });
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend; npx vitest run tests/api.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/tests/api.test.ts
git commit -m "feat(frontend): API 타입 + fetch 래퍼 (Bearer 첨부·에러파싱·401 토큰삭제)"
```

---

## Task 3: 라우팅 헬퍼 + AuthContext (TDD)

**Files:**
- Create: `frontend/src/lib/routing.ts`, `frontend/src/lib/auth.tsx`
- Test: `frontend/tests/routing.test.ts`, `frontend/tests/auth.test.tsx`

- [ ] **Step 1: 라우팅 헬퍼 실패 테스트**

`frontend/tests/routing.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { destinationFor } from "../src/lib/routing";

describe("destinationFor", () => {
  it("active → /home", () => {
    expect(destinationFor("active")).toBe("/home");
  });
  it("pending → /pending", () => {
    expect(destinationFor("pending")).toBe("/pending");
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend; npx vitest run tests/routing.test.ts`
Expected: FAIL — `routing.ts` 없음.

- [ ] **Step 3: routing.ts 구현**

`frontend/src/lib/routing.ts`:
```ts
import type { UserStatus } from "./types";

// suspended는 호출측에서 별도 차단 처리 (이동 경로 없음)
export function destinationFor(status: UserStatus): string {
  return status === "active" ? "/home" : "/pending";
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd frontend; npx vitest run tests/routing.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: AuthContext 실패 테스트**

`frontend/tests/auth.test.tsx`:
```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "../src/lib/auth";
import * as api from "../src/lib/api";
import type { UserOut } from "../src/lib/types";

const fakeUser: UserOut = {
  id: 1, email: "a@b.com", name: "홍길동", university: "테스트대",
  status: "active", profile_photo: null, bio: null, instagram: null,
  kakao_id: null, phone: null, matching_paused: false, is_admin: false,
  created_at: "2026-06-13T00:00:00",
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useAuth", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("토큰 없으면 loading 끝나고 user null", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
  });

  it("login 시 토큰 저장 + user 설정", async () => {
    vi.spyOn(api, "loginRequest").mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.spyOn(api, "fetchMe").mockResolvedValue(fakeUser);
    const setSpy = vi.spyOn(api, "setToken");

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let returned: UserOut | undefined;
    await act(async () => {
      returned = await result.current.login("a@b.com", "password12");
    });

    expect(setSpy).toHaveBeenCalledWith("tok");
    expect(result.current.user).toEqual(fakeUser);
    expect(returned).toEqual(fakeUser);
  });

  it("logout 시 토큰삭제 + user null", async () => {
    vi.spyOn(api, "loginRequest").mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.spyOn(api, "fetchMe").mockResolvedValue(fakeUser);
    const clearSpy = vi.spyOn(api, "clearToken");

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.login("a@b.com", "password12"); });

    act(() => result.current.logout());
    expect(clearSpy).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });
});
```

- [ ] **Step 6: 실패 확인**

Run: `cd frontend; npx vitest run tests/auth.test.tsx`
Expected: FAIL — `auth.tsx` 없음.

- [ ] **Step 7: auth.tsx 구현**

`frontend/src/lib/auth.tsx`:
```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { UserOut } from "./types";
import { loginRequest, fetchMe, setToken, clearToken, getToken } from "./api";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserOut>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string): Promise<UserOut> {
    const { access_token } = await loginRequest(email, password);
    setToken(access_token);
    const me = await fetchMe();
    setUser(me);
    return me;
  }

  function logout(): void {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 8: 통과 확인**

Run: `cd frontend; npx vitest run tests/auth.test.tsx tests/routing.test.ts`
Expected: PASS (routing 2 + auth 3 = 5 tests).

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/lib/routing.ts frontend/src/lib/auth.tsx frontend/tests/routing.test.ts frontend/tests/auth.test.tsx
git commit -m "feat(frontend): AuthContext + status 라우팅 헬퍼"
```

---

## Task 4: 공용 컴포넌트 (Button, Input)

UI 컴포넌트 — 유닛테스트 없이 작성, 다음 페이지 태스크에서 실사용으로 검증.

**Files:**
- Create: `frontend/src/components/Button/Button.tsx`, `frontend/src/components/Button/Button.module.css`, `frontend/src/components/Input/Input.tsx`, `frontend/src/components/Input/Input.module.css`

- [ ] **Step 1: Button 작성**

`frontend/src/components/Button/Button.tsx`:
```tsx
import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`${styles.button} ${className ?? ""}`} {...props} />;
}
```

`frontend/src/components/Button/Button.module.css`:
```css
.button {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: var(--radius);
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.button:disabled {
  background: var(--color-secondary);
  opacity: 0.6;
  cursor: not-allowed;
}
```

- [ ] **Step 2: Input 작성**

`frontend/src/components/Input/Input.tsx`:
```tsx
import type { InputHTMLAttributes } from "react";
import styles from "./Input.module.css";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, id, ...props }: Props) {
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <input id={id} className={styles.input} {...props} />
    </div>
  );
}
```

`frontend/src/components/Input/Input.module.css`:
```css
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: var(--space);
}

.label {
  font-size: 14px;
  font-weight: 600;
}

.input {
  padding: 12px;
  border: 1px solid var(--color-secondary);
  border-radius: var(--radius);
  font-size: 16px;
}

.input:focus {
  outline: 2px solid var(--color-primary);
}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd frontend; npm run build`
Expected: 빌드 성공 (컴포넌트 미사용 경고는 없음 — export만 됨).

> 참고: `noUnusedLocals`는 export된 컴포넌트엔 영향 없음. 빌드 통과해야 함.

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/components/Button frontend/src/components/Input
git commit -m "feat(frontend): 공용 Button·Input 컴포넌트 (디자인토큰 적용)"
```

---

## Task 5: 랜딩 페이지

**Files:**
- Create: `frontend/src/pages/Landing/Landing.tsx`, `frontend/src/pages/Landing/Landing.module.css`

- [ ] **Step 1: Landing 작성**

`frontend/src/pages/Landing/Landing.tsx`:
```tsx
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/Button/Button";
import styles from "./Landing.module.css";

export default function Landing() {
  const navigate = useNavigate();
  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>DateDrop</h1>
      <p className={styles.subtitle}>한국 대학생 주간 소개팅 매칭</p>
      <div className={styles.actions}>
        <Button onClick={() => navigate("/register")}>회원가입</Button>
        <button className={styles.linkBtn} onClick={() => navigate("/login")}>
          이미 계정이 있어요
        </button>
      </div>
    </div>
  );
}
```

`frontend/src/pages/Landing/Landing.module.css`:
```css
.wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  text-align: center;
}

.title {
  font-size: 48px;
  color: var(--color-primary);
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  margin-bottom: 48px;
}

.actions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.linkBtn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 14px;
  cursor: pointer;
  text-decoration: underline;
}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend; npm run build`
Expected: 빌드 성공.

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/Landing
git commit -m "feat(frontend): 랜딩 페이지"
```

---

## Task 6: 회원가입 페이지

가입 성공 시 자동로그인 안 함 → `/login`으로 이동 (state로 가입완료 안내 전달).

**Files:**
- Create: `frontend/src/pages/Register/Register.tsx`, `frontend/src/pages/Register/Register.module.css`

- [ ] **Step 1: Register 작성**

`frontend/src/pages/Register/Register.tsx`:
```tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Register.module.css";

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [university, setUniversity] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function validate(): string {
    if (!email.includes("@")) return "올바른 이메일을 입력하세요";
    if (password.length < 8) return "비밀번호는 8자 이상이어야 합니다";
    if (!name.trim()) return "이름을 입력하세요";
    if (!university.trim()) return "학교를 입력하세요";
    return "";
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const v = validate();
    if (v) { setError(v); return; }
    setError("");
    setSubmitting(true);
    try {
      await registerUser({ email, password, name: name.trim(), university: university.trim() });
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "가입에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>회원가입</h1>
      <form onSubmit={handleSubmit}>
        <Input id="email" label="이메일" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Input id="password" label="비밀번호 (8자 이상)" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        <Input id="name" label="이름" value={name}
          onChange={(e) => setName(e.target.value)} />
        <Input id="university" label="학교" value={university}
          onChange={(e) => setUniversity(e.target.value)} />
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "처리 중..." : "가입하기"}
        </Button>
      </form>
    </div>
  );
}
```

`frontend/src/pages/Register/Register.module.css`:
```css
.wrap { padding-top: 24px; }

.title {
  font-size: 28px;
  margin-bottom: 24px;
  color: var(--color-primary);
}

.error {
  color: var(--color-error);
  font-size: 14px;
  margin-bottom: var(--space);
}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend; npm run build`
Expected: 빌드 성공.

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/Register
git commit -m "feat(frontend): 회원가입 페이지 (제출검증·중복이메일 처리)"
```

---

## Task 7: 로그인 페이지

`login()` 성공 후 status 분기. suspended는 별도 차단 메시지 + logout.

**Files:**
- Create: `frontend/src/pages/Login/Login.tsx`, `frontend/src/pages/Login/Login.module.css`

- [ ] **Step 1: Login 작성**

`frontend/src/pages/Login/Login.tsx`:
```tsx
import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { destinationFor } from "../../lib/routing";
import { ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Login.module.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, logout } = useAuth();
  const registered = (location.state as { registered?: boolean } | null)?.registered;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login(email, password);
      if (user.status === "suspended") {
        logout();
        setError("이용이 정지된 계정입니다. 운영팀에 문의하세요.");
        return;
      }
      navigate(destinationFor(user.status));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>로그인</h1>
      {registered && <p className={styles.notice}>가입이 완료되었습니다. 로그인하세요.</p>}
      <form onSubmit={handleSubmit}>
        <Input id="email" label="이메일" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Input id="password" label="비밀번호" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "처리 중..." : "로그인"}
        </Button>
      </form>
    </div>
  );
}
```

`frontend/src/pages/Login/Login.module.css`:
```css
.wrap { padding-top: 24px; }

.title {
  font-size: 28px;
  margin-bottom: 24px;
  color: var(--color-primary);
}

.notice {
  color: var(--color-primary);
  font-size: 14px;
  margin-bottom: var(--space);
}

.error {
  color: var(--color-error);
  font-size: 14px;
  margin-bottom: var(--space);
}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd frontend; npm run build`
Expected: 빌드 성공.

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/Login
git commit -m "feat(frontend): 로그인 페이지 (status 분기·suspended 차단·가입완료 안내)"
```

---

## Task 8: 인증대기/홈 페이지 + 라우트 보호 + App 배선

**Files:**
- Create: `frontend/src/pages/Pending/Pending.tsx`, `frontend/src/pages/Pending/Pending.module.css`, `frontend/src/pages/Home/Home.tsx`, `frontend/src/components/ProtectedRoute.tsx`
- Modify: `frontend/src/main.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: Pending 페이지 작성**

`frontend/src/pages/Pending/Pending.tsx`:
```tsx
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { Button } from "../../components/Button/Button";
import styles from "./Pending.module.css";

export default function Pending() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>승인 대기 중</h1>
      <p className={styles.desc}>
        학생증 인증이 검토 중입니다. 승인되면 매칭에 참여할 수 있어요.
      </p>
      <Button onClick={handleLogout}>로그아웃</Button>
    </div>
  );
}
```

`frontend/src/pages/Pending/Pending.module.css`:
```css
.wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  text-align: center;
  gap: 16px;
}

.title {
  font-size: 28px;
  color: var(--color-primary);
}

.desc {
  font-size: 15px;
  margin-bottom: 16px;
}
```

- [ ] **Step 2: Home placeholder 작성**

`frontend/src/pages/Home/Home.tsx`:
```tsx
export default function Home() {
  return <h1>홈 (준비 중)</h1>;
}
```

- [ ] **Step 3: ProtectedRoute 작성**

`frontend/src/components/ProtectedRoute.tsx`:
```tsx
import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/auth";

interface Props {
  children: ReactNode;
  requireStatus?: "pending" | "active";
}

export function ProtectedRoute({ children, requireStatus }: Props) {
  const { user, loading } = useAuth();

  if (loading) return <p>불러오는 중...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.status === "suspended") return <Navigate to="/login" replace />;

  // 요구 status와 다르면 본인 status의 목적지로 보정
  if (requireStatus && user.status !== requireStatus) {
    return <Navigate to={user.status === "active" ? "/home" : "/pending"} replace />;
  }
  return <>{children}</>;
}
```

- [ ] **Step 4: main.tsx에 AuthProvider 추가**

`frontend/src/main.tsx` 수정 (AuthProvider로 감싸기):
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./lib/auth";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 5: App.tsx 라우트 정의**

`frontend/src/App.tsx` 전체 교체:
```tsx
import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing/Landing";
import Register from "./pages/Register/Register";
import Login from "./pages/Login/Login";
import Pending from "./pages/Pending/Pending";
import Home from "./pages/Home/Home";
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
      <Route
        path="/home"
        element={
          <ProtectedRoute requireStatus="active">
            <Home />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
```

- [ ] **Step 6: 빌드 + 전체 테스트 확인**

Run: `cd frontend; npm run build`
Expected: 빌드 성공.

Run: `cd frontend; npm run test`
Expected: PASS (api 6 + routing 2 + auth 3 = 11 tests).

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/pages/Pending frontend/src/pages/Home frontend/src/components/ProtectedRoute.tsx frontend/src/main.tsx frontend/src/App.tsx
git commit -m "feat(frontend): 인증대기·홈 placeholder + ProtectedRoute + 라우트 배선"
```

---

## Task 9: 수동 통합 검증

백엔드를 켠 상태에서 실제 플로우를 확인한다.

**Files:** 없음 (검증만)

- [ ] **Step 1: 백엔드 기동**

Run (별도 터미널): `cd backend; uv run uvicorn app.main:app --reload`
Expected: `http://localhost:8000` 기동.

- [ ] **Step 2: 프론트 기동**

Run (별도 터미널): `cd frontend; npm run dev`
Expected: `http://localhost:5173` 기동.

- [ ] **Step 3: 플로우 수동 확인**

브라우저 `http://localhost:5173`:
1. 랜딩 → [회원가입] → 폼 작성(이메일/8자비번/이름/학교) → 가입 → `/login` 이동 + "가입 완료" 안내.
2. 같은 이메일 재가입 시도 → "이미 사용 중인 이메일입니다" 표시.
3. 로그인 → 신규 유저는 status `pending` → `/pending` 이동, 승인대기 화면.
4. `/pending`에서 [로그아웃] → `/login`.
5. (관리자로 해당 유저 active 승인 후) 재로그인 → `/home` 이동.
6. 토큰 없이 `/home` 직접 접근 → `/login` redirect.

Expected: 모든 단계 정상.

- [ ] **Step 4: 디자인토큰 확인**

브라우저 개발자도구로 색상이 크림(#FFF5E6)/코랄(#FF7F5C)/오렌지(#FF9472)만 쓰였는지 확인. 임의 색상 없어야 함.

- [ ] **Step 5: PROGRESS.md 갱신**

`docs/superpowers/PROGRESS.md`의 프론트엔드 상태를 "인증 플로우 완료"로 갱신, 커밋.

```bash
git add docs/superpowers/PROGRESS.md
git commit -m "docs: 프론트엔드 인증 플로우 완료 반영"
```

---

## Self-Review 결과

**Spec coverage:**
- §2 기술결정 → Task 1 (스택), Task 2~3 (TS 타입/로직). ✅
- §3 디렉토리구조 → Task 1, 전 태스크. ✅
- §4 디자인토큰 → Task 1 Step 5. ✅
- §5 API계약 → Task 2 (api.ts). ✅
- §6 AuthContext → Task 3. ✅
- §7 화면흐름 → Task 5(랜딩)/6(가입)/7(로그인)/8(대기). ✅
- §8 라우트보호 → Task 8 ProtectedRoute. ✅
- §9 에러처리 → Task 2 parseDetail + 각 폼 인라인. ✅
- §10 보안 → Task 1 Step 8 보안체크, .env gitignore. ✅
- §11 테스트 → Task 2/3 vitest. ✅
- §12 성공기준 → Task 9 수동검증 + build/test. ✅

**Placeholder scan:** 모든 step에 실제 코드/명령 존재. /home·Home.tsx는 의도된 placeholder(스펙 명시). ✅

**Type consistency:** `UserOut`/`UserStatus`/`TokenResponse`/`RegisterPayload`(types.ts) → api.ts/auth.tsx/routing.ts/페이지 전반 일관. `destinationFor`, `apiFetch`, `ApiError`, `login/logout`, `setToken/getToken/clearToken` 시그니처 태스크 간 일치. ✅
