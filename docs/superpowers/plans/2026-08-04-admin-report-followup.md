# 관리자 신고 조회 후속 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR #12 리뷰에서 "머지 후 처리"로 분류된 Minor 3건(M4 / M3 / M1+M8)을 해결한다.

**Architecture:** 세 항목은 서로 파일이 겹치지 않는 독립 작업이다. Task 1은 기존 `require_admin` 게이트를 고정하는 백엔드 테스트만 추가하고 프로덕션 코드를 건드리지 않는다. Task 2는 프론트에 날짜 포맷 헬퍼를 신규 도입해 UTC→KST 변환을 한 파일에 가둔다. Task 3은 관리자 페이지 헤딩을 탭 컨테이너로 올리고 탭 바에 ARIA 롤을 붙인다.

**Tech Stack:** FastAPI + pytest (backend) / React 18 + TypeScript + Vite + Vitest + @testing-library/react (frontend)

## Global Constraints

- 설계 문서: `docs/superpowers/specs/2026-08-04-admin-report-followup-design.md` — 충돌 시 스펙이 진실
- 브랜치: `feat/admin-report-followup` (main `f6d9c73`에서 분기). 이미 생성되어 있고 스펙 커밋 `27b4773`이 올라가 있다
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + 본문 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 디자인 토큰: 크림 `#FFF5E6`, 코랄 `#FF7F5C`, 보조 `#FF9472`, 기준 너비 `max-width: 390px`. 이 외 색상 사용 금지
- 백엔드 테스트 실행: `cd backend && uv run pytest`
- 프론트 테스트 실행: `cd frontend && npm run test`
- 요청하지 않은 기능 추가 금지 (YAGNI). 범위 밖 항목(M2/M5/M6/M7/M9)은 건드리지 않는다
- 인접 코드 "개선" 금지. 이 계획이 지정한 줄만 수정한다

---

### Task 1: M4 — `handle_report` admin 게이트 테스트

**Files:**
- Modify: `backend/tests/test_admin_reports.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: `backend/tests/conftest.py`의 `client` fixture (인증 없는 `TestClient`), 같은 파일의 헬퍼 `_reporter_headers(client, email=..., name=..., university=...) -> dict` 와 `_make_report(client, headers, reason=...) -> int`
- Produces: 없음 (테스트만 추가)

**배경:** `POST /admin/reports/{id}/handle`에는 `require_admin` 의존성이 걸려 있으나 이를 검증하는 테스트가 없다. 지금 그 한 줄을 지워도 백엔드 테스트 106개가 전부 통과한다. 즉 일반 유저가 임의의 신고를 처리 완료로 바꿀 수 있게 되어도 아무도 못 잡는다. `GET /admin/reports` 쪽은 `test_list_forbidden_for_normal_user` / `test_list_unauthorized`로 이미 고정되어 있으므로 그 둘과 대칭이 되게 만든다.

**주의:** 이 태스크는 프로덕션 코드가 이미 올바르므로 **테스트가 처음부터 통과한다.** 일반적인 TDD의 "실패하는 테스트 먼저"가 성립하지 않는다. 대신 Step 3에서 프로덕션 코드를 일시적으로 망가뜨려 테스트가 실제로 그 결함을 잡는지 확인한 뒤 되돌린다. 이 확인을 건너뛰면 아무것도 검증하지 않는 테스트를 남길 위험이 있다.

- [ ] **Step 1: 테스트 2개 추가**

`backend/tests/test_admin_reports.py` 파일 맨 끝(현재 133번째 줄 `assert res.status_code == 401` 다음)에 붙여넣는다:

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

**존재하는 report id를 쓰는 이유:** 없는 id(예: 99999)로 테스트하면 403이 나와도 그것이 권한 검사 때문인지 확인할 수 없다. 실제 구현에서는 의존성이 먼저 평가되어 403이 404보다 우선하지만, 테스트가 그 평가 순서에 의존하지 않도록 실재하는 id를 쓴다.

**`admin_client`가 아니라 `client` fixture를 쓰는 이유:** `admin_client`는 이미 관리자 토큰이 헤더에 박혀 있어서 권한 거부를 테스트할 수 없다.

- [ ] **Step 2: 테스트 실행 — 통과 확인**

Run: `cd backend && uv run pytest tests/test_admin_reports.py -v`
Expected: PASS. 총 12 passed (기존 10 + 신규 2)

- [ ] **Step 3: 뮤테이션 확인 — 테스트에 실효성이 있는지 검증**

`backend/app/api/reports.py:93`의 `require_admin` 의존성을 **일시적으로** 무력화한다. 아래처럼 `require_admin` → `get_current_user`로 바꾼다:

```python
@admin_router.post("/{report_id}/handle", response_model=AdminReportOut)
def handle_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
```

Run: `cd backend && uv run pytest tests/test_admin_reports.py::test_handle_forbidden_for_normal_user -v`
Expected: **FAIL** — `assert 200 == 403`

이것이 실패하지 않으면 테스트가 게이트를 검증하지 않는다는 뜻이다. 그 경우 멈추고 원인을 조사한다.

- [ ] **Step 4: 프로덕션 코드 원복**

`backend/app/api/reports.py:93`을 원래대로 되돌린다:

```python
    _: User = Depends(require_admin),
