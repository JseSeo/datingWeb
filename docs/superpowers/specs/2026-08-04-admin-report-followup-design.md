# 관리자 신고 조회 후속 정리 — 설계안 (design doc)

**작성: 2026-08-04 · 상태: 🟡 검토 요망 (brainstorming 산출물)**
**선행: `2026-08-03-admin-report-review-design.md` / PR #12 (머지됨, main `f6d9c73`)**

---

## 1. 목표 · 범위

PR #12 전체-브랜치 리뷰에서 "머지 후 처리"로 분류된 Minor 9건 중 **상위 3건**을 처리한다.

**다루는 항목:**

| 항목 | 문제 | 성격 |
|---|---|---|
| **M4** | `handle_report`의 admin 게이트에 테스트가 없다 | 회귀 방어 |
| **M3** | `created_at`을 UTC 원문 그대로 출력해 실제 시각과 9시간 어긋난다 | 데이터 정확성 |
| **M1 + M8** | 탭 결합 후 제목이 비대칭이고, 탭 버튼에 ARIA 롤이 없다 | 구조·접근성 |

**범위 밖 (다음 기회):**

- M2 — 탭 바 시각적 이음매. **조사 결과 실재하지 않는다:** `global.css:6`에서 `body`가 이미 `--color-bg: #FFF5E6`이라 `.wrap`의 `background: #FFF5E6`은 같은 색 재선언이다. 색 차이로 인한 이음매가 없다
- M6 — 구 스펙 `2026-08-02-report-suggestion-design.md` §7 문구 갱신. 문서만이라 나중에 몰아서
- M7 — `admin_router` prefix 관례 통일. 동작 문제 없음
- M9 — 재조회 중 "불러오는 중…"과 stale 목록 동시 렌더. 로컬 API라 체감 없음
- M5 — 리뷰에서 "고칠 필요 없음"으로 이미 판정 (탈퇴는 행 유지 익명화 + `reporter_id` NOT NULL FK라 도달 불가)
- ⛔ 매칭 알고리즘

---

## 2. 확정 결정 요약

| # | 질문 | 결정 |
|---|------|------|
| Q1 | UTC 문제를 어디서 고칠까? | **프론트 헬퍼에서 `Z`를 붙여 해석.** 백엔드 무수정 |
| Q2 | 날짜 표시 형식 | **`2026-08-04 02:01`** (고정폭 숫자) |
| Q3 | 관리자 페이지 h1 구조 | **`Admin.tsx`에 `<h1>관리자</h1>` 하나.** 두 탭의 h1 제거, 탭 라벨이 부제 역할 |
| Q4 | 브랜치·커밋 | **브랜치 1개(`feat/admin-report-followup`), 커밋 3개** |
| Q5 | 작업 순서 | **M4 → M3 → M1+M8** |
| Q6 | ARIA 범위 | `tablist`/`tab`/`aria-selected`/`tabpanel`까지. 화살표 키 이동·로빙 tabindex는 제외 |

### Q1 근거

백엔드는 `datetime.utcnow()`로 **naive** UTC를 저장한다. Pydantic 직렬화 결과에 타임존 suffix가 없다 (`2026-08-03T17:01:59.776396`).

여기서 흔한 함정: 프론트에서 `new Date(iso)`만 하면 자바스크립트는 offset 없는 ISO 문자열을 **로컬 시간으로 해석**한다. 따라서 `toLocaleString()`을 붙여도 여전히 9시간 틀린 값이 나온다. 포맷만 개선되고 버그는 남는다. **"이건 UTC다"라는 명시가 반드시 필요하다.**

대안이었던 "백엔드를 tz-aware로" 안은 근본 해결이지만 `Report` 외 5개 모델·기존 DB 행·테스트까지 번진다. 게다가 SQLite/PostgreSQL 컬럼이 `DateTime`(= `TIMESTAMP WITHOUT TIME ZONE`)이라 **이미 저장된 행은 여전히 naive로 읽힌다** — 결국 읽는 쪽 처리가 어딘가엔 남는다. Minor 1건 치고 과하다.

