# 이어서 작업: game (백엔드 PR 머지 → 프론트 구현)

> **다음 세션 재개 명령:**
> `RESUME-game-frontend.md 읽고 이어서`

**최종: 2026-07-01**
**브랜치:** `feat/frontend-auth`

## 완료
- ✅ 브레인스토밍 → 스펙: `docs/superpowers/specs/2026-06-29-game-frontend-design.md`
- ✅ 구현계획 5 Task: `docs/superpowers/plans/2026-06-29-game-frontend.md`
- ✅ 백엔드 PR 리뷰 (`feat/game-endpoints`) — 테스트 26개 통과 확인(격리 워크트리+venv)
- ✅ **백엔드 PR 처리 완료 (2026-07-01)**
  - max_length=100 6필드 적용 + TDD 테스트 2개 (총 28개 통과)
  - `feat/game-endpoints` → main 머지(no-ff `0da1d1e`) + push
  - dev.db 재생성 (새 스키마 8테이블)

## 다음 단계
1. **프론트 구현** — `subagent-driven-development`로 plan Task 1→5
   - Task1 타입+api / Task2 네비+MainLayout / Task3 오작교탭 / Task4 붉은실탭 / Task5 Game셸+라우트
   - 주의: 붉은실 = **최대 2명** 리스트 (`targets:[...]`). 프론트 spec/plan 이미 2명 반영됨

## 백엔드 PR 리뷰 결과 (참고)
- 병합 가능. 코드품질 양호, IDOR 없음, 인증/검증 견고
- 🟡 미해결(제품/개인정보 판단): #1 이름+학교=신원 가정→동명이인 오염 / #2 제3자 실명 입력 동의
- 🟢 후속: #3 max_length(머지 전 1줄), #4 빈입력 422/400 혼재(무방), #5 alembic 마이그레이션 0개(운영 전 필수)

## 환경 메모
- backend venv: `backend/.venv/Scripts/python.exe` (pytest+fastapi 있음). 시스템 python엔 fastapi 없음
- 테스트 실행 시 env 필요: `DATABASE_URL` `SECRET_KEY` (.env gitignore)
- ⚠️ 구현(코드) 전 백엔드 머지 필수

## 확정 설계 (스펙 반영됨)
- 진입점: 상단 고정 네비(홈·게임·마이페이지), MainLayout 래퍼(Outlet)
- /game 단일 라우트 + 내부 2탭(오작교/붉은실) state 전환
- 오작교: fire-and-forget, A==B 선차단, 백엔드 detail 표시
- 붉은실: prefill + received count + 덮어쓰기, 최소 1명(취소 기능 없음)
- 대학 입력 = 자유 텍스트(드롭다운 금지)
- api 함수 4개: postOjakgyo, postRedThread, getRedThread, getRedThreadReceived