```

Run: `cd backend && uv run git diff --stat app/api/reports.py`
Expected: 출력 없음 (변경 사항 0). 출력이 있으면 원복이 덜 된 것이다.

- [ ] **Step 5: 백엔드 전체 테스트**

Run: `cd backend && uv run pytest`
Expected: **108 passed** (기존 106 + 신규 2)

- [ ] **Step 6: 커밋**

```bash
git add backend/tests/test_admin_reports.py
git commit -m "$(cat <<'EOF'
test(backend): handle_report 관리자 게이트 403/401 테스트

list_reports 쪽만 권한 거부가 고정돼 있었다. handle_report의
require_admin 의존성이 리팩터링 중 사라져도 테스트가 잡도록 대칭 추가.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: M3 — KST 날짜 표시

**Files:**
- Create: `frontend/src/lib/datetime.ts`
- Create: `frontend/src/lib/datetime.test.ts`
- Modify: `frontend/src/pages/Admin/ReportTab.tsx:72` (및 상단 import)
- Modify: `frontend/src/pages/Admin/ReportTab.test.tsx` (단언 1개 추가)

**Interfaces:**
- Consumes: 없음 (신규 모듈)
- Produces: `formatKST(iso: string): string` — `frontend/src/lib/datetime.ts`에서 named export. UTC ISO 문자열을 `YYYY-MM-DD HH:mm` 형태의 KST 문자열로 변환한다. 파싱 실패 시 입력 문자열을 그대로 반환한다

**배경:** 백엔드는 `datetime.utcnow()`로 **naive** UTC를 저장하고, Pydantic 직렬화 결과에 타임존 suffix가 없다 (`2026-08-03T17:01:59.776396`). 현재 `ReportTab.tsx:72`가 이 문자열을 그대로 화면에 출력해서 실제 한국 시각보다 9시간 이르게 보인다.

**함정:** 여기서 `new Date(iso)`만 쓰면 자바스크립트는 offset 없는 ISO 문자열을 **로컬 시간으로 해석**한다. 따라서 `.toLocaleString()`을 붙여도 여전히 9시간 틀린 값이 나온다. 반드시 "이건 UTC다"를 명시해야 한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/datetime.test.ts` 신규 생성:

```ts
import { describe, it, expect } from "vitest";
import { formatKST } from "./datetime";