프론트 헬퍼 한 파일에 `Z` 로직을 가두면, 나중에 백엔드를 tz-aware로 옮기고 싶어질 때 그 파일 하나만 고치면 된다.

### Q3 배경

`created_at`은 6개 타입에 존재하지만 **화면에 출력한 전례가 없다.** `ReportTab.tsx:72`가 프로젝트 최초 날짜 표시다. 여기서 정하는 방식이 이후 마이페이지 가입일·학생증 신청일 등의 관례가 된다.

---

## 3. 작업 단위

브랜치 `feat/admin-report-followup` (main `f6d9c73`에서 분기), 커밋 3개. 세 항목은 파일이 겹치지 않아 순서 교환 시에도 충돌이 없다.

| 커밋 | 항목 | 파일 |
|---|---|---|
| 1 | M4 | `backend/tests/test_admin_reports.py` |
| 2 | M3 | `frontend/src/lib/datetime.ts` (신규), `frontend/src/lib/datetime.test.ts` (신규), `ReportTab.tsx`, `ReportTab.test.tsx` |
| 3 | M1+M8 | `Admin.tsx`, `VerificationTab.tsx`, `Admin.test.tsx` |

프로젝트 규칙(`superpowers:test-driven-development` 우선)에 따라 각 커밋은 실패하는 테스트를 먼저 쓰고 구현한다.

---

## 4. M4 — handle 게이트 테스트

`test_admin_reports.py`에 2개 추가. 기존 `test_list_forbidden_for_normal_user` / `test_list_unauthorized`와 대칭 구조다.

```python
def test_handle_forbidden_for_normal_user(client: TestClient):
    headers = _reporter_headers(client, "normal2@test.com")
    report_id = _make_report(client, headers)
    res = client.post(f"/admin/reports/{report_id}/handle", headers=headers)
    assert res.status_code == 403


def test_handle_unauthorized(client: TestClient):
    headers = _reporter_headers(client, "normal3@test.com")
    report_id = _make_report(client, headers)
    res = client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 401
```

**존재하는 report id를 쓰는 이유:** 없는 id로 테스트하면 403이 나와도 그것이 권한 때문인지 확인할 수 없다. 실제 구현에서는 의존성이 먼저 평가되어 403이 404보다 우선하지만, 테스트가 그 평가 순서에 의존하지 않도록 실재하는 id를 쓴다.

**왜 필요한가:** 현재 `require_admin` 의존성은 코드에 있으나 테스트가 검증하지 않는다. 리팩터링 중 그 한 줄이 사라져도 백엔드 테스트 106개가 전부 통과한다. 그 경우 일반 유저가 임의의 신고를 처리 완료로 바꿀 수 있다.

---

## 5. M3 — KST 날짜 표시

### 5.1 신규 모듈 `frontend/src/lib/datetime.ts`

```ts
export function formatKST(iso: string): string
```

동작:

1. 문자열 끝에 타임존 표시가 없으면 `Z`를 붙인다 — 서버가 UTC로 저장하므로.
   판정 기준은 **끝부분이 `Z` 또는 `±HH:MM` 형태인가**로 한정한다 (`/(Z|[+-]\d{2}:\d{2})$/`).
   날짜 부분의 `-`(예: `2026-08-03`)를 offset으로 오인하지 않기 위해 반드시 끝 위치에 고정한다
2. `Intl.DateTimeFormat`을 `timeZone: "Asia/Seoul"`로 사용해 년/월/일/시/분 조각을 뽑는다
3. `YYYY-MM-DD HH:mm` 형태로 직접 조립한다
4. 파싱 실패(Invalid Date)면 **원문을 그대로 반환**한다 — 정보를 잃는 것보다 낫다

