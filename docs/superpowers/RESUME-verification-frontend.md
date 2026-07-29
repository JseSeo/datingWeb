# 학생증 인증 — 완료 기록 + 다음 작업

> **다음 세션 재개 명령:**
> `RESUME-verification-frontend.md 읽고 이어서`

**최종: 2026-07-17**
**상태: ✅ 학생증 인증 전부 완료·머지됨 (업로드 PR#3 · 비공개화 PR#4 · 심사 UI PR#5 · 이미지삭제 PR#6 · 재업로드 orphan수정 PR#7). ✅ Task B(가입 동의 체크박스) 완료 → PR#8 (미머지, 리뷰대기).**

---

## ✅ 완료 — Task B: 가입 동의 체크박스 (법적, 스펙 §10) → PR#8

**결정: 서버 기록 방식** (개보법 §22 입증책임 — 클라 게이트만으론 동의 입증 불가).
- 스펙: `docs/superpowers/specs/2026-07-17-signup-consent-design.md`
- 플랜: `docs/superpowers/plans/2026-07-17-signup-consent.md`

**구현 (브랜치 `feat/signup-consent`, decea02..2aeac4a):**
- 백엔드(7a3f521): RegisterRequest 동의 3필드(agreed_terms/privacy/age_14) 필수 + register 검증(400) + User.terms_agreed_at nullable + alembic 마이그레이션. 기존 register 호출 21곳 수정. 86 pass.
- 프론트(e4ebbd3): 전체동의+3체크박스+14세고지, 버튼 게이트, placeholder ConsentModal. 58 pass, tsc+build clean.
- 최종 리뷰(opus): Ready to merge, Critical/Important 0.

**후속(비차단):**
- 실제 약관/방침 문안 = 팀/변호사 몫 → 확정 시 ConsentModal placeholder 교체
- 동의블록 CSS 미정의(무스타일), 모달 a11y(Esc/focus-trap/aria-label)
- 관찰(기존 gap): alembic versions에 users CREATE 마이그레이션 없음 → fresh DB `upgrade head` 부트스트랩 불가. prod 전 팀 인지

---

## ✅ 학생증 인증 — 완료 (전부 main 머지됨)

---

## ✅ 완료 (main 머지됨)

| 기능 | PR |
|------|-----|
| 학생증 업로드 (백엔드 `GET /me/verification` + UploadForm + Pending 상태기계) | PR #3 |
| 이미지 비공개화 (API 파일경로 제거 + 무인증 정적서빙 차단 → 관리자 전용 엔드포인트) | PR #4 |
| 관리자 학생증 심사 UI (백엔드 AdminVerificationOut + 프론트 타입/API + requireAdmin 게이트 + 심사페이지) | PR #5 (main d13279e) |

---

## 🟡 승인/반려 시 이미지 삭제 (구현완료, 미머지)

**브랜치: `feat/verification-image-deletion`**
- 스펙: `docs/superpowers/specs/2026-07-13-verification-image-deletion-design.md`

| 커밋 | 내용 |
|------|------|
| 198c598 | docs: 설계 스펙 |
| 40d8b23 | fix: 심사 완료 시 이미지 삭제 + 테스트 3개 |

**구현:** `review_verification`(backend/app/api/verification.py) — 승인·반려 commit 후 `verification_dir` 이미지 파일 삭제. 존재 체크로 멱등. `image_url` 필드는 유지(파일명 dangling, API 미노출).
**검증:** 백엔드 82/82 pass (79 + 신규 3: 승인삭제·반려삭제·멱등). TDD RED→GREEN 확인됨.

### ⬜ 다음 = 브랜치 마무리
`finishing-a-development-branch` 스킬 → PR 생성(지금까지 방식). **git = 사용자 허락 필수.**

---

## ⬜ 후속 이슈 후보 (비차단)

**심사 UI 브랜치(PR#5) Minor:**
| # | 항목 |
|---|------|
| f | Admin 카드에 `created_at`(제출일) 미표시 — 스펙엔 있으나 plan 누락 |
| g | "학생증 보기" 로딩상태 없음 + 이중클릭 시 objectURL 누수 |
| c/e | fetchImage 401분기·승인반려 실패경로·busy disable 무테스트 |
| a | 백엔드 목록 N+1 (스케일 시 `joinedload(StudentVerification.user)`) |

**이미지 삭제 브랜치 범위 밖:**
- 재업로드(upsert) 시 이전 파일 orphan 누수 — 기존 별도 버그. 정리하려면 upload upsert 시 옛 파일 삭제 추가 필요.

---

## 환경 메모
- 백엔드 테스트: `cd backend && uv run pytest -v`
- 프론트: `cd frontend && npm run test` / `npm run build` / `npx tsc --noEmit`
- git(머지/push/PR) = 사용자 허락 필수.
- **매칭 알고리즘 = "설계 시작해" 명령 전까지 금지.**
