# 관리자 신고 조회 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관리자가 접수된 신고·건의를 읽고 처리 완료를 표시할 수 있게 한다.

**Architecture:** `Report`에 `handled` boolean 하나를 더해 처리 여부를 표현한다. 조회·처리 엔드포인트 2개를 `require_admin`으로 보호하고, `Admin` 페이지를 `Game.tsx`와 같은 탭 컨테이너로 재편해 학생증 심사와 신고·건의를 나란히 둔다.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · pytest / React 18 · Vite · vitest · @testing-library/react

**설계 문서:** `docs/superpowers/specs/2026-08-03-admin-report-review-design.md`

## Global Constraints

- 두 엔드포인트 모두 `require_admin`(`app/core/deps.py:55`) 사용. 일반 유저 → 403, 미인증 → 401.
- 응답에 **`reporter_id`를 절대 넣지 않는다.** 화면에서 쓰지 않고, 유출된 내부 PK는 다른 API를 찌르는 재료가 된다.
- `POST .../handle`은 **멱등**이다. 이미 `handled=True`여도 200을 반환한다.
- 처리 되돌리기(`unhandle`), 신고 삭제, 페이징, `handled_at`/`handled_by`는 **범위 밖**이다. 만들지 않는다.
- 에러 문구는 정확히 이 문자열: `"존재하지 않는 신고입니다"`
- 프론트 문구는 기존 관리자 화면과 통일: 로드 실패 `"목록을 불러오지 못했어요."`, 빈 목록 `"신고 · 건의 없음"`
- 학생증 심사 코드는 **옮기기만 하고 고치지 않는다.** 이동과 변경이 한 diff에 섞이면 리뷰가 둘을 구분할 수 없다.
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- ⛔ 매칭 알고리즘 관련 코드 금지.

**명령어**
- 백엔드: `cd backend && uv run pytest -v`
- 프론트: `cd frontend && npm run test` / `npx tsc --noEmit` / `npm run build`
- 마이그레이션: `cd backend && uv run alembic revision --autogenerate -m "..."` → `uv run alembic upgrade head`

**착수 시점 기준선:** 백엔드 96 passed / 프론트 20 files 92 passed

---

## File Structure

| 파일 | 책임 | 작업 |
|---|---|---|
| `backend/app/models/report.py` | `handled` 컬럼 | 수정 |
| `backend/alembic/versions/<rev>_report_handled.py` | 스키마 반영 | 생성 |
| `backend/app/schemas/report.py` | `AdminReportOut` | 수정 |
| `backend/app/api/reports.py` | 관리자 라우터 2개 | 수정 |
| `backend/app/api/router.py` | 관리자 라우터 등록 | 수정 |
| `backend/tests/test_admin_reports.py` | 백엔드 테스트 10개 | 생성 |
| `frontend/src/lib/types.ts` | `AdminReportOut` | 수정 |
| `frontend/src/lib/api.ts` | `listReports`, `markReportHandled` | 수정 |
| `frontend/src/pages/Admin/Admin.tsx` | 탭 컨테이너로 축소 | 수정 |
| `frontend/src/pages/Admin/VerificationTab.tsx` | 학생증 심사 (이동) | 생성 |
| `frontend/src/pages/Admin/VerificationTab.test.tsx` | 기존 테스트 (이동) | 생성 |
| `frontend/src/pages/Admin/Admin.test.tsx` | 탭 전환만 | 재작성 |
| `frontend/src/pages/Admin/ReportTab.tsx` | 신고·건의 목록 | 생성 |
| `frontend/src/pages/Admin/ReportTab.test.tsx` | 프론트 테스트 5개 | 생성 |
| `frontend/src/pages/Admin/Admin.module.css` | 탭·카드 스타일 | 수정 |
| `frontend/src/pages/Report/Report.tsx` | 고지 문구 | 수정 |
| `frontend/src/pages/Report/Report.test.tsx` | 고지 문구 테스트 | 수정 |
| `CLAUDE.md` | 미결 항목 행 제거 | 수정 |
| `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md` | API 목록 | 수정 |