**`toLocaleString`을 쓰지 않는 이유:** 로케일과 브라우저 구현에 따라 구분자·자릿수가 달라져 `2026-08-04 02:01` 고정 형식이 보장되지 않는다. 조각을 뽑아 직접 조립하면 실행 환경과 무관하게 동일한 결과가 나오고 테스트도 안정적이다.

### 5.2 테스트 `frontend/src/lib/datetime.test.ts`

| 케이스 | 입력 | 기대 |
|---|---|---|
| UTC → KST, 날짜 넘어감 | `2026-08-03T17:01:59.776396` | `2026-08-04 02:01` |
| 이미 `Z` 붙은 입력 (중복 방지) | `2026-08-03T17:01:59Z` | `2026-08-04 02:01` |
| 자정 경계 | `2026-08-03T15:00:00` | `2026-08-04 00:00` |
| 잘못된 입력 | `어제` | `어제` (원문 반환) |

### 5.3 호출부

`ReportTab.tsx:72` — `{r.created_at}` → `{formatKST(r.created_at)}`

`ReportTab.test.tsx` — 현재 날짜를 단언하는 테스트가 하나도 없다. 기존 목데이터 `created_at: "2026-08-03T14:30:00"`에 대해 화면에 `2026-08-03 23:30`이 나오는지 단언 1개를 추가한다.

---

## 6. M1 + M8 — 헤딩 · 탭 시맨틱

### 6.1 변경

- **`Admin.tsx`**: `<h1 className={styles.title}>관리자</h1>` 추가. `.title` 클래스는 `Admin.module.css`에 이미 존재하므로 신규 CSS 없음
- **`VerificationTab.tsx:99`**: `<h1 className={styles.title}>학생증 심사</h1>` 삭제
- **`Admin.tsx` 탭 바**: `role="tablist"`, 각 버튼에 `role="tab"` + `aria-selected`, 탭 내용 래퍼에 `role="tabpanel"` + `id`/`aria-controls` 한 쌍

### 6.2 ARIA 범위 판단

**포함:** `tablist` / `tab` / `aria-selected` / `tabpanel` + `aria-controls` 연결

**제외:** 좌우 화살표 키보드 이동, 로빙 tabindex

완전한 ARIA 탭 패턴은 화살표 키 이동까지 요구한다. 그러나 탭이 2개뿐이라 Tab 키만으로 모두 도달 가능하고, 로빙 tabindex를 도입하면 상태 관리 코드가 눈에 띄게 늘어난다. 반대로 `role="tab"`만 넣고 `role="tabpanel"`을 생략하면 스크린리더에 "탭인데 연결된 패널이 없는" 반쪽 상태가 된다. 위 조합이 완결되는 최소 단위다.

### 6.3 기존 테스트 영향

- **`Admin.test.tsx:23`이 깨진다.** 현재 `getByRole("button", { name: "신고 · 건의" })`인데 `role="tab"`을 붙이면 더 이상 button 롤이 아니다. `getByRole("tab", ...)`으로 바꾸고, 클릭 후 `aria-selected`가 뒤바뀌는지 단언을 추가한다
- **`VerificationTab.test.tsx`는 안 깨진다.** h1을 단언하는 테스트가 없음을 확인했다

---

## 7. 검증 기준

| 항목 | 기대 |
|---|---|
| `cd backend && uv run pytest` | 108 passed (기존 106 + 2) |
| `cd frontend && npm run test` | 신규 5개 (datetime 4 + ReportTab 날짜 1), Admin ARIA 단언 추가 |
| `npx tsc --noEmit` | 무에러 |
| `npm run build` | 성공 |
| 브라우저 `/admin` | h1 "관리자" 1개, 신고 카드 날짜가 `2026-08-04 02:01` 꼴 |

---

## 8. 미결 · 후속

- M2 / M6 / M7 / M9 — 위 §1 "범위 밖" 참조
- 날짜 표시가 다른 화면으로 확산되면(마이페이지 가입일 등) `formatKST` 재사용. 그 시점에 백엔드 tz-aware 전환을 재검토할 수 있다
