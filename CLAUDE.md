# DateDrop Korea

한국 대학생 주간 소개팅 매칭 웹서비스. 학생증 인증 + 가치관 설문 기반 매칭.

- 스펙: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`
- 프론트: React(Vite) → `frontend/` (각 규칙: `frontend/CLAUDE.md`)
- 백엔드: Python FastAPI → `backend/` (각 규칙: `backend/CLAUDE.md`)

## 작업 규칙

| 규칙 | 내용 |
|------|------|
| 스킬 | 작업 전 관련 스킬 먼저 선언 후 진행 |
| 설명 | 작업마다 이유/구조 설명 필수 (코딩 초보자) |
| git | 커밋/브랜치/푸시는 반드시 허락 후만 실행 |
| 스펙 | 스펙이 진실. 코드↔스펙 충돌 시 사용자 확인 후 스펙 먼저 수정 |
| 스킬 경합 | superpowers `test-driven-development` 우선 |

## 워크플로우

| 단계 | 방법 |
|------|------|
| 기능 정의 | `brainstorming` 먼저 — 모호함 제거, 요구사항 정리 |
| 구현 계획 | `writing-plans` |
| 작은 구현 (1~2파일, 스펙 명확) | 직접 or `cavecrew-builder` dispatch |
| 큰 구현 (다파일, plan 필요) | `writing-plans` → `subagent-driven-development` |

## 핵심 위반 금지

| 금지 항목 | 이유 |
|----------|------|
| 매칭 알고리즘 구현 | 미결 — "매칭 알고리즘 설계 시작해" 명령 전까지 금지 |
| 카카오 알림톡 연동 | 사업자등록 완료 전 금지 |
| 대학 목록 하드코딩 | 팀 미결 항목 |
| 요청하지 않은 기능 추가 | YAGNI |
| 허락 없이 git push | — |

## 도구 설정

- **caveman 모드** `full` + 한국어 기본. 응답 ~75% 토큰 절감. 끄기: "stop caveman"
- **메인 = 오케스트레이터**: 메인세션은 계획·판단·검증만. 코드 조사/편집은 subagent 위임
- **새 세션 권장**: 컨텍스트 압축 발생 or 대화 매우 길어지면 완료 후 새 세션 권장

## 모델 사용 규칙

| 작업 유형 | 모델 | 예시 |
|----------|------|------|
| 코드 탐색 / 파일 읽기 | sonnet | cavecrew-investigator |
| 단순 편집 (1~2파일) | sonnet | cavecrew-builder |
| diff / PR 리뷰 | sonnet | cavecrew-reviewer |
| 아키텍처 설계 / 복잡한 버그 분석 | opus | 일반 Agent dispatch |
| 구현 계획 수립 / 스펙 검토 | opus | writing-plans, subagent-driven-development |

## 커밋 형식

```
<영어prefix>(<scope>): <한국어 제목>
```

prefix: feat / fix / docs / chore / refactor / test / perf / ci

<example>
feat(backend): auth 엔드포인트 (register, login)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
</example>

<example>
fix(backend): JWT 토큰 만료 검증 로직 수정 — `<` → `<=`

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
</example>

<example>
chore: .gitignore Claude Code 개인설정 추가

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
</example>

## 미결 항목 (운영 전 교체 필수)

| 항목 | 상태 |
|------|------|
| 매칭 요일/시간 | 팀 결정 필요 |
| 매칭 알고리즘 상세 | 팀 회의 후 별도 설계 |
| 16개 대학 목록 | 팀 내부 선정 |
| 카카오 알림톡 | 사업자등록 완료 후 연동 |

## 도입 보류: code-review-graph (트리거 시 재검토)

현재 코드탐색은 `smart-explore`(claude-mem 번들, tree-sitter AST, on-demand)로 충분.
code-review-graph는 영속 그래프 인덱스(관계/영향분석)지만 훅 상시비용 + smart-explore와 중복 → 현 규모선 보류.

**아래 트리거 中 하나라도 뜨면 메인세션이 사용자에게 도입 권고할 것:**

| # | 트리거 | 측정 |
|---|--------|------|
| 1 | 소스 파일 수십~수백 개로 증가 | backend `*.py` + frontend `*.tsx/ts` 합산 |
| 2 | "이거 고치면 어디 깨지나" 영향분석을 세션마다 반복 | cross-file 관계 추적 빈발 |
| 3 | smart-explore 단독 탐색이 답답 (풀파일 재읽기 잦음) | 체감 |

**발동 시 행동:** ① 친구 원본 가이드의 `.mcp.json` code-review-graph 설정 복사(정확한 서버 커맨드 거기 있음) → ② 1주 켜고 caveman-stats로 smart-explore 대비 토큰 실측 → ③ 절감 확인되면 유지, 아니면 제거.
