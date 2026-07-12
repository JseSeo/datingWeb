# 관리자 학생증 심사 UI — 설계

**작성: 2026-07-13**
**상태: 설계 합의 완료, 구현 대기**

프론트에 관리자 학생증 심사 화면(`/admin`)이 없다. 백엔드 심사 엔드포인트는 준비돼 있으나, 목록 응답에 심사에 필요한 신원정보(이름·대학)가 빠져 있어 백엔드 스코프 확장을 함께 진행한다.

관련 선행 작업:
- 학생증 업로드: PR #3 (main)
- 학생증 이미지 비공개화: PR #4 (main) — `docs/superpowers/specs/2026-07-10-verification-image-privacy-design.md`

---

## 1. 백엔드 변경

### 신규 스키마 `AdminVerificationOut`
`backend/app/schemas/verification.py`에 추가.

```
id: int
user_id: int
status: VerificationStatus
reviewed_at: datetime | None
created_at: datetime
name: str          # 심사용 — 유저가 주장한 이름
university: str    # 심사용 — 유저가 주장한 대학
```

기존 `VerificationOut`(본인용, `GET /me/verification`)은 **변경하지 않는다**. 신원정보는 관리자 응답에만 노출 → 최소노출 유지.

### 엔드포인트 변경
`GET /admin/verifications` (`backend/app/api/verification.py`):
- 응답 모델 `list[VerificationOut]` → `list[AdminVerificationOut]`.
- pending 필터는 그대로.
- 각 건의 `user_id`로 `User`를 join(또는 relationship)해 `name`·`university`를 채운다.

변경 없음:
- `POST /admin/verifications/{id}` (승인/반려) — 그대로.
- `GET /admin/verifications/{id}/image` (이미지 서빙, require_admin, FileResponse) — 그대로.

---

## 2. 프론트 — API 계층 (`frontend/src/lib/`)

### 타입 (`types.ts`)
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

### API 함수 (`lib/api.ts`) — 3개 신규

**1. `listPendingVerifications()`** — 기존 `apiFetch` 재사용 (JSON).
```ts
export function listPendingVerifications(): Promise<AdminVerificationOut[]> {
  return apiFetch<AdminVerificationOut[]>("/admin/verifications", { method: "GET" });
}
```

**2. `reviewVerification(id, action)`** — 기존 `apiFetch` 재사용 (JSON).
```ts
export function reviewVerification(
  id: number,
  action: "approve" | "reject",
): Promise<AdminVerificationOut> {
  return apiFetch<AdminVerificationOut>(`/admin/verifications/${id}`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}
```

**3. `fetchVerificationImage(id)`** — blob 처리 신규 헬퍼.

`apiFetch`는 성공 시 `res.json()`을 강제하므로 바이너리 이미지에 쓸 수 없다. 또한 `<img src=...>` 직접 지정은 브라우저가 Authorization 헤더를 붙이지 않아 401이 난다. 따라서 JS로 헤더 포함 fetch → blob → objectURL 변환한다.

```ts
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

**objectURL revoke 책임:** 헬퍼는 URL만 반환한다. `URL.revokeObjectURL`은 URL을 사용하는 카드 컴포넌트가 수행한다(이미지 닫을 때 / 카드 언마운트 시 `useEffect` 정리 함수). 헬퍼가 revoke하면 반환 즉시 URL이 무효화되므로 호출측 책임이 맞다.

---

## 3. 프론트 — 라우팅 & 접근 게이트

### `ProtectedRoute` 확장 (`components/ProtectedRoute.tsx`)
```tsx
interface Props {
  children: ReactNode;
  requireStatus?: "pending" | "active";
  requireAdmin?: boolean;   // 신규
}
```

체크 순서: 로그인 → suspended → **admin** → status.
`requireAdmin && !user.is_admin`이면 비admin은 조용히 redirect (`active` → `/home`, 그 외 → `/pending`). 기존 status 보정과 동일 패턴.

### `App.tsx` 라우트 추가
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
- 숨김 경로 — 네비게이션 링크 없음. 관리자가 URL 직접 접근.
- `MainLayout`(하단 탭) **밖**에 배치 — 일반 유저 탭바에 노출 안 함.

---

## 4. 프론트 — Admin 페이지 (`src/pages/Admin/`)

페이지 단위 폴더 구조. `Admin.tsx` + `Admin.test.tsx`.

### 상태 & 흐름
```
마운트 → listPendingVerifications() 1회 조회
  로딩       → "불러오는 중"
  실패       → 에러 메시지
  빈 목록    → "심사 대기 없음"
  목록 있음  → 카드 리스트
```

### 카드 1건 (`AdminVerificationOut`)
- 표시: **이름 · 대학**(주장 신원) + 제출일(`created_at`).
- **[학생증 보기]** 버튼 → `fetchVerificationImage(id)` → objectURL로 `<img>` 표시 (클릭 로드).
  - 카드별 개별 상태: 로딩중 / 표시중 / 에러.
  - objectURL은 카드 언마운트·재심사 시 `revokeObjectURL`.
- **[승인] [반려]** 버튼 → `reviewVerification(id, action)`.
  - 성공 → 카드를 로컬 목록에서 **즉시 제거**(낙관적 제거, 재조회 없음).
  - 실패 → 카드 유지 + 에러 표시.
  - 진행 중 버튼 disable (중복 클릭 방지).

### 디자인
크림 `#FFF5E6` 배경, 코랄 `#FF7F5C` 강조, max-width 390px 모바일 우선. 임의 색상 금지 (`frontend/CLAUDE.md`).

---

## 5. 테스트 & 검증

### 백엔드 (`backend/tests/`, TDD)
- `AdminVerificationOut` 응답에 name·university 포함.
- `GET /admin/verifications` — pending만 반환, name·university 채워짐, require_admin 게이트(비admin 403).
- 기존 78/78 회귀 없음.

### 프론트 (`Admin.test.tsx`, TDD)
- 목록 렌더(이름·대학), 빈 목록 안내, 로딩·에러.
- "학생증 보기" 클릭 → 이미지 fetch 호출 → 표시 (fetch mock).
- 승인/반려 클릭 → `reviewVerification` 호출 → 카드 제거.
- 비admin 접근 → redirect (`ProtectedRoute`).
- 기존 41/41 회귀 없음.

### 검증 게이트
- 백엔드 `cd backend && uv run pytest -v` — green.
- 프론트 `cd frontend && npm run test` + `npm run build` — green.

---

## 결정 요약

| # | 결정 | 선택 |
|---|------|------|
| 1 | 신원정보 전달 | admin 전용 스키마 `AdminVerificationOut` 신설 (본인 응답 불변) |
| 2 | 이미지 로드 | 클릭 시 개별 blob fetch (민감정보 최소노출·대량가입 대비) |
| 3 | admin 게이트 | `ProtectedRoute`에 `requireAdmin` 옵션 추가 |
| 4 | 심사 후 갱신 | 낙관적 제거 (재조회 없음) |

## 범위 밖 (YAGNI)
- approved/rejected 이력 조회 화면.
- 관리자 진입 네비 링크/버튼 (숨김 경로 유지).
- 매칭 알고리즘 (별도 명령 전까지 금지).
