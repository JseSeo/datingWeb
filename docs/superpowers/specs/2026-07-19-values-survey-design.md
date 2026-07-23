# 가치관 설문 — 설계안 (design doc)

**작성: 2026-07-19 · 상태: 🟡 검토 요망 (brainstorming 산출물)**
**출처 기록: `docs/superpowers/RESUME-survey.md`**

---

## 1. 목표 · 범위

프론트 `/survey` 페이지 구축. 설문을 **본인(self) / 매칭 상대 선호(partner)** 두 섹션으로 분리하고, **절대질문**(최대 2개, "이것만은 포기 못함") 기능 포함.

**범위 밖 (건드리지 않음):**
- ⛔ **매칭 알고리즘** — 스펙 §5.2, 보류. "매칭 알고리즘 설계 시작해" 명령 전까지 금지. 설문은 **데이터 구조만** 생성.
- 백엔드 저장소(`Survey.answers: JSON`, `GET/PUT /me/survey`)는 이미 존재. 재사용.

**이 설계가 만드는 변경:**
1. 프론트 `/survey` 페이지 + 질문 카탈로그 상수 파일
2. `User.gender` 신규 컬럼 (+ Register 폼 + 마이그레이션)
3. 백엔드 `PUT /me/survey` **얕은 구조 검증** 추가

---

## 2. 확정 결정 요약 (Q1~Q6)

| # | 결정 |
|---|------|
| Q1 | 성별 = **가입 시 수집**. `User.gender` 신규 + Register 폼 |
| Q5 | 성별 값 = **남/여 2개만** (기타/거부 없음) |
| Q2 | 질문 카탈로그 = **프론트 코드 정의(정적)**. `frontend/src/pages/Survey/questions.ts`. 백엔드는 제네릭 JSON 유지 |
| Q3 | 백엔드 검증 = **얕게**. 구조 규칙만, 카탈로그 사본 없음 |
| Q4 | 완료 기준 = **응답가능 전 문항 필수**(남자국한은 여성 제외). 부분저장 허용 |
| Q6 | 얼굴상 = **사진+00상 선택지**. 목록 TBD(에셋 의존). 본인=단일 / 상대=복수+상관없음 |

---

## 3. 데이터 shape — `answers` JSON (확정)

```json
{
  "responses": { "<질문id>": <값>, ... },
  "absolute":  ["<질문id>", "<질문id>"]
}
```

- `responses` 값 타입은 문항 타입에 따름 (아래 §6 타입표).
- `absolute` = 절대질문 id 배열. **최대 2개. partner 문항만. "상관없음" 선택 문항은 불가.**
- 섹션/타입/선택지/남자국한/이미지 = **프론트 카탈로그에만** 정의. `answers`엔 값만.

---

## 4. `User.gender` 추가

| 항목 | 내용 |
|------|------|
| 컬럼 | `gender: Mapped[str]` — `Enum("male","female", name="gender")`, `nullable=False` |
| Register | 프론트 폼에 성별 라디오(남/여) 추가. 백엔드 `RegisterRequest`에 `gender` 필수 필드 |
| 마이그레이션 | 신규 alembic revision (현 baseline `8ed1fb6` = 전체 스키마 위에) |
| 조건부 렌더 | 남자국한 문항 = `gender=="male"`만 노출. 여성은 응답가능 문항에서 제외 |