---

## Task 1: 모델 · 마이그레이션

**Files:**
- Modify: `backend/app/models/report.py`
- Create: `backend/alembic/versions/<자동생성>_report_handled.py`

**Interfaces:**
- Produces: `Report.handled: bool`
- Consumes: 없음

- [ ] **Step 1: 기존 행 수 확인**

Run: `cd backend && uv run python -c "from app.database import SessionLocal; from sqlalchemy import text; print(SessionLocal().execute(text('SELECT count(*) FROM reports')).scalar())"`

Expected: `0`

0이 아니어도 이번에는 진행해도 된다 — `handled=false`는 기존 신고에 대해 "아직 처리 안 함"이라는 **참인 값**이다. (`User.gender`에서 문제가 됐던 것은 기본값의 존재가 아니라 `"male"`이 여성 유저에게 거짓이었다는 점이다.) 다만 실제 숫자를 보고서에 기록한다.

- [ ] **Step 2: 모델에 컬럼 추가**

`backend/app/models/report.py` — import 줄에 `Boolean`을 추가한다:

```python
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
```

`created_at` 정의 **앞에** 다음 줄을 넣는다:

```python
    handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **Step 3: 리비전 생성**

Run: `cd backend && uv run alembic revision --autogenerate -m "report handled"`

- [ ] **Step 4: 생성된 파일 대조·수정**

생성된 파일이 아래와 일치하는지 확인하고 다르면 맞춘다.

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column("handled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("reports", "handled")
```

새 enum 타입을 만들지 않으므로 `CREATE TYPE` 문제(`33aa8ba5f23f`, `f791f9b09268`에서 겪은 것)는 해당하지 않는다. `batch_alter_table`도 필요 없다.

만약 SQLite에서 `drop_column`이 실패하면 downgrade만 batch로 감싼다:

```python
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("handled")
```

- [ ] **Step 5: 양방향 확인**

Run:
```bash
cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
```
Expected: 세 명령 모두 에러 없이 완료

- [ ] **Step 6: 회귀 확인**

Run: `cd backend && uv run pytest -v`
Expected: 96 passed

- [ ] **Step 7: 커밋**

```bash
git add backend/app/models/report.py backend/alembic/versions/
git commit -m "feat(backend): Report.handled 컬럼 + 마이그레이션

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: 관리자 조회 · 처리 API

**Files:**
- Modify: `backend/app/schemas/report.py`
- Modify: `backend/app/api/reports.py`
- Modify: `backend/app/api/router.py:2,8`
- Test: `backend/tests/test_admin_reports.py` (생성)

**Interfaces:**
- Consumes: Task 1의 `Report.handled`
- Produces: `GET /admin/reports?include_handled=`, `POST /admin/reports/{id}/handle`, 스키마 `AdminReportOut`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_admin_reports.py` 생성:

