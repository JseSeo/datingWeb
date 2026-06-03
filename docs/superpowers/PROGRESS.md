# DateDrop Korea — 진행 상황 (이어서 작업용)

> 세션 재시작 시 컨텍스트가 날아가므로, 작업 상태를 여기 기록한다.
> 다음 세션 시작 시 이 파일부터 읽으면 이어서 진행 가능.
> **최종 업데이트: 2026-06-04**

---

## 현재 상태 한눈에

| 영역 | 상태 |
|------|------|
| 설계 스펙 | ✅ 확정 (`specs/2026-05-23-datedrop-korea-design.md`) — 매칭 알고리즘만 보류 |
| Plan 1: 백엔드 기반 | ✅ 완료 (auth, /me, 학생증 업로드, 관리자 승인) |
| 백엔드: 설문(survey) | ✅ 완료 (2026-06-01, 커밋 `466bba1`) |
| 백엔드: game (오작교/붉은실) | 🟡 설계 확정 (2026-06-04, 스펙 §6 갱신) — 구현 대기 |
| 백엔드: reports (신고) | ✅ 완료 (2026-06-03, `POST /reports`) |
| 백엔드: match (매칭 실행) | 🚫 금지 — "매칭 알고리즘 설계 시작해" 명령 전까지 |
| Alembic 초기 마이그레이션 | ⏸️ 보류 (PostgreSQL/Railway 환경 필요) |
| 프론트엔드 | ⬜ 미착수 (전체) |

**테스트: 33개 전부 통과** (`cd backend; uv run pytest -q`)

---

## ▶ 다음 세션 시작 지점 (game 구현)

오작교/붉은실 **설계 확정·스펙 갱신·커밋 완료**. 남은 건 구현뿐.

**바로 할 일:** `writing-plans`로 game 구현계획 → TDD 구현.

확정된 설계 요약 (상세는 스펙 §5.3·§6):
- **오작교** `POST /game/ojakgyo` (active) — 지목자 + 두 사람(이름+학교) 저장, 익명.
  검증: 본인 ∉ {person_a,b}(400) / person_a≠person_b(400) / 같은 지목자·같은 쌍 중복 409. 쌍 순서무관 정규화. 가입검증 안 함.
  ⚠️ **`Ojakgyo` 모델 필드 교체 필요**: referrer_id/referee_id/invite_token → recommender_id + person_a_name/university + person_b_name/university.
- **붉은실** (active):
  - `POST /game/red-thread` — target(이름+학교) 입력/수정(1명·덮어쓰기). self 400.
  - `GET /game/red-thread` — 내 현재 입력 조회.
  - `GET /game/red-thread/received` — 나를 지목한 인원수 `{count:N}` (익명).
  - `RedThread` 모델 변경 없음 (스펙대로).
- **공통**: 확률/상호매칭 적용 전부 보류(매칭 알고리즘 영역) — 저장·집계·알림까지만.
- 모델 필드 교체 시 `app/models/__init__.py` re-export 영향 없음(클래스명 유지).

---

## 완료된 백엔드 엔드포인트

```
POST /auth/register              ✅
POST /auth/login                 ✅
GET  /me                         ✅
PUT  /me/profile                 ✅
PUT  /me/matching-pause          ✅
GET  /me/survey                  ✅  ← 설문 답변 조회 (없으면 빈 {})
PUT  /me/survey                  ✅  ← 설문 답변 저장 (freeform JSON)
POST /reports                    ✅  ← 신고 (target_id, reason)
POST /verification/upload        ✅  ← 학생증 업로드
GET  /admin/verifications        ✅  ← 관리자: 승인 대기 목록
POST /admin/verifications/{id}   ✅  ← 관리자: 승인/거절
```

## 미구현 엔드포인트 (스펙 §9 기준)

```
POST /game/ojakgyo               ⬜ 두 사람(이름+학교) 지목 중매
POST /game/red-thread            ⬜ 붉은 실 입력/수정 (1명, 덮어쓰기)
GET  /game/red-thread            ⬜ 내 붉은 실 입력 조회
GET  /game/red-thread/received   ⬜ 나를 지목한 인원수 (익명)
POST /admin/match/run            🚫 매칭 실행 (알고리즘 보류)
GET  /admin/matches              🚫 매칭 결과
```

---

## 다음 작업 후보 (우선순위)

1. **game 엔드포인트** — 오작교/붉은실 (설계 확정 2026-06-04, 스펙 §6 갱신됨).
   - ⚠️ `Ojakgyo` 모델 필드 전면 교체 필요 (referrer/referee/invite_token → recommender_id + person_a/b name·university). 중매 모델로 재설계됨.
   - `RedThread` 모델은 스펙대로 변경 없음.
   - "매칭 확률/상호매칭 반영"은 매칭 알고리즘 미결 → *지목/입력 저장·집계·알림까지만*. 확률 적용 보류.
2. **프론트엔드 Plan 2** — 기반 세팅 + 인증 플로우 화면 (백엔드 있는 기능만 연동).

> 매칭(match)은 CLAUDE.md 금지 항목. 건드리지 말 것.

---

## 기록된 설계 결정

- **설문 저장 = freeform JSON** (검증 안 함). 이유: 매칭 알고리즘 미결이라 "유효한 답"의 기준이 아직 없음. 빡센 검증은 시기상조(YAGNI). 회의에서 뽑은 질문 리스트는 **프론트(설문 화면)**가 보유. 매칭 설계 시작할 때 검증/가중치 같이 정의.
- 설문 질문 리스트 확정돼도 **DB 스키마/마이그레이션 영향 없음** (answers가 JSON blob).
- `GET /me/survey`는 스펙엔 없지만 마이페이지 "설문 수정" 화면 prefill 위해 추가함.

---

## 작업 방식 메모

- 작은 백엔드 기능 = TDD 직접 (superpowers `test-driven-development` 우선).
- 큰 기능(다파일) = `writing-plans` → `subagent-driven-development`.
- 테스트 명령: `cd backend; uv run pytest -q`
- 커밋 형식: `<prefix>(<scope>): <한국어 제목>` + `Co-Authored-By`.
