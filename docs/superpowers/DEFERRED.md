# 생략·보류 항목 기록 (의도적으로 넘어간 것들)

> 세션 넘어가면 컨텍스트 유실됨. "나중에 안 한 거 찾아줘" 할 때 이 파일이 정본.
> git 히스토리·계획 체크박스로 안 잡히는 "의도적 skip / 나중에 결정" 항목만 모음.
> **최종 업데이트: 2026-06-14**

---

## 프론트엔드 Plan 2 (브랜치 `feat/frontend-auth`) — 진행 중

### 미완 태스크
정본 = 계획 파일 체크박스: `docs/superpowers/plans/2026-06-13-frontend-auth.md`
- Task 5 랜딩 / Task 6 회원가입 / Task 7 로그인 / Task 8 대기·홈+ProtectedRoute+App배선 / Task 9 수동통합검증+PROGRESS갱신
- (Task 1~4 완료: 스캐폴드·API래퍼·AuthContext·Button/Input. 테스트 14개 통과.)

### 코드리뷰서 의도적으로 skip한 것 (재검토 가능)
| 위치 | 항목 | skip 이유 |
|------|------|-----------|
| `frontend/src/lib/api.ts` | `VITE_API_URL` 미설정 시 가드 없음 → `undefined`+path로 fetch | YAGNI. 운영빌드 전 module-load 가드 추가 검토 |
| `frontend/src/lib/api.ts` `parseDetail` | FastAPI 422 다중에러 중 **첫 msg만** 표시 | UX 선택. 다중표시 원하면 `detail.map(e=>e.msg).join(", ")` |
| `frontend/src/lib/api.ts` | 네이밍 비일관: `registerUser`/`fetchMe` vs `loginRequest` | 기능 무해. 정리시 `loginUser`로 |
| `frontend/src/lib/auth.tsx` | `AuthContext` 미export | `useAuth`로 충분. HOC/DevTools 필요시 export |

### 설계 단계서 의도적으로 안 한 것
- **UI 유닛테스트 없음** (Button/Input/페이지) — 수동확인만 (스펙 §11 결정). 순수로직(api/auth/routing)만 vitest.
- **E2E/렌더링 테스트 없음** — Plan 2 범위 밖.
- **`/home` = placeholder** — 홈 화면은 이후 Plan.
- **`/suspended` 전용 라우트 없음** — 로그인 화면서 인라인 차단 메시지로 처리.

---

## 백엔드 — 기존 미결 (상세는 PROGRESS.md / CLAUDE.md)
- 매칭 알고리즘 + `/admin/match/run` + `/admin/matches` → 🚫 명령 전까지 금지
- Alembic 초기 마이그레이션 → ⏸️ PostgreSQL/Railway 환경 필요
- 붉은실 통째교체 **race** → 운영 전 row-lock 검토
- received count 정합 불변식: **모든 쓰기는 strip 엔드포인트 경유 필수** (시드/마이그레이션도)
- game PR **#1 미병합** (`feat/game-endpoints`)

---

## ⚠️ 브랜치 분기 주의 (PROGRESS.md 충돌 예상)
PROGRESS.md 내용이 브랜치마다 다름:
- `feat/game-endpoints`: 최신 (game 완료, 테스트 59, 2026-06-09)
- `main` / `feat/frontend-auth`: 구버전 (game "구현 대기", 테스트 33, 2026-06-04)

→ game PR + frontend PR 둘 다 병합 시 **PROGRESS.md 머지 충돌** 발생. 병합 후 수동 통합 필요.
→ 그래서 frontend 브랜치선 PROGRESS.md 직접 수정 안 하고 이 파일에 따로 기록함.

---

## 운영 전 교체 필수 (CLAUDE.md "미결 항목"과 동일 — 중복 방지용 포인터)
매칭 요일/시간 · 매칭 알고리즘 상세 · 16개 대학 목록 · 카카오 알림톡 — 전부 팀 결정/사업자등록 후.