```python
from fastapi.testclient import TestClient


def _reporter_headers(
    client: TestClient,
    email: str = "reporter@test.com",
    name: str = "신고자",
    university: str = "서울대학교",
) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": name,
        "university": university,
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_report(client: TestClient, headers: dict, reason: str = "부적절한 사진") -> int:
    res = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": reason,
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def _make_suggestion(client: TestClient, headers: dict) -> int:
    res = client.post("/reports", json={
        "type": "suggestion",
        "target_name": None,
        "target_university": None,
        "reason": "알림 끄는 기능 주세요",
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_list_excludes_handled_by_default(admin_client: TestClient):
    headers = _reporter_headers(admin_client)
    handled_id = _make_report(admin_client, headers, "처리될 신고")
    _make_report(admin_client, headers, "남아있을 신고")
    admin_client.post(f"/admin/reports/{handled_id}/handle")

    res = admin_client.get("/admin/reports")
    assert res.status_code == 200
    reasons = [r["reason"] for r in res.json()]
    assert "남아있을 신고" in reasons
    assert "처리될 신고" not in reasons


def test_list_include_handled(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r2@test.com")
    handled_id = _make_report(admin_client, headers, "처리될 신고")
    admin_client.post(f"/admin/reports/{handled_id}/handle")

    res = admin_client.get("/admin/reports?include_handled=true")
    assert res.status_code == 200
    reasons = [r["reason"] for r in res.json()]
    assert "처리될 신고" in reasons


def test_list_sorted_newest_first(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r3@test.com")
    _make_report(admin_client, headers, "먼저 쓴 신고")
    _make_report(admin_client, headers, "나중 쓴 신고")

    data = admin_client.get("/admin/reports").json()
    ids = [r["id"] for r in data]
    assert ids == sorted(ids, reverse=True)


def test_list_includes_reporter_and_hides_id(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r4@test.com", "김철수", "고려대학교")
    _make_report(admin_client, headers)

    item = admin_client.get("/admin/reports").json()[0]
    assert item["reporter_name"] == "김철수"
    assert item["reporter_university"] == "고려대학교"
    assert "reporter_id" not in item


def test_list_suggestion_has_null_target(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r5@test.com")
    _make_suggestion(admin_client, headers)

    item = admin_client.get("/admin/reports").json()[0]
    assert item["type"] == "suggestion"
    assert item["target_name"] is None
    assert item["target_university"] is None


def test_handle_marks_handled(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r6@test.com")
    report_id = _make_report(admin_client, headers)

    res = admin_client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 200
    assert res.json()["handled"] is True


def test_handle_is_idempotent(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r7@test.com")
    report_id = _make_report(admin_client, headers)

    admin_client.post(f"/admin/reports/{report_id}/handle")
    res = admin_client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 200
    assert res.json()["handled"] is True


def test_handle_missing_report(admin_client: TestClient):
    res = admin_client.post("/admin/reports/99999/handle")
    assert res.status_code == 404
    assert res.json()["detail"] == "존재하지 않는 신고입니다"


def test_list_forbidden_for_normal_user(client: TestClient):
    headers = _reporter_headers(client, "normal@test.com")
    res = client.get("/admin/reports", headers=headers)
    assert res.status_code == 403


def test_list_unauthorized(client: TestClient):
    res = client.get("/admin/reports")
    assert res.status_code == 401
```

`admin_client` 픽스처(`backend/tests/conftest.py:41`)는 관리자 토큰을 클라이언트 기본 헤더에 넣어둔다. `_reporter_headers`가 돌려주는 헤더를 요청마다 명시하면 그 요청만 일반 유저로 나간다.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_admin_reports.py -v`
Expected: FAIL — 엔드포인트가 없으므로 대부분 404. 10개 중 최소 9개 실패.

- [ ] **Step 3: 스키마 추가**

`backend/app/schemas/report.py` 끝에 추가:

```python
class AdminReportOut(BaseModel):
    id: int
    type: ReportType
    target_name: str | None
    target_university: str | None
    reason: str
    created_at: datetime
    handled: bool
    reporter_name: str
    reporter_university: str
```

`from_attributes`를 넣지 않는다. `AdminVerificationOut`(`app/schemas/verification.py`)처럼 엔드포인트에서 직접 만들어 채운다 — 조인한 유저 필드가 ORM 객체에 없기 때문이다.

- [ ] **Step 4: 관리자 라우터 구현**

`backend/app/api/reports.py`의 import 블록을 아래로 바꾼다:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.report import Report, ReportType
from app.models.user import User
from app.schemas.report import AdminReportOut, ReportCreate, ReportOut
```

`router = APIRouter(prefix="/reports", tags=["reports"])` 아래에 한 줄 추가한다:

```python
admin_router = APIRouter(prefix="/admin/reports", tags=["reports"])
```

파일 끝에 다음을 추가한다:

