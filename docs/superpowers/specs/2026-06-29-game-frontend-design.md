# Game 프론트엔드 설계 (오작교 · 붉은실)

> 상태: 설계 확정 (브레인스토밍 완료)
> 작성: 2026-06-29
> 브랜치: `feat/frontend-auth` (구현은 game 백엔드 병합 후)

## 0. 선행 조건 (구현 전 필수)

- **game 백엔드 병합**: `feat/game-endpoints` 브랜치가 아직 `main`에 미병합. 이 PR을 먼저 병합한 뒤 game 프론트 구현 시작. (설계/스펙 작성은 무관하게 진행 가능)

## 1. 범위

active 유저용 game 화면 2개 탭(오작교·붉은실) + 화면 도달용 상단 네비게이션.

포함:
- 상단 고정 네비게이션 (홈 · 게임 · 마이페이지) — 공용 레이아웃 래퍼
- `/game` 라우트, 내부 2탭(오작교 / 붉은실)
- `api.ts`에 game API 함수 5개 추가
- 에러 처리 (백엔드 detail 표시 + 일부 클라이언트 자체검증)

제외 (YAGNI):
- 매칭 알고리즘 (CLAUDE.md 금지 항목)
- 대학 목록 드롭다운 (CLAUDE.md 금지 → 대학 입력은 자유 텍스트)
- 하단 탭바 (사용자가 상단 네비 선택)

## 2. 네비게이션

### 2.1 배치
- **상단 고정** (`position: fixed; top: 0`), max-width 390px 중앙 정렬
- 3링크 가로 배치: **홈** `/home` · **게임** `/game` · **마이페이지** `/mypage`
- active 링크 = 코랄 `#FF7F5C`, 비active = 회색. 텍스트(+이모지 아이콘) 미니멀, 애니메이션 없음
- 본문이 고정 바에 가리지 않도록 레이아웃에 `padding-top` 적용

### 2.2 노출 범위
active 유저 메인 화면에만 노출: `/home`, `/game`, `/mypage`.
landing(`/`) · login · register · pending 에는 **노출 안 함**.

### 2.3 구현 방식 — 공용 레이아웃 래퍼 (B안)
`MainLayout` 컴포넌트가 네비 + `<Outlet/>`(자식 페이지)을 감쌈. 네비 코드 1곳 관리.

```tsx
// frontend/src/components/MainLayout/MainLayout.tsx
export default function MainLayout() {
  return (
    <>
      <TopNav />
      <main><Outlet /></main>
    </>
  );
}
```

```tsx
// App.tsx — 네비 필요한 라우트만 래퍼로 묶음 (각 페이지는 기존 ProtectedRoute 유지)
<Route element={<MainLayout />}>
  <Route path="/home" element={<ProtectedRoute requireStatus="active"><Home/></ProtectedRoute>} />
  <Route path="/game" element={<ProtectedRoute requireStatus="active"><Game/></ProtectedRoute>} />
  <Route path="/mypage" element={<ProtectedRoute><MyPage/></ProtectedRoute>} />
</Route>
```

페이지들은 네비를 모름(관심사 분리). 새 페이지 추가 시 래퍼 안에 넣으면 네비 자동 적용.

### 2.4 파일
- `frontend/src/components/MainLayout/MainLayout.tsx` (+ `.module.css`)
- `frontend/src/components/TopNav/TopNav.tsx` (+ `.module.css`)
- `frontend/src/App.tsx` — 라우트 구조 수정

## 3. /game 라우트 + 탭 구조

- 단일 라우트 `/game`, `<ProtectedRoute requireStatus="active">` 보호 (Home과 동일)
- 내부 2탭 전환: `[오작교] [붉은실]` — 컴포넌트 state로 전환, URL 안 바뀜
- 파일:
  - `frontend/src/pages/Game/Game.tsx` (+ `.module.css`) — 탭 전환 컨테이너
  - `frontend/src/pages/Game/OjakgyoTab.tsx`
  - `frontend/src/pages/Game/RedThreadTab.tsx`
- 기존 디자인 토큰 + Button/Input 컴포넌트 재사용

## 4. API 계층 (`frontend/src/lib/api.ts`)

기존 `apiFetch<T>` / `ApiError` 패턴 사용. game 함수 추가:

```ts
postOjakgyo(payload): Promise<OjakgyoOut>           // POST /game/ojakgyo
postRedThread(targets): Promise<RedThreadOut>       // POST /game/red-thread
getRedThread(): Promise<RedThreadOut>               // GET  /game/red-thread
getRedThreadReceived(): Promise<{count:number}>     // GET  /game/red-thread/received
```

(오작교는 조회 API 없음 — fire-and-forget)

