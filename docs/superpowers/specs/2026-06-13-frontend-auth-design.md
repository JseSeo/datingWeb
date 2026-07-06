# 프론트엔드 Plan 2 — 기반 세팅 + 인증 플로우 설계

> 작성일: 2026-06-13
> 스코프: 프론트엔드 프로젝트 기반 + 인증 플로우 화면 (랜딩/회원가입/로그인/인증대기)
> 상위 스펙: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`
> 프론트 규칙: `frontend/CLAUDE.md`

## 1. 목표 / 범위

프론트엔드 첫 착수. 빈 `frontend/` 디렉토리에 Vite+React+TS 프로젝트를 세우고,
백엔드 auth 엔드포인트와 연동되는 인증 플로우 4화면을 구현한다.

**포함:**
- 프로젝트 기반 세팅 (Vite, 라우팅, API 클라이언트, 인증 컨텍스트, 디자인 토큰)
- 랜딩 `/`, 회원가입 `/register`, 로그인 `/login`, 인증대기 `/pending`

**제외 (이후 Plan):**
- 설문 `/survey`, 프로필 `/profile`, 홈 `/home`, 게임 `/game`, 마이페이지 `/mypage`, 관리자 `/admin`, 신고 `/report`
- `/home`은 라우트 보호 골격 검증용 placeholder만 둔다.

## 2. 기술 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 언어 | TypeScript | CLAUDE.md가 frontend를 .tsx/.ts로 가정. 타입안전 + API 응답 타입 정의 |
| 스타일 | CSS Modules | Vite 내장, 의존성 0. 디자인토큰은 CSS 변수 |
| 라우팅 | react-router-dom | 표준 |
| 폼 | useState 수동 | 인증폼 단순. 라이브러리 불필요 (YAGNI) |
| 테스트 | vitest | api/auth 로직 유닛테스트 |

## 3. 디렉토리 구조

```
frontend/
  .env.example          # VITE_API_URL=http://localhost:8000
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  src/
    main.tsx            # 진입점 + BrowserRouter + AuthProvider
    App.tsx             # 라우트 정의
    vite-env.d.ts
    styles/
      tokens.css        # 디자인토큰 (CSS 변수)
      global.css        # reset + 모바일 컨테이너
    lib/
      api.ts            # fetch 래퍼 (VITE_API_URL + Bearer 자동첨부 + 에러파싱)
      auth.tsx          # AuthContext (token/user 상태, login/logout/refresh)
      types.ts          # UserOut, TokenResponse 등 API 타입
    pages/
      Landing/Landing.tsx
      Register/Register.tsx + Register.module.css
      Login/Login.tsx + Login.module.css
      Pending/Pending.tsx
    components/
      Button/Button.tsx + Button.module.css
      Input/Input.tsx + Input.module.css
```

## 4. 디자인 토큰 (`tokens.css`)

frontend/CLAUDE.md 디자인시스템 그대로:

```css
:root {
  --color-bg: #FFF5E6;       /* 크림 */
  --color-primary: #FF7F5C;  /* 코랄 */
  --color-secondary: #FF9472;/* 오렌지 */
  --container-max: 390px;    /* 모바일 우선 */
}
```

`global.css`: 기본 reset, body 배경 크림, 중앙정렬 컨테이너(max-width 390px, PC 중앙).
디자인토큰 외 임의 색상 금지 (CLAUDE.md 규칙).

## 5. API 계약 (백엔드 확인 완료)

| 호출 | 요청 본문 | 응답 | 에러 |
|------|-----------|------|------|
| `POST /auth/register` | `{email, password, name, university}` | `UserOut` (201) | 409 중복이메일, 422 검증실패 |
| `POST /auth/login` | `{email, password}` | `{access_token, token_type}` | 401 불일치 |
| `GET /me` | (Authorization: Bearer) | `UserOut` | 401 |

- password 검증: 8자 이상 (백엔드 422). 프론트도 제출 전 1차 검증.
- `UserOut.status`: `pending` / `active` / `suspended`.

### api.ts 동작
- `VITE_API_URL` 베이스 + 경로.
- localStorage 토큰 있으면 `Authorization: Bearer <token>` 자동첨부.
- non-2xx 시 응답 JSON의 `detail`을 메시지로 `ApiError` throw.
- 401 응답 시 토큰 삭제 (호출측에서 `/login` 유도).

## 6. 인증 컨텍스트 (`auth.tsx`)

상태: `{ token: string | null, user: UserOut | null }`.

- `login(email, password)`: `POST /login` → 토큰 저장(localStorage + state) → `GET /me` → user 저장.
- `logout()`: 토큰/유저 삭제.
- `refresh()`: 앱 시작 시 토큰 있으면 `GET /me`로 user 복원 (실패 시 logout).

## 7. 화면별 흐름

### 랜딩 `/`
소개 텍스트 + [회원가입] [로그인] 버튼. 이미 로그인 상태면 status 따라 redirect.

### 회원가입 `/register`
- 입력: email, password, name, university.
- 제출 전 검증: 빈값/이메일형식/password 8자.
- `POST /register` 성공(201) → **자동로그인 안 함** → `/login`으로 이동 (가입완료 안내).
- 409 → "이미 사용 중인 이메일" 인라인 표시.

### 로그인 `/login`
- 입력: email, password.
- `login()` 호출 성공 → user.status 분기:
  - `pending` → `/pending`
  - `active` → `/home` (placeholder)
  - `suspended` → 차단 안내 메시지
- 401 → "이메일 또는 비밀번호가 올바르지 않습니다" 인라인 표시.

### 인증대기 `/pending`
- "학생증 승인 대기중입니다" 안내 + [로그아웃].
- pending 유저 전용. active/없음이면 redirect.

## 8. 라우트 보호

`<ProtectedRoute>` 래퍼:
- 토큰/유저 없음 → `/login`.
- status `pending` → `/pending` 강제.
- status `active` → 통과.
- status `suspended` → 차단 안내.

Plan 2는 `/home` placeholder로 보호 골격만 검증.

## 9. 에러 처리

- 모든 API 에러는 `ApiError`(detail 메시지) → 폼 인라인 표시.
- 네트워크 실패 → "서버 연결 실패" 일반 메시지.
- 401 → 토큰 삭제 + `/login`.

## 10. 보안

- API URL은 `VITE_API_URL` 환경변수만. 하드코딩 금지.
- `.env`는 gitignore 등록됨 (루트 `.gitignore`). `.env.example`만 커밋.
- JWT는 localStorage 저장 (CLAUDE.md 규칙). 운영 시 XSS 대비는 별도 과제.
- 백엔드 CORS는 `http://localhost:5173`(Vite 기본) 허용 중 — dev 일치.

## 11. 테스트 (vitest)

유닛테스트 대상 (순수 로직):
- `api.ts`: Bearer 토큰 자동첨부, non-2xx → ApiError(detail) 파싱, 401 토큰삭제.
- `auth.tsx` 로직: login 시 토큰저장+user설정, logout 클리어.
- status 분기 헬퍼: pending/active/suspended → 목적지 경로.

UI 렌더링/E2E는 Plan 2 범위 밖 (수동 확인).

## 12. 성공 기준

- `npm run dev` 기동, 4화면 라우팅 동작.
- 회원가입 → 로그인 → status별 redirect 실제 백엔드 연동 확인.
- `npm run test` (vitest) 통과.
- `npm run build` 성공.
- 디자인토큰 외 색상 미사용.