```python
def _to_admin_out(report: Report, reporter: User) -> AdminReportOut:
    return AdminReportOut(
        id=report.id,
        type=report.type,
        target_name=report.target_name,
        target_university=report.target_university,
        reason=report.reason,
        created_at=report.created_at,
        handled=report.handled,
        reporter_name=reporter.name,
        reporter_university=reporter.university,
    )


@admin_router.get("", response_model=list[AdminReportOut])
def list_reports(
    include_handled: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Report, User).join(User, Report.reporter_id == User.id)
    if not include_handled:
        query = query.filter(Report.handled.is_(False))
    rows = query.order_by(Report.created_at.desc(), Report.id.desc()).all()
    return [_to_admin_out(report, reporter) for report, reporter in rows]


@admin_router.post("/{report_id}/handle", response_model=AdminReportOut)
def handle_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지 않는 신고입니다",
        )
    # 멱등: 이미 처리된 건을 다시 눌러도 200
    if not report.handled:
        report.handled = True
        db.commit()
        db.refresh(report)
    reporter = db.get(User, report.reporter_id)
    return _to_admin_out(report, reporter)
```

`order_by`에 `Report.id.desc()`를 함께 넣는 이유: `created_at`이 초 단위라 같은 테스트 안에서 만든 두 신고가 동일한 값을 가질 수 있다. id를 보조 키로 두면 순서가 안정된다.

- [ ] **Step 5: 라우터 등록**

`backend/app/api/router.py` 마지막 줄 뒤에 추가:

```python
router.include_router(reports.admin_router)
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_admin_reports.py -v`
Expected: PASS 10/10

- [ ] **Step 7: 뮤테이션 검증**

작성한 테스트가 실제로 규칙을 고정하는지 확인한다. 하나씩 고의로 망가뜨리고 대응 테스트가 실패하는지 본다:

1. `if not include_handled:` 필터 블록 제거 → `test_list_excludes_handled_by_default` 실패해야 함
2. `require_admin` → `get_current_user`로 교체 → `test_list_forbidden_for_normal_user` 실패해야 함
3. `_to_admin_out`에 `reporter_id=report.reporter_id`를 추가하고 스키마에도 필드 추가 → `test_list_includes_reporter_and_hides_id` 실패해야 함
4. 404 분기 제거 → `test_handle_missing_report` 실패해야 함

실패하지 않는 항목이 있으면 그 테스트가 무효이니 고친다. **확인 후 모든 뮤테이션을 원복하고** `git status`가 깨끗한지 본다. 결과를 표로 보고서에 남긴다.

- [ ] **Step 8: 전체 회귀**

Run: `cd backend && uv run pytest -v`
Expected: 106 passed (96 + 10)

- [ ] **Step 9: 커밋**

```bash
git add backend/app/schemas/report.py backend/app/api/reports.py backend/app/api/router.py backend/tests/test_admin_reports.py
git commit -m "feat(backend): 관리자 신고 조회·처리 API

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: 프론트 타입 · API 함수

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: Task 2의 API 계약
- Produces: `AdminReportOut` 타입 / `listReports(includeHandled?: boolean)`, `markReportHandled(id: number)`

- [ ] **Step 1: 타입 추가**

`frontend/src/lib/types.ts` 끝에 추가:

```ts
export interface AdminReportOut {
  id: number;
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
  created_at: string;
  handled: boolean;
  reporter_name: string;
  reporter_university: string;
}
```

- [ ] **Step 2: api 함수 추가**

`frontend/src/lib/api.ts`의 import 목록에 `AdminReportOut,` 한 줄을 추가하고, 파일 끝에 다음을 넣는다:

```ts
export function listReports(includeHandled = false): Promise<AdminReportOut[]> {
  return apiFetch<AdminReportOut[]>(
    `/admin/reports?include_handled=${includeHandled}`,
    { method: "GET" },
  );
}