### 4.1 백엔드 계약 (feat/game-endpoints, 확인 완료)

```
POST /game/ojakgyo
  body: {person_a_name, person_a_university, person_b_name, person_b_university}  (각 min 1자)
  → 201 OjakgyoOut
  400 "이름과 학교를 입력해야 합니다"          (빈 입력)
  400 "본인은 지목 대상에 포함될 수 없습니다"   (본인이 짝에 포함)
  400 "서로 다른 두 사람을 지목해야 합니다"     (A == B)
  409 "이미 지목한 쌍입니다"                   (같은 지목자·같은 쌍 중복)
  ※ 쌍은 순서무관 정규화됨 (A,B == B,A)

POST /game/red-thread
  body: {targets: [{target_name, target_university}, ...]}  (1~2개, 최소 1 필수)
  → 200 RedThreadOut {targets:[...]}
  400 "이름과 학교를 입력해야 합니다"      (빈 입력)
  400 "본인을 지목할 수 없습니다"          (self)
  400 "같은 상대를 두 번 입력할 수 없습니다" (중복)
  ※ 목록 통째 덮어쓰기 (기존 전부 삭제 후 재삽입)

GET /game/red-thread          → 200 {targets:[...]}  (없으면 빈 배열)
GET /game/red-thread/received → 200 {count: N}        (익명, 나를 지목한 인원수)
```

## 5. 오작교 탭 (중매)

동작: fire-and-forget. 조회 없음 → 제출 → 성공 → 폼 리셋.

### 5.1 입력 (제3자로서 두 사람 짝지어줌)
- 사람A: 이름 + 대학 (자유 텍스트)
- 사람B: 이름 + 대학 (자유 텍스트)
- 4필드 모두 필수

### 5.2 제출 흐름
1. 클라이언트 자체검증: A == B(이름+대학 동일)면 제출 전 차단, "두 사람이 같아요"
2. POST `/game/ojakgyo`
3. 성공(201) → "중매 완료!" 메시지 + 폼 리셋
4. 실패 → 인라인 에러 (Register 페이지 에러 스타일 재사용), 백엔드 `detail` 문구 그대로 표시

### 5.3 에러 표시
백엔드 detail이 이미 사유별 한국어 문구 → `ApiError.detail` 직접 표시.
A == B만 클라이언트 선차단(즉시 피드백). 본인포함/중복 등은 백엔드 응답 표시.

## 6. 붉은실 탭

동작: 상태 있음. 마운트 시 현재값 prefill + 받은 인원수 표시. 제출은 덮어쓰기.

### 6.1 마운트 시 (2개 GET 병렬)
1. `GET /game/red-thread` → 현재 내 지목 prefill (0~2명)
2. `GET /game/red-thread/received` → `{count:N}` → "나를 N명이 지목했어요" 표시 (익명)
   - count 0 → "아직 나를 지목한 사람이 없어요"

### 6.2 입력 (최대 2명)
- 슬롯1: 이름 + 대학 (1명은 반드시 입력 — 백엔드 최소 1 요구)
- 슬롯2: 이름 + 대학 (선택)
- 대학 = 자유 텍스트

### 6.3 제출 흐름
1. 클라이언트 자체검증: 슬롯1 == 슬롯2면 차단, "같은 사람을 두 번 넣을 수 없어요". 유효 슬롯 0개면 제출 버튼 비활성
2. POST `/game/red-thread` `{targets:[...]}` (빈 슬롯 제외, 채워진 것만)
3. 성공(200) → "저장됐어요" + 응답으로 prefill 갱신
4. 실패 → 인라인 에러, 백엔드 `detail` 표시

### 6.4 제약 메모
- 백엔드가 최소 1명 요구(`min_length=1`) → **전체 비우기(지목 취소) 기능 없음**. 한 번 제출하면 최소 1명 유지. 향후 취소 필요 시 백엔드 변경 필요 — 현재 범위 외.

## 7. 테스트

기존 프론트 테스트 패턴(vitest) 따름:
- TopNav: active 링크 하이라이트, 노출 라우트
- OjakgyoTab: A==B 선차단, 성공 시 리셋, 백엔드 에러 detail 표시
- RedThreadTab: prefill 렌더, received count 표시, 슬롯1==슬롯2 선차단, 덮어쓰기 제출

## 8. 미해결 / 메모

- ⚠️ **모바일 vs 웹 우선순위 충돌**: `frontend/CLAUDE.md`는 "모바일 우선, max-width 390px" 명시. 사용자는 이번에 "웹 먼저" 결정. 상단 네비는 둘 다 호환되어 현재 무방하나, 추후 문서 우선순위 정리 필요.
- 붉은실 전체 취소 기능 부재 (§6.4) — 운영 중 요청 시 백엔드 변경.
