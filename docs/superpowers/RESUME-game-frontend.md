# 이어서 작업: game 프론트엔드

**상태:** ✅ 브레인스토밍 완료 → 스펙 작성됨. 사용자 스펙 리뷰 대기 중.
**스펙:** `docs/superpowers/specs/2026-06-29-game-frontend-design.md`
**브랜치:** `feat/frontend-auth`
**최종: 2026-06-29**

## 다음 단계
1. 사용자 스펙 리뷰 → 승인
2. `writing-plans`로 구현 계획 작성
3. ⚠️ 구현(코드) 전 game 백엔드(`feat/game-endpoints`) main 병합 필수 — 아직 미병합

## 확정 결정 (스펙에 반영됨)
- 진입점: 상단 고정 네비 (홈·게임·마이페이지), 공용 레이아웃 래퍼(B안)
- game: `/game` 단일 라우트, 내부 2탭 (오작교/붉은실)
- 오작교: fire-and-forget, A==B 선차단, 백엔드 detail 표시
- 붉은실: prefill + received count + 덮어쓰기, 최소 1명(취소 기능 없음)
- 대학 입력 = 자유 텍스트 (드롭다운 금지항목)