**⚠️ 영향 범위:** `User` 모델 + `RegisterRequest` 스키마 + register 엔드포인트 + 프론트 Register 폼 + register 테스트. (PR#8 동의 체크박스와 같은 파일 겹침 → 머지 순서 조율 필요.)

---

## 5. 백엔드 얕은 검증 (`PUT /me/survey`)

카탈로그 사본 없이 **구조 규칙만**. 어긋나면 `400`.

| 규칙 | 내용 |
|------|------|
| 최상위 | `answers` = `{responses: dict, absolute: list}` 형태 |
| absolute 타입 | list이고 원소는 문자열 |
| absolute 개수 | **≤ 2** |
| absolute 정합 | `absolute`의 모든 id가 `responses`의 key에 존재 |

**검증 안 하는 것:** 문항 id 유효성, 값 타입, 완료 여부, self/partner 구분, 남자국한 — 전부 프론트 책임(카탈로그가 프론트에만 있으므로). 완료 여부는 매칭 참여 시점에 별도 판정(매칭 보류라 지금은 미구현).

---

## 6. 질문 카탈로그 — ✅ 확정 (45문항, 2026-07-23 리뷰 완료)

> 문항별 리뷰 완료. self/partner 쌍 = 매칭(`A.self ↔ B.pref`) 고려해 확정. MBTI 제거.

**타입 정의:**

| 타입 | 값 shape | 비고 |
|------|----------|------|
| `single` | 선택지 id 1개 | 라디오 |
| `multi` | 선택지 id 배열 | 체크박스 |
| `scale` | 1~5 정수 | 척도 |
| `number` | 정수 | 예: 키 cm |
| `range` | `[min,max]` 정수 | 예: 상대 키 범위 |
| `ranking` | 항목 id 순서 배열 | 드래그 정렬 |
| `image-single` | 선택지 id 1개 | 얼굴상(본인) |
| `image-multi` | 선택지 id 배열 | 얼굴상(상대) |

**섹션 = self(본인) / partner(상대 선호). 절대질문 = partner만 가능.**
상대 문항의 "상관없음"은 대부분 선택지에 포함(선택 시 그 문항은 절대질문 불가).

**UI 규칙(전역):** 모든 복수선택 문항(`multi` · `image-multi`)은 질문 밑에 **"복수 선택 가능"** 안내문 표시.

### 6.1 외모 · 스타일

| id | 섹션 | 질문 | 타입 | 선택지 | 남자국한 |
|----|------|------|------|--------|:---:|
| `height_self` | self | 내 키 | number(cm) | — | |
| `height_pref` | partner | 원하는 상대 키 | single | ~165 / 165~175 / 175~185 / 185↑ / 상관없음 (5개) | |
| `face_self` | self | 내 얼굴상 | image-single | (TBD 이미지) | |
| `face_pref` | partner | 원하는 상대 얼굴상 | image-multi + 상관없음 | (TBD 이미지) | |
| `style_self` | self | 내 스타일 | multi | 캐주얼/포멀/스트릿/미니멀/빈티지 | |
| `style_pref` | partner | 원하는 상대 스타일 | multi + 상관없음 | 위와 동일 | |
| `tattoo_self` | self | 내 문신 여부 | single | 있음/없음 | |
| `tattoo_pref` | partner | 문신 선호 | single | 있어도됨/없었으면/상관없음 | |
| `piercing_self` | self | 내 피어싱 여부 | single | 있음/없음 | |
| `piercing_pref` | partner | 피어싱 선호 | single | 있어도됨/없었으면/상관없음 | |
| `grooming_self` | self | 외모관리 습관 | multi | 로션/썬크림/머리손질/화장/손톱관리 | **✔** (여성 제외 확정) |

### 6.2 가치관 · 신념

| id | 섹션 | 질문 | 타입 | 선택지 |
|----|------|------|------|--------|
| `politics_self` | self | 정치 성향 | single | 진보/중도/보수/모름 |
| `politics_pref` | partner | 상대 정치 성향 | single | 진보/중도/보수/상관없음 |
| `religion_self` | self | 종교 | single | 무교/기독교/천주교/불교/기타 |
| `religion_pref` | partner | 상대 종교 | multi + 상관없음 | 기독교/천주교/불교/무교 |

### 6.3 관계 · 감정

| id | 섹션 | 질문 | 타입 | 선택지 |
|----|------|------|------|--------|
| `contact_freq_self` | self | 내 연락 빈도 성향 | scale | 1(가끔)~5(자주) |
| `contact_freq_pref` | partner | 원하는 상대 연락 빈도 | scale | 1(가끔)~5(자주) |
| `date_freq_self` | self | 내 데이트 빈도 성향 | scale | 1~5 |
| `date_freq_pref` | partner | 원하는 상대 데이트 빈도 | scale | 1~5 |
| `alone_time_self` | self | 내 개인시간 필요 정도 | scale | 1(적음)~5(많음) |
| `alone_time_pref` | partner | 원하는 상대 개인시간 필요 정도 | scale | 1(적음)~5(많음) |
| `affection_self` | self | 내 애정표현 정도 | scale | 1(은은)~5(적극) |
| `affection_pref` | partner | 원하는 상대 애정표현 정도 | scale | 1(은은)~5(적극) |
| `conflict_style_self` | self | 내 갈등 시 반응 | single | 즉시품/시간두고/혼자삭힘 |
| `conflict_style_pref` | partner | 원하는 상대 갈등 반응 | single | 즉시품/시간두고/혼자삭힘/상관없음 |
| `priority_rank_self` | self | 내 인생 우선순위 | ranking | 연인/친구/자기개발/가족 |
| `priority_rank_pref` | partner | 원하는 상대 우선순위 | ranking | 연인/친구/자기개발/가족 |

### 6.4 경제 · 생활 · 건강

| id | 섹션 | 질문 | 타입 | 선택지 |
|----|------|------|------|--------|
| `date_budget_self` | self | 내 1회 데이트 예산 | single | 5만↓/5~10/10~20/20~30/30↑ |
| `date_budget_pref` | partner | 원하는 상대 예산 | single | 5만↓/5~10/10~20/20~30/30↑/상관없음 |
| `cost_share_self` | self | 내 비용부담 선호 | single | 더치/번갈아/여유쪽더/내가전담 |
| `cost_share_pref` | partner | 원하는 상대 비용부담 | single | 더치/번갈아/여유쪽더/상대전담/상관없음 |
| `smoking_self` | self | 내 흡연 | single | 비흡연/가끔/흡연 |
| `smoking_pref` | partner | 상대 흡연 선호 | single | 비흡연만/가끔OK/상관없음 |
| `drinking_self` | self | 내 음주 빈도 | single | 안함/가끔/자주 |
| `drinking_pref` | partner | 상대 음주 선호 | single | 안함/가끔OK/상관없음 |
| `exercise_self` | self | 내 운동 빈도 | single | 안함/주1~2/주3↑ |
| `exercise_pref` | partner | 상대 운동 선호 | single | 안함/주1~2/주3↑/상관없음 |
| `sleep_self` | self | 내 수면 패턴 | single | 아침형/올빼미/불규칙 |
| `sleep_pref` | partner | 상대 수면 선호 | single | 아침형/올빼미/불규칙/상관없음 |
| `hobby_self` | self | 내 취미 성향 | single | 실내/실외/둘다 |
| `hobby_pref` | partner | 상대 취미 선호 | single | 실내/실외/상관없음 |
| `residence_self` | self | 내 거주지 | single | 시/도 17개 (하드코딩) |
| `residence_pref` | partner | 허용 이동거리 | single | 차로 1시간↓/2시간↓/3시간↓/상관없음 |
| `living_self` | self | 내 자취 여부 | single | 자취/본가/기숙사 |
| `living_pref` | partner | 상대 자취 선호 | single | 자취선호/상관없음 |

---

## 7. 얼굴상 (face type) 상세

- 선택지 = **`{id, label:"00상", image: 에셋경로}`** 배열. 카탈로그 문항에 `image` 필드.
- **본인(`face_self`) = 단일(image-single). 상대(`face_pref`) = 복수 + "상관없음"(image-multi).**
- **목록·이미지 미확정(TBD)** — 추후 AI생성 or 실사진. 구현 시 placeholder 에셋으로 개발, 확정 목록 교체.
- → §11 미결 + CLAUDE.md "운영 전 교체 필수"에 추가.

---

## 8. 절대질문 UI 규칙

| 규칙 | 내용 |
|------|------|
| 위치 | **partner 섹션 문항에만** 별(★)/체크 토글 노출 |
| 최대 | **2개**. 2개 선택되면 나머지 토글 비활성 |
| 금지 | 값이 "상관없음"인 문항은 절대질문 불가(토글 숨김/비활성) |
| 저장 | 선택된 문항 id → `answers.absolute` 배열 |
| 의미 | 매칭 시 데드라인(반드시 충족). **매칭 로직은 지금 미구현** — 데이터만 저장 |

---

## 9. 프론트 페이지 구조

```
frontend/src/pages/Survey/
  index.tsx        # 페이지: 섹션 탭/스텝, 진행률, 저장
  questions.ts     # 카탈로그 상수 (§6) — 단일 진실원
  types.ts         # Question/Answer 타입
  faceTypes.ts     # 얼굴상 선택지 (TBD placeholder)
```

- 라우팅: 스펙 §7 `/survey`. active 유저 접근.
- 흐름: self 섹션 → partner 섹션(+절대질문) → 저장. 부분저장(중간 이탈 후 재개, `PUT`이 통째 교체).
- 진행률: 응답가능 문항 대비 응답 수(남자국한은 여성이면 분모 제외).
- 검증: 프론트가 타입/필수/남자국한/절대질문 규칙 담당. 백엔드는 §5 얕은 검증만.

---

## 10. 마이그레이션 · 영향

- `User.gender` = 새 alembic revision (baseline `8ed1fb6` 위). Enum `gender` 타입 생성.
- register 경로 전부 영향(모델/스키마/엔드포인트/프론트폼/테스트) — Task 분리 시 인지.
- 검증 명령: 백 `uv run pytest -v` / 프론트 `npm run test`, `npx tsc --noEmit`, `npm run build`.

---

## 11. 미결 · TBD

| 항목 | 상태 |
|------|------|
| 얼굴상 목록·이미지 | **TBD, 에셋 의존.** 운영 전 교체 필수 |
| ~~거주지 선택지~~ | ✅ 해결: 시/도 17개 행정표준 = 하드코딩. `residence_pref`는 이동시간 버킷 |
| ~~카탈로그 문항 전체~~ | ✅ 해결: §6 리뷰 완료(45문항 확정). MBTI 제거 |
| PR#8 (동의 체크박스) | 미머지. gender 추가와 register 파일 겹침 → 머지 순서 조율 |

---

## 12. 다음 단계

design doc 검토(사용자) → 확정 반영 → **writing-plans** → subagent-driven 구현.
```
brainstorming(완료) → design doc(현재, 검토대기) → writing-plans → 구현
```
