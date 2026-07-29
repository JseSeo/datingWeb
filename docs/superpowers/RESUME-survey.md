# 가치관 설문 — 진행 기록 + 재개

> **다음 세션 재개 명령:**
> `RESUME-survey.md 읽고 이어서`

**최종: 2026-07-27**
**상태: 🟢 구현 완료(9/9 Task). subagent-driven 실행 + final review(opus) = Ready to merge. 미머지, 사용자 허락 대기.**

## 구현 결과 (2026-07-27)
- plan: `docs/superpowers/plans/2026-07-26-values-survey.md`
- 브랜치 `feat/values-survey`: 10 코드커밋 (4be8716..fca7b45). 백 93 / 프론트 76 pass, tsc/build clean.
- BE: User.gender(필수, male/female) + alembic(f791f9b09268) + PUT /me/survey 얕은검증(400).
- FE: 성별 라디오, Survey 타입/얼굴상 placeholder/API, 카탈로그 45문항, QuestionField 렌더러, /survey 페이지+라우트.
- Final review: Critical/Important 0. Minor 전부 follow-up.
- **다음 = 브랜치 마무리(머지/PR — 사용자 허락 필수).**

### follow-up (비차단, ship 전/운영 전)
- 얼굴상 placeholder 에셋 교체(운영 전).
- migration server_default="male" → 기존 유저 male 백필 → 매칭 운영 전 성별 재확인.
- QuestionField ranking/number/image 테스트 커버리지 추가.
- Register/Survey 무스타일 블록(styles.gender/consent 미정의) 시각 폴리시.

---
## (아래는 계획 단계 기록 — 보존)

**과거 상태: design doc 리뷰 완료(45문항 확정).**

---

## 목표
프론트 `/survey` 페이지 구축. self(본인)/partner(상대 선호) 분리 + 절대질문(최대 2). 백엔드 저장소(`GET/PUT /me/survey`, `Survey.answers: JSON`)는 기존 재사용.
**⚠️ 매칭 알고리즘은 금지·보류.** 설문은 데이터 구조만.

---

## ✅ 완료된 것

### 1. 브랜치 정리 (2026-07-23)
- **PR#8(가입 동의 체크박스) squash 머지 완료** → main. 원격 브랜치 유지.
- 로컬 main = origin/main 정렬(중복 커밋 decea02 + 머지커밋 리셋).
- **새 브랜치 `feat/values-survey`** = 깨끗한 main 위 분기. 설문 작업은 여기서.

### 2. design doc 리뷰 완료 → 45문항 확정
`specs/2026-07-19-values-survey-design.md` 커밋됨. 문항별 리뷰로 §6 카탈로그 확정:

| 섹션 | 문항 | 주요 결정 |
|----|:-:|----|
| §6.1 외모·스타일 | 11 | height_pref=버킷5(~165/165~175/175~185/185↑/상관없음), tattoo_self·piercing_self 추가, grooming_self 남자국한(여성 제외) |
| §6.2 가치관·신념 | 4 | 유지(정치·종교). **복수선택 문항 전부 "복수 선택 가능" 안내문** |
| §6.3 관계·감정 | 12 | 6문항 전부 self/partner 쌍 |
| §6.4 경제·생활·건강 | 18 | self/partner 쌍. 거주지=시/도17 하드코딩. residence_pref=이동시간 버킷(차로 1/2/3시간↓/상관없음) |
| ~~MBTI~~ | 0 | **제거** |

**핵심 원칙:** 매칭이 `A.self ↔ B.pref` 양방향 비교 → 속성마다 self+pref 쌍 필요.

### 확정 데이터 shape
```json
{ "responses": { "<id>": <값> }, "absolute": ["<id>", "<id>"] }
```
absolute = partner 문항만, 최대 2, "상관없음" 선택 문항 불가.

---

## ⬜ 남은 미결 (1개)
- **얼굴상(face) 목록·이미지 = TBD, 에셋 의존.** placeholder로 개발 → 운영 전 교체. (§7, CLAUDE.md 운영전교체 항목)

## ✅ 확정 (재론 불필요)
- 데이터 shape(§3), User.gender 남/여(§4), 백엔드 얕은 검증(§5), 절대질문 UI(§8), 페이지 구조(§9).

---

## 다음 단계
**`writing-plans`** → 구현 계획 작성 → subagent-driven 구현.

**구현 주의:**
- `User.gender` 추가 = User 모델 + RegisterRequest + register 엔드포인트 + 프론트 Register 폼 + register 테스트. **새 alembic revision**(현 baseline = PR#8 머지 후 최신).
- 프론트 카탈로그 = `frontend/src/pages/Survey/questions.ts` 단일 진실원. 백엔드는 제네릭 JSON 유지.
- 완료 기준 = 응답가능 전 문항 필수(grooming_self는 여성 제외). 부분저장 허용.

## 환경 메모
- 백 테스트: `cd backend && uv run pytest -v` / 프론트: `cd frontend && npm run test`, `npx tsc --noEmit`, `npm run build`
- 마이그레이션: `uv run alembic revision --autogenerate -m "..."` → `uv run alembic upgrade head`
- git 머지/push/PR = 사용자 허락 필수. 매칭 알고리즘 = 명령 전까지 금지.