export function markReportHandled(id: number): Promise<AdminReportOut> {
  return apiFetch<AdminReportOut>(`/admin/reports/${id}/handle`, { method: "POST" });
}
```

- [ ] **Step 3: 타입체크**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): 관리자 신고 조회 타입 + API 함수

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Admin 탭 재편 (순수 이동)

학생증 심사 로직을 `VerificationTab`으로 옮기고 `Admin`을 탭 컨테이너로 만든다. **로직은 한 줄도 바꾸지 않는다.**

**Files:**
- Create: `frontend/src/pages/Admin/VerificationTab.tsx`
- Create: `frontend/src/pages/Admin/VerificationTab.test.tsx`
- Modify: `frontend/src/pages/Admin/Admin.tsx` (전면 교체)
- Modify: `frontend/src/pages/Admin/Admin.test.tsx` (전면 교체)
- Modify: `frontend/src/pages/Admin/Admin.module.css`

**Interfaces:**
- Consumes: 없음 (기존 코드 이동)
- Produces: `VerificationTab` 기본 export, `ReportTab`이 들어갈 탭 자리

- [ ] **Step 1: VerificationTab 생성 (내용 이동)**

`frontend/src/pages/Admin/VerificationTab.tsx`를 만들고, **현재 `Admin.tsx`의 1~108줄 전체를 그대로 복사한 뒤** 마지막 컴포넌트 이름만 바꾼다:

- `export default function Admin() {` → `export default function VerificationTab() {`
- import 경로(`../../lib/api`, `../../components/Button/Button`, `./Admin.module.css`)는 같은 디렉터리이므로 **그대로 둔다**
- `Card` 컴포넌트, `useEffect` 로직, JSX 모두 **손대지 않는다**

- [ ] **Step 2: 테스트 이동**

`frontend/src/pages/Admin/VerificationTab.test.tsx`를 만들고 현재 `Admin.test.tsx` 전체를 복사한 뒤 두 곳만 바꾼다:

- `import Admin from "./Admin";` → `import VerificationTab from "./VerificationTab";`
- 모든 `render(<Admin />)` → `render(<VerificationTab />)` (6곳)
- `describe("Admin", ...)` → `describe("VerificationTab", ...)`

테스트 본문은 바꾸지 않는다.

- [ ] **Step 3: 이동 검증**

Run: `cd frontend && npx vitest run src/pages/Admin/VerificationTab.test.tsx`
Expected: PASS 6/6 — 이동이 무손실임을 확인하는 단계다.

- [ ] **Step 4: Admin.tsx를 탭 컨테이너로 교체**

`frontend/src/pages/Admin/Admin.tsx` 전체를 아래로 바꾼다:

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
      <div className={styles.tabs}>
        <button
          type="button"
          className={tab === "verification" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("verification")}
        >
          학생증 심사
        </button>
        <button
          type="button"
          className={tab === "report" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("report")}
        >
          신고 · 건의
        </button>
      </div>
      {tab === "verification" ? <VerificationTab /> : <ReportTab />}
    </div>
  );
}
```

`ReportTab`은 Task 5에서 만든다. **이 태스크 안에서 최소 구현체를 먼저 만들어 둔다** — 아래 Step 5.

- [ ] **Step 5: ReportTab 임시 스텁 생성**

Task 4를 독립적으로 통과시키기 위해 `frontend/src/pages/Admin/ReportTab.tsx`를 만든다:

```tsx
export default function ReportTab() {
  return null;
}
```

Task 5가 이 파일을 실제 구현으로 채운다.

- [ ] **Step 6: Admin.test.tsx 재작성**

`frontend/src/pages/Admin/Admin.test.tsx` 전체를 아래로 바꾼다:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Admin from "./Admin";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
  vi.spyOn(api, "listReports").mockResolvedValue([]);
});