describe("formatKST", () => {
  it("타임존 표시 없는 UTC 문자열을 KST로 변환 (날짜 넘어감)", () => {
    expect(formatKST("2026-08-03T17:01:59.776396")).toBe("2026-08-04 02:01");
  });

  it("이미 Z가 붙은 입력도 같은 결과 (Z 중복 안 붙음)", () => {
    expect(formatKST("2026-08-03T17:01:59Z")).toBe("2026-08-04 02:01");
  });

  it("offset이 붙은 입력은 그 offset을 존중 (이중 변환 안 함)", () => {
    expect(formatKST("2026-08-03T17:01:59+09:00")).toBe("2026-08-03 17:01");
  });

  it("자정 경계에서 24시가 아니라 00시로 출력", () => {
    expect(formatKST("2026-08-03T15:00:00")).toBe("2026-08-04 00:00");
  });

  it("파싱 불가한 입력은 원문 그대로 반환", () => {
    expect(formatKST("어제")).toBe("어제");
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: FAIL — `Failed to resolve import "./datetime"`

- [ ] **Step 3: 최소 구현 작성**

`frontend/src/lib/datetime.ts` 신규 생성:

```ts
// 서버는 naive UTC(타임존 표시 없음)로 내려준다. 표시가 없으면 UTC로 간주한다.
// 날짜 부분의 "-"(2026-08-03)를 offset으로 오인하지 않도록 끝 위치에 고정한다.
const TZ_SUFFIX = /(Z|[+-]\d{2}:\d{2})$/;

const KST_FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** UTC ISO 문자열을 "YYYY-MM-DD HH:mm" 형태의 KST로 변환. 실패하면 원문 반환. */
export function formatKST(iso: string): string {
  const date = new Date(TZ_SUFFIX.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) return iso;

  const parts = KST_FORMAT.formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}
```

구현 노트 (검토자용):

- **`toLocaleString`을 안 쓴 이유:** 로케일·브라우저 구현에 따라 구분자와 자릿수가 달라져 `2026-08-04 02:01` 고정 형식이 보장되지 않는다. `formatToParts`로 조각을 뽑아 직접 조립하면 실행 환경과 무관하게 같은 결과가 나온다
- **`hourCycle: "h23"`인 이유:** `hour12: false`는 구현에 따라 자정을 `24:00`으로 내놓는 경우가 있다. `h23`은 `00`을 보장한다
- **`en-US` 로케일인 이유:** 숫자 조각만 뽑아 쓰고 구분자는 직접 붙이므로 로케일은 결과에 영향을 주지 않는다. `ko-KR`을 쓰면 조각 값에 "오전/오후" 같은 요소가 섞여 혼란만 준다
- **`Intl.DateTimeFormat`을 모듈 최상위에 한 번만 만드는 이유:** 생성 비용이 있어 목록 렌더마다 새로 만들 필요가 없다

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: PASS — 5 passed

- [ ] **Step 5: `ReportTab`에 실패하는 단언 추가**

`frontend/src/pages/Admin/ReportTab.test.tsx`의 `describe("ReportTab", ...)` 블록 안, 마지막 `it("로드 실패 시 에러 문구", ...)` 앞에 추가한다:

```tsx
  it("작성 시각을 KST로 변환해 표시", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report]);
    render(<ReportTab />);
    // 목데이터 created_at 은 UTC 2026-08-03T14:30:00 → KST 23:30
    await waitFor(() =>
      expect(screen.getByText("2026-08-03 23:30")).toBeInTheDocument(),
    );
  });
```

- [ ] **Step 6: 테스트 실행 — 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/ReportTab.test.tsx`
Expected: FAIL — `Unable to find an element with the text: 2026-08-03 23:30` (현재는 `2026-08-03T14:30:00` 원문이 렌더된다)

- [ ] **Step 7: 호출부 연결**

`frontend/src/pages/Admin/ReportTab.tsx` 상단 import에 한 줄 추가한다. 현재 3번째 줄(`import type { AdminReportOut } ...`) 다음에:

```tsx
import { formatKST } from "../../lib/datetime";
```

그리고 72번째 줄을 바꾼다:

```tsx
          <div className={styles.when}>{formatKST(r.created_at)}</div>
```

(변경 전: `<div className={styles.when}>{r.created_at}</div>`)

- [ ] **Step 8: 테스트 실행 — 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/ReportTab.test.tsx`
Expected: PASS — 6 passed (기존 5 + 신규 1)

- [ ] **Step 9: 타입 체크 + 전체 테스트**

Run: `cd frontend && npx tsc --noEmit`
Expected: 출력 없음

Run: `cd frontend && npm run test`
Expected: **106 passed** (기존 100 + datetime 5 + ReportTab 1)

- [ ] **Step 10: 커밋**

```bash
git add frontend/src/lib/datetime.ts frontend/src/lib/datetime.test.ts frontend/src/pages/Admin/ReportTab.tsx frontend/src/pages/Admin/ReportTab.test.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): 신고 작성 시각 KST 변환 표시

서버가 naive UTC로 내려주는데 화면이 원문을 그대로 찍어 9시간 어긋났다.
offset 없는 문자열은 JS가 로컬로 해석하므로 Z를 명시해 파싱한다.
포맷 로직은 lib/datetime.ts 한 곳에 가둔다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: M1 + M8 — 헤딩 · 탭 시맨틱

**Files:**
- Modify: `frontend/src/pages/Admin/Admin.tsx` (전체 교체)
- Modify: `frontend/src/pages/Admin/Admin.module.css:32-36` (`.title` 규칙)
- Modify: `frontend/src/pages/Admin/VerificationTab.tsx:99` (h1 삭제)
- Modify: `frontend/src/pages/Admin/Admin.test.tsx` (기존 테스트 수정 + 단언 추가)

**Interfaces:**
- Consumes: `VerificationTab` / `ReportTab` 기본 export (변경 없음)
- Produces: 없음

**배경 (M1):** 탭 구조로 바꾼 뒤 `VerificationTab`에만 `<h1>학생증 심사</h1>`가 남아 탭 라벨과 글자가 중복된다. 반대로 `ReportTab`에는 h1이 없어서 신고 탭을 보면 페이지에 h1이 아예 사라진다. h1을 `Admin.tsx`로 올려 어느 탭에서든 하나만 존재하게 한다.

**배경 (M8):** 탭 버튼이 그냥 `<button>`이라 스크린리더가 탭 UI로 인식하지 못한다.

**ARIA 범위:** `tablist` / `tab` / `aria-selected` / `tabpanel` + `aria-labelledby`까지만 넣는다. 좌우 화살표 키보드 이동과 로빙 tabindex는 **넣지 않는다** — 탭이 2개뿐이라 Tab 키로 모두 도달 가능하고, 로빙 tabindex는 상태 관리 코드를 크게 늘린다.

- [ ] **Step 1: 실패하는 테스트로 기존 테스트 수정**

`frontend/src/pages/Admin/Admin.test.tsx`의 `describe("Admin", ...)` 블록 전체를 아래로 교체한다. 기존 2번째 테스트가 `getByRole("button", ...)`을 쓰는데 `role="tab"`이 붙으면 더 이상 button 롤이 아니라서 그대로 두면 깨진다:

```tsx
describe("Admin", () => {
  it("기본 탭은 학생증 심사", async () => {
    render(<Admin />);
    await waitFor(() =>
      expect(screen.getByText("심사 대기 없음")).toBeInTheDocument(),
    );
    expect(api.listPendingVerifications).toHaveBeenCalled();
  });

  it("페이지 h1은 탭과 무관하게 '관리자' 하나", async () => {
    render(<Admin />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("관리자");
    fireEvent.click(screen.getByRole("tab", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("관리자");
  });

  it("신고 · 건의 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("tab", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
  });

  it("선택된 탭만 aria-selected=true", async () => {
    render(<Admin />);
    const verification = screen.getByRole("tab", { name: "학생증 심사" });
    const report = screen.getByRole("tab", { name: "신고 · 건의" });

    expect(verification).toHaveAttribute("aria-selected", "true");
    expect(report).toHaveAttribute("aria-selected", "false");

    fireEvent.click(report);
    await waitFor(() =>
      expect(report).toHaveAttribute("aria-selected", "true"),
    );
    expect(verification).toHaveAttribute("aria-selected", "false");
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/Admin.test.tsx`
Expected: FAIL — `Unable to find an accessible element with the role "tab"` (신규 3개 테스트 전부 실패, 첫 번째만 통과)

- [ ] **Step 3: `Admin.tsx` 구현**

`frontend/src/pages/Admin/Admin.tsx` 전체를 아래로 교체한다:

```tsx
import { useState } from "react";
import VerificationTab from "./VerificationTab";
import ReportTab from "./ReportTab";
import styles from "./Admin.module.css";

type Tab = "verification" | "report";

export default function Admin() {
  const [tab, setTab] = useState<Tab>("verification");

  return (
    <div>
      <h1 className={styles.title}>관리자</h1>
      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          id="tab-verification"
          aria-selected={tab === "verification"}
          className={tab === "verification" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("verification")}
        >
          학생증 심사
        </button>
        <button
          type="button"
          role="tab"
          id="tab-report"
          aria-selected={tab === "report"}
          className={tab === "report" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("report")}
        >
          신고 · 건의
        </button>
      </div>
      {tab === "verification" ? (
        <div role="tabpanel" aria-labelledby="tab-verification">
          <VerificationTab />
        </div>
      ) : (
        <div role="tabpanel" aria-labelledby="tab-report">
          <ReportTab />
        </div>
      )}
    </div>
  );
}
```

구현 노트 (검토자용):

- **`aria-labelledby`만 쓰고 `aria-controls`는 안 쓴 이유:** 선택되지 않은 패널은 DOM에서 아예 제거되는 구조(삼항 렌더)라, 탭에 `aria-controls`를 달면 존재하지 않는 id를 가리키게 된다. 패널→탭 방향의 `aria-labelledby`만 쓰면 이 문제가 없다
- **`.tab` / `.tabActive` 클래스 조립 방식은 기존 코드 그대로 유지**한다

- [ ] **Step 4: `VerificationTab`의 h1 삭제**

`frontend/src/pages/Admin/VerificationTab.tsx`의 99번째 줄을 삭제한다:

```tsx
      <h1 className={styles.title}>학생증 심사</h1>
```

삭제 후 해당 return 문은 이렇게 시작한다:

```tsx
  return (
    <div className={styles.wrap}>
      {loading && <p>불러오는 중…</p>}
```

- [ ] **Step 5: `.title` CSS 수정**

`frontend/src/pages/Admin/Admin.module.css`의 32~36번째 줄을 아래로 교체한다:

```css
.title {
  max-width: 390px;
  margin: 0 auto 16px;
  padding: 0 16px;
  font-size: 20px;
  font-weight: 700;
}
```

(변경 전: `max-width` / `margin` / `padding` 없이 `font-size`, `font-weight`, `margin-bottom: 16px`만 있었다)

**이 수정이 필요한 이유:** 기존 `.title`은 `.wrap`(`max-width: 390px` + `padding: 24px 16px`) **안에** 있었기 때문에 폭과 좌우 여백을 부모에게서 받았다. h1이 `Admin.tsx` 최상위로 올라가면 `.wrap` 밖이라 그 제약이 사라져 화면 왼쪽 끝에 붙고 탭 바와 어긋난다. 값은 `.tabs` 규칙(9~15번째 줄)과 동일하게 맞춘다.

- [ ] **Step 6: 테스트 실행 — 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/`
Expected: PASS — Admin 4 passed, ReportTab 6 passed, VerificationTab 6 passed

`VerificationTab.test.tsx`는 h1을 단언하지 않으므로 h1 삭제로 깨지지 않는다.

- [ ] **Step 7: 타입 체크 + 전체 테스트 + 빌드**

Run: `cd frontend && npx tsc --noEmit`
Expected: 출력 없음

Run: `cd frontend && npm run test`
Expected: **108 passed** (Task 2 종료 시점 106 + Admin 신규 2)

Run: `cd frontend && npm run build`
Expected: 성공

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/pages/Admin/Admin.tsx frontend/src/pages/Admin/Admin.module.css frontend/src/pages/Admin/VerificationTab.tsx frontend/src/pages/Admin/Admin.test.tsx
git commit -m "$(cat <<'EOF'
fix(frontend): 관리자 페이지 h1 통합 + 탭 ARIA 롤

h1이 학생증 탭에만 있어 탭 라벨과 중복되고 신고 탭에선 사라졌다.
Admin 으로 올려 어느 탭에서든 하나만 두고, 탭 바에 tablist/tab/
aria-selected/tabpanel 부여. .wrap 밖으로 나가는 만큼 .title 에
폭·여백을 직접 지정한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## 최종 검증

세 태스크를 모두 마친 뒤 실행한다.

- [ ] **백엔드 전체**

Run: `cd backend && uv run pytest`
Expected: **108 passed**

- [ ] **프론트 전체**

Run: `cd frontend && npm run test`
Expected: **108 passed**

- [ ] **타입 · 빌드**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: 무에러, 빌드 성공

- [ ] **브라우저 수동 확인**

백엔드 `:8000`, 프론트 `:5173`을 띄운 뒤 관리자 계정으로 `/admin`에 접속한다.

**주의:** `dev.db`의 기존 관리자 계정(`admin@datedrop.kr`) 비밀번호는 알려져 있지 않다. 임시 관리자 계정이 필요하면 `POST /auth/register`로 만든 뒤 DB에서 `is_admin=True`, `status=active`로 승격시키고, 확인이 끝나면 삭제한다.

확인 항목:

| 항목 | 기대 |
|---|---|
| 페이지 h1 | "관리자" 하나. 탭을 전환해도 그대로 |
| 학생증 심사 탭 | 탭 라벨 아래에 "학생증 심사" 제목이 더 이상 없음 |
| h1 정렬 | 탭 바와 좌측 끝이 맞음 (왼쪽 끝에 붙지 않음) |
| 신고 카드 날짜 | `2026-08-04 02:01` 꼴. 원문 ISO 문자열이 아님 |
| 날짜 정확성 | 표시된 시각이 실제 한국 시각과 일치 (9시간 어긋나지 않음) |
| 탭 동작 | 전환 · "처리 완료" · "처리된 항목도 보기" 모두 기존대로 동작 |

- [ ] **통합**

`superpowers:finishing-a-development-branch` 스킬로 진행한다. 사용자에게 머지/PR/유지를 묻고 선택에 따른다.
