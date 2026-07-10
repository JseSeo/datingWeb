# 학생증 인증 — 완료 기록 + 다음 작업 (관리자 심사 UI)

> **다음 세션 재개 명령:**
> `RESUME-verification-frontend.md 읽고 이어서`

**최종: 2026-07-11**
**상태: ✅ 학생증 업로드(PR #3) + ✅ 이미지 비공개화(PR #4) 둘 다 main 머지됨. 다음 = 관리자 심사 UI (미착수)**

---

## ✅ 완료 (전부 main)

### 기능 1 — 학생증 인증 업로드 (PR #3)
| Task | 내용 | 커밋 |
|------|------|------|
| 1 | 백엔드 `GET /me/verification` | 4aa230c |
| 2 | 프론트 타입 + API (FormData) | 42b0cd9 |
| 3 | UploadForm (클라검증·미리보기·에러) | e430313 |
| 4 | Pending 상태기계 (마운트1회조회, active→홈) | 142241a |
| fix | try/catch 에러화면 · active 깜빡임 제거 | 6c23019, dd422d0 |

### 기능 2 — 학생증 이미지 비공개화 (PR #4, main=f313a01 이후)
개인정보 노출 두 겹 제거:
1. API 응답의 서버 파일경로/파일명 노출 제거.
2. 무인증 정적 서빙(`/uploads`) 차단 → 관리자 전용 인증 엔드포인트.

| 변경 | 커밋 |
|------|------|
| 학생증을 비공개 `verification_dir`로 분리 + 확장자 sanitize | 945a759 |
| `VerificationOut` image_url 제거 + `GET /admin/verifications/{id}/image` | 77f3ac8 |
| 프론트 `VerificationOut` 타입 image_url 제거 | 4df74ca |
| `.gitignore`에 `backend/verification_uploads/` | f313a01 |

- 스펙: `docs/superpowers/specs/2026-07-10-verification-image-privacy-design.md`
- 계획: `docs/superpowers/plans/2026-07-10-verification-image-privacy.md`
- 테스트: 백엔드 78/78 · 프론트 41/41 · build clean.

---

## ⬜ 다음 작업 — 관리자 학생증 심사 UI (프로덕션 필수 #2)

프론트 `/admin` 화면 없음. 백엔드는 준비됨. **새 기능 → brainstorming부터 시작할 것.**

### 준비된 백엔드 엔드포인트 (`backend/app/api/verification.py`)
| 엔드포인트 | 용도 | 권한 |
|-----------|------|------|
| `GET /admin/verifications` | pending 목록 | require_admin |
| `POST /admin/verifications/{id}` `{action:"approve"\|"reject"}` | 승인/반려 (approve 시 user active로) | require_admin |
| `GET /admin/verifications/{id}/image` | 학생증 이미지 (FileResponse) | require_admin |

### ⚠️ brainstorming에서 먼저 풀어야 할 설계 걸림돌 (이미 조사됨)
- **A. 이미지 표시 = 인증 fetch 필요.** 이미지 엔드포인트는 Bearer 토큰 요구. `<img src=...>`는 Authorization 헤더 안 붙어 안 뜸. → blob fetch(헤더 포함) 후 `URL.createObjectURL` 방식 필요. (`api.ts`의 `apiFetch`는 JSON 전용 → blob용 별도 함수 필요.)
- **B. 목록에 신원정보 없음.** `GET /admin/verifications` 응답 = `{id, user_id, status, reviewed_at, created_at}`뿐. 심사하려면 **이름·대학**(주장 신원 대조) 필요. → 백엔드 응답 확장(user name/university 포함) 스코프에 넣을지 결정 필요. **UI만으로는 불충분.**

### 프론트 기존 패턴 (조사됨)
- 라우팅: `App.tsx` react-router, `ProtectedRoute(requireStatus)`. **is_admin 게이트 아직 없음** — `/admin` 라우트는 `user.is_admin` 체크 추가 필요.
- `UserOut.is_admin: boolean` 존재 (`types.ts:15`).
- API: `lib/api.ts` `apiFetch<T>` 헬퍼 + 엔드포인트별 함수 (admin 함수 미존재).
- 디자인 토큰: `frontend/CLAUDE.md` (크림 #FFF5E6, 코랄 #FF7F5C). 임의 색상 금지.
- 페이지 폴더구조 `src/pages/`, 각 페이지 `.test.tsx` 동반 (TDD).

---

## 참고
- 백엔드 없으면 null 반환(404 아님). 승인 감지 = 마운트 1회 조회(폴링 없음).
- 비차단 Minor (기능1 리뷰 지적): UploadForm blob `revokeObjectURL` 없음 / `accept="image/*"` 넓음 / `messageFor` approved 분기 도달불가.
- **매칭 알고리즘 = "설계 시작해" 명령 전까지 금지.**

## 환경 메모
- 백엔드 테스트: `cd backend && uv run pytest -v`
- 프론트: `cd frontend && npm run test` / `npm run build`
- git(머지/push/PR) = 사용자 허락 필수.