describe("Admin", () => {
  it("기본 탭은 학생증 심사", async () => {
    render(<Admin />);
    await waitFor(() =>
      expect(screen.getByText("심사 대기 없음")).toBeInTheDocument(),
    );
    expect(api.listPendingVerifications).toHaveBeenCalled();
  });
});
```

탭 전환 테스트는 `ReportTab`이 실제로 렌더할 내용이 생긴 뒤라야 의미가 있으므로 Task 5에서 추가한다. **이 태스크가 끝난 시점에 실패하는 테스트는 없어야 한다.**

`fireEvent`는 이 시점에 쓰이지 않으므로 import 목록에서 빼고, Task 5에서 다시 넣는다.

- [ ] **Step 7: 탭 스타일 추가**

`frontend/src/pages/Admin/Admin.module.css`의 `.wrap` 정의 **뒤에** 추가한다. 색상값은 이 파일과 `Game.module.css`가 이미 쓰는 값과 동일하게 맞춘다:

```css
.tabs {
  display: flex;
  gap: 8px;
  max-width: 390px;
  margin: 0 auto 16px;
  padding: 0 16px;
}

.tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  border-bottom: 2px solid transparent;
  color: #999;
  font-weight: 600;
  cursor: pointer;
}

.tabActive {
  color: #FF7F5C;
  border-bottom-color: #FF7F5C;
}
```

- [ ] **Step 8: 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/ && npx tsc --noEmit`
Expected: `VerificationTab.test.tsx` 6/6 PASS, `Admin.test.tsx` 1 PASS / 1 FAIL(스텁 때문), tsc 무에러

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/pages/Admin/
git commit -m "refactor(frontend): Admin 을 탭 컨테이너로 분리 (학생증 심사 이동)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: ReportTab

**Files:**
- Modify: `frontend/src/pages/Admin/ReportTab.tsx` (스텁 → 구현)
- Create: `frontend/src/pages/Admin/ReportTab.test.tsx`
- Modify: `frontend/src/pages/Admin/Admin.module.css`

**Interfaces:**
- Consumes: Task 3의 `listReports`, `markReportHandled`, `AdminReportOut`
- Produces: `ReportTab` 기본 export (props 없음)

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/pages/Admin/ReportTab.test.tsx` 생성:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReportTab from "./ReportTab";
import * as api from "../../lib/api";
import type { AdminReportOut } from "../../lib/types";

beforeEach(() => vi.clearAllMocks());

const report: AdminReportOut = {
  id: 1, type: "report",
  target_name: "홍길동", target_university: "연세대학교",
  reason: "부적절한 사진", created_at: "2026-08-03T14:30:00",
  handled: false,
  reporter_name: "김철수", reporter_university: "서울대학교",
};

const suggestion: AdminReportOut = {
  id: 2, type: "suggestion",
  target_name: null, target_university: null,
  reason: "알림 끄는 기능 주세요", created_at: "2026-08-03T15:00:00",
  handled: false,
  reporter_name: "이영희", reporter_university: "고려대학교",
};

describe("ReportTab", () => {
  it("신고는 대상 줄 표시, 건의는 미표시 + 유형 배지", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report, suggestion]);
    render(<ReportTab />);
    await waitFor(() => expect(screen.getByText(/홍길동/)).toBeInTheDocument());
    expect(screen.getByText("신고")).toBeInTheDocument();
    expect(screen.getByText("건의")).toBeInTheDocument();
    expect(screen.getByText(/알림 끄는 기능/)).toBeInTheDocument();
    // 카드 2장 중 대상 줄은 신고 쪽 하나뿐이어야 한다
    expect(screen.getAllByText(/^대상:/)).toHaveLength(1);
  });

  it("신고자 이름·학교 표시", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report]);
    render(<ReportTab />);
    await waitFor(() => expect(screen.getByText(/김철수/)).toBeInTheDocument());
    expect(screen.getByText(/서울대학교/)).toBeInTheDocument();
  });

  it("처리 완료 클릭 → API 호출 후 목록에서 제거", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report]);
    const spy = vi.spyOn(api, "markReportHandled")
      .mockResolvedValue({ ...report, handled: true });
    render(<ReportTab />);
    await waitFor(() => screen.getByText(/홍길동/));
    fireEvent.click(screen.getByRole("button", { name: "처리 완료" }));
    await waitFor(() => expect(screen.queryByText(/홍길동/)).toBeNull());
    expect(spy).toHaveBeenCalledWith(1);
  });

  it("처리된 항목도 보기 체크 → include_handled=true 로 재조회", async () => {
    const spy = vi.spyOn(api, "listReports").mockResolvedValue([]);
    render(<ReportTab />);
    await waitFor(() => expect(spy).toHaveBeenCalledWith(false));
    fireEvent.click(screen.getByLabelText("처리된 항목도 보기"));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(true));
  });

  it("로드 실패 시 에러 문구", async () => {
    vi.spyOn(api, "listReports").mockRejectedValue(new Error("fail"));
    render(<ReportTab />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/ReportTab.test.tsx`
Expected: FAIL 5/5 — 스텁이 `null`을 반환하므로 아무 요소도 없다.

- [ ] **Step 3: 구현**

`frontend/src/pages/Admin/ReportTab.tsx` 전체를 아래로 바꾼다:

```tsx
import { useEffect, useState } from "react";
import { listReports, markReportHandled } from "../../lib/api";
import type { AdminReportOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

export default function ReportTab() {
  const [items, setItems] = useState<AdminReportOut[]>([]);
  const [includeHandled, setIncludeHandled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    listReports(includeHandled)
      .then((data) => {
        if (active) setItems(data);
      })
      .catch(() => {
        if (active) setError("목록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [includeHandled]);

  async function handle(id: number) {
    try {
      const updated = await markReportHandled(id);
      setItems((prev) =>
        includeHandled
          ? prev.map((r) => (r.id === updated.id ? updated : r))
          : prev.filter((r) => r.id !== id),
      );
    } catch {
      setError("처리에 실패했어요. 다시 시도해주세요.");
    }
  }

  return (
    <div className={styles.wrap}>
      <label className={styles.filter}>
        <input
          type="checkbox"
          checked={includeHandled}
          onChange={(e) => setIncludeHandled(e.target.checked)}
        />
        처리된 항목도 보기
      </label>
      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>신고 · 건의 없음</p>}
      {items.map((r) => (
        <div key={r.id} className={styles.card} data-handled={r.handled}>
          <span className={styles.badge}>
            {r.type === "report" ? "신고" : "건의"}
          </span>
          {r.type === "report" && (
            <div className={styles.name}>
              대상: {r.target_name} · {r.target_university}
            </div>
          )}
          <div className={styles.university}>
            {r.type === "report" ? "신고자" : "작성자"}: {r.reporter_name} ·{" "}
            {r.reporter_university}
          </div>
          <div className={styles.when}>{r.created_at}</div>
          <p className={styles.reason}>{r.reason}</p>
          {!r.handled && <Button onClick={() => handle(r.id)}>처리 완료</Button>}
        </div>
      ))}
    </div>
  );
}
```

`items.map` 안에서 `data-handled`를 쓰는 이유: "처리된 항목도 보기"가 켜져 있을 때 처리된 카드를 흐리게 표시하기 위해서다(다음 스텝의 CSS).

- [ ] **Step 4: 스타일 추가**

`frontend/src/pages/Admin/Admin.module.css` 끝에 추가한다. 색상은 이 파일이 이미 쓰는 값과 동일하게 맞춘다:

```css
.filter {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  margin-bottom: 12px;
}

.badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: #FF7F5C;
  color: #fff;
  margin-bottom: 8px;
}

.when {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.reason {
  white-space: pre-wrap;
  margin: 0 0 12px;
}

.card[data-handled="true"] {
  opacity: 0.5;
}
```

- [ ] **Step 5: 탭 전환 테스트 추가**

`frontend/src/pages/Admin/Admin.test.tsx`의 import 줄에 `fireEvent`를 다시 넣는다:

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
```

`describe("Admin", ...)` 안 마지막에 추가한다:

```tsx
  it("신고 · 건의 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("button", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
  });
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Admin/`
Expected: `ReportTab.test.tsx` 5/5 PASS, `Admin.test.tsx` 2/2 PASS, `VerificationTab.test.tsx` 6/6 PASS

- [ ] **Step 7: 전체 확인**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run build`
Expected: 전체 PASS, tsc 무에러, 빌드 성공

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/pages/Admin/
git commit -m "feat(frontend): 관리자 신고·건의 목록 탭

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: /report 고지 문구 · 문서 정합

**Files:**
- Modify: `frontend/src/pages/Report/Report.tsx`
- Modify: `frontend/src/pages/Report/Report.test.tsx`
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트 추가**

`frontend/src/pages/Report/Report.test.tsx`의 `describe("Report", ...)` 안, 첫 번째 `it` 앞에 추가:

```tsx
  it("작성자 정보 전달 고지 문구 노출", () => {
    render(<Report />);
    expect(
      screen.getByText("작성 내용과 작성자 정보는 관리자에게 전달됩니다"),
    ).toBeInTheDocument();
  });
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Report/Report.test.tsx`
Expected: FAIL — `Unable to find an element with the text: 작성 내용과 작성자 정보는 관리자에게 전달됩니다`

- [ ] **Step 3: 고지 문구 추가**

`frontend/src/pages/Report/Report.tsx`에서 유형 선택 `</fieldset>` 바로 **뒤에** 추가한다:

```tsx
        <p className={styles.hint}>작성 내용과 작성자 정보는 관리자에게 전달됩니다</p>
```

`styles.hint`는 이미 정의돼 있다(`Report.module.css`). 새 클래스를 만들지 않는다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npm run test && npx tsc --noEmit`
Expected: 전체 PASS

- [ ] **Step 5: CLAUDE.md 미결 항목 제거**

`CLAUDE.md`의 미결 항목 표에서 아래 행을 **삭제**한다(이 작업으로 해결됐으므로):

```
| 관리자 신고 조회 | **관리자 페이지 작업 시 필수.** 신고 제출만 구현됨(`GET /admin/reports` + Admin 목록 없음) → 신고를 읽을 방법이 없음. 설계: `specs/2026-08-02-report-suggestion-design.md` §7 |
```

- [ ] **Step 6: 원 스펙 API 목록 갱신**

`docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`에서 아래 줄을 찾는다:

```
POST /reports                     -- 신고 · 건의 (type으로 구분)
```

그 **뒤에** 두 줄을 추가한다:

```
GET  /admin/reports               -- 관리자: 신고·건의 목록 (기본 미처리만)
POST /admin/reports/{id}/handle   -- 관리자: 처리 완료 표시
```

줄 번호는 참고값이다. 내용으로 찾아 확인한 뒤 수정한다. 대상 텍스트를 못 찾으면 BLOCKED로 보고한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/pages/Report/ CLAUDE.md docs/superpowers/specs/2026-05-23-datedrop-korea-design.md
git commit -m "docs: 관리자 신고 조회 반영 + /report 고지 문구

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## 완료 확인

- [ ] `cd backend && uv run pytest -v` — 106 passed
- [ ] `cd frontend && npm run test` — 신규 6개 포함 전체 PASS
- [ ] `cd frontend && npx tsc --noEmit` 무에러
- [ ] `cd frontend && npm run build` 성공
- [ ] `cd backend && uv run alembic upgrade head` 후 `downgrade -1` / `upgrade head` 정상
- [ ] `CLAUDE.md` 미결 항목에서 "관리자 신고 조회" 행이 사라졌는지 확인
- [ ] 브라우저 확인(`npm run dev`): `/admin` → 탭 전환 → 신고 목록 → 처리 완료 → 목록에서 사라짐 → "처리된 항목도 보기" 체크 시 다시 나타남

## 범위 밖 (건드리지 않음)

- 제재 조치(경고·정지) — 제재 정책이 팀 미결
- 처리 되돌리기(`unhandle`), 신고 삭제 API, 페이징, `handled_at`/`handled_by`
- PostgreSQL 실환경 마이그레이션 검증 — 배포 전 스테이징에서 별도 수행
