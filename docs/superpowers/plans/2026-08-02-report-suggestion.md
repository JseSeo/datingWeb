# 신고 & 건의 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유저가 부적절 유저를 신고하거나 서비스에 건의할 수 있는 `/report` 페이지를 만들고, 그에 맞게 `Report` 모델·API를 개편한다.

**Architecture:** `Report`의 대상 지정을 `target_id` FK에서 `target_name`/`target_university` 텍스트로 바꾸고 `type` 컬럼(`report`/`suggestion`)을 추가한다. 신고/건의는 한 테이블·한 엔드포인트를 공유하며, "신고면 대상 필수 / 건의면 대상 무시"는 API 검증으로 강제한다. 프론트는 유형 라디오로 분기하는 단일 폼 페이지.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 · Alembic · pytest / React 18 · Vite · React Router 6 · vitest · @testing-library/react

**설계 문서:** `docs/superpowers/specs/2026-08-02-report-suggestion-design.md`

## Global Constraints

- 대상 이름·학교는 **strip 후 저장**. 붉은실(`models/game.py:44-45`)과 동일하게 `String(100)`, 컬럼명도 `target_name`·`target_university`로 통일.
- 에러 메시지 진실원은 백엔드. 프론트는 `ApiError.message`를 그대로 노출하고 자체 문구를 만들지 않는다.
- 검증 실패 문구 3종(정확히 이 문자열):
  - `"내용을 입력하세요"`
  - `"신고 대상의 이름과 학교를 입력하세요"`
  - `"자기 자신을 신고할 수 없습니다"`
- 인증은 `get_current_user` (인증 대기 유저도 제출 가능). 프론트 라우트도 `requireStatus` 없이 `<ProtectedRoute>`만.
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- ⛔ 매칭 알고리즘 관련 코드 금지. 관리자 조회(`GET /admin/reports`)는 이번 범위 밖.

**명령어**
- 백엔드: `cd backend && uv run pytest -v`
- 프론트: `cd frontend && npm run test` / `npx tsc --noEmit` / `npm run build`
- 마이그레이션: `cd backend && uv run alembic revision --autogenerate -m "..."` → `uv run alembic upgrade head`

---

## File Structure

| 파일 | 책임 | 작업 |
|---|---|---|
| `backend/app/models/report.py` | Report ORM + ReportType enum | 수정 |
| `backend/app/models/__init__.py` | 모델 re-export | 수정 |
| `backend/app/schemas/report.py` | 요청·응답 스키마 | 수정 |
| `backend/app/api/reports.py` | POST /reports 검증·저장 | 수정 |
| `backend/tests/test_reports.py` | 백엔드 테스트 | 재작성 |
| `backend/alembic/versions/<rev>_report_type_target_text.py` | 스키마 마이그레이션 | 생성 |
| `frontend/src/lib/types.ts` | 공용 타입 | 수정 |
| `frontend/src/lib/api.ts` | `submitReport()` | 수정 |
| `frontend/src/pages/Report/Report.tsx` | 신고·건의 폼 | 생성 |
| `frontend/src/pages/Report/Report.module.css` | 폼 스타일 | 생성 |
| `frontend/src/pages/Report/Report.test.tsx` | 폼 테스트 | 생성 |
| `frontend/src/App.tsx` | `/report` 라우트 | 수정 |
| `frontend/src/pages/MyPage/MyPage.tsx` | 진입 행 | 수정 |
| `frontend/src/pages/MyPage/MyPage.test.tsx` | 진입 테스트 | 수정 |
| `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md` | 원 스펙 정합 | 수정 |

---

## Task 1: 백엔드 모델 · 스키마 · 엔드포인트

`target_id` FK를 텍스트 대상 + `type`으로 교체한다. 모델·스키마·엔드포인트가 서로 물려 있어 한 태스크로 묶는다 (중간 상태에서는 기존 테스트가 깨진 채로 남기 때문).

**Files:**
- Modify: `backend/app/models/report.py`
- Modify: `backend/app/models/__init__.py:6,14`
- Modify: `backend/app/schemas/report.py`
- Modify: `backend/app/api/reports.py`
- Test: `backend/tests/test_reports.py` (전면 재작성)

**Interfaces:**
- Produces: `ReportType` enum (`report`/`suggestion`), `Report` 모델(`reporter_id`, `type`, `target_name`, `target_university`, `reason`, `created_at`), `POST /reports` 계약
- Consumes: 없음 (첫 태스크)

- [ ] **Step 1: 기존 테스트를 새 계약으로 재작성**

`backend/tests/test_reports.py` 전체를 아래로 교체한다. 기존 테스트는 `target_id`를 쓰므로 그대로 두면 의미가 없다.

```python
from fastapi.testclient import TestClient


def _register_and_get_headers(
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


def test_create_report_strips_target(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "  대상자  ",
        "target_university": "  연세대학교  ",
        "reason": "부적절한 프로필 사진",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "report"
    assert data["target_name"] == "대상자"
    assert data["target_university"] == "연세대학교"
    assert data["reason"] == "부적절한 프로필 사진"
    assert "id" in data
    assert "created_at" in data


def test_report_requires_target(client: TestClient):
    headers = _register_and_get_headers(client, "r2@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "   ",
        "reason": "학교를 안 적음",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "신고 대상의 이름과 학교를 입력하세요"


def test_suggestion_ignores_target(client: TestClient):
    headers = _register_and_get_headers(client, "r3@test.com")
    response = client.post("/reports", json={
        "type": "suggestion",
        "target_name": "무시되어야 함",
        "target_university": "무시되어야 함",
        "reason": "알림을 꺼두는 기능이 있으면 좋겠어요",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "suggestion"
    assert data["target_name"] is None
    assert data["target_university"] is None


def test_report_blank_reason(client: TestClient):
    headers = _register_and_get_headers(client, "r4@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": "   ",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "내용을 입력하세요"


def test_report_self_forbidden(client: TestClient):
    headers = _register_and_get_headers(
        client, "self@test.com", name="자기자신", university="고려대학교",
    )
    response = client.post("/reports", json={
        "type": "report",
        "target_name": " 자기자신 ",
        "target_university": " 고려대학교 ",
        "reason": "자기신고",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "자기 자신을 신고할 수 없습니다"


def test_report_unauthorized(client: TestClient):
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": "x",
    })
    assert response.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_reports.py -v`
Expected: FAIL — `type` 필드를 모르는 스키마라 422가 나오거나, `target_id` 누락으로 422. 6개 중 최소 5개 실패.

- [ ] **Step 3: 모델 교체**

`backend/app/models/report.py` 전체를 교체:

```python
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ReportType(str, enum.Enum):
    report = "report"
    suggestion = "suggestion"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, name="report_type"), nullable=False
    )
    target_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_university: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 4: 모델 re-export 갱신**

`backend/app/models/__init__.py` — `backend/CLAUDE.md` 규칙상 필수.

6번 줄을 이렇게 바꾼다:
```python
from app.models.report import Report, ReportType
```

14번 줄을 이렇게 바꾼다:
```python
    "Report", "ReportType",
```

- [ ] **Step 5: 스키마 교체**

`backend/app/schemas/report.py` 전체를 교체:

```python
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.report import ReportType


class ReportCreate(BaseModel):
    type: ReportType
    target_name: str | None = Field(default=None, max_length=100)
    target_university: str | None = Field(default=None, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


class ReportOut(BaseModel):
    id: int
    type: ReportType
    target_name: str | None
    target_university: str | None
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

`reason`에 `min_length=1`을 남겨두는 이유: 빈 문자열 `""`은 pydantic이 422로 막고, 공백뿐인 문자열은 통과시킨 뒤 엔드포인트가 400으로 막는다. 두 층이 각각 다른 경우를 담당한다.

- [ ] **Step 6: 엔드포인트 교체**

`backend/app/api/reports.py` 전체를 교체:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.report import Report, ReportType
from app.models.user import User
from app.schemas.report import ReportCreate, ReportOut

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="내용을 입력하세요",
        )

    name: str | None = (payload.target_name or "").strip()
    university: str | None = (payload.target_university or "").strip()

    if payload.type == ReportType.suggestion:
        # 건의는 대상이 없다. 클라이언트가 무엇을 보내든 버린다.
        name = None
        university = None
    else:
        if not name or not university:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="신고 대상의 이름과 학교를 입력하세요",
            )
        if (
            name == current_user.name.strip()
            and university == current_user.university.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="자기 자신을 신고할 수 없습니다",
            )

    report = Report(
        reporter_id=current_user.id,
        type=payload.type,
        target_name=name,
        target_university=university,
        reason=reason,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_reports.py -v`
Expected: PASS 6/6

- [ ] **Step 8: 백엔드 전체 회귀 확인**

Run: `cd backend && uv run pytest -v`
Expected: 전부 PASS. 실패가 있으면 `Report`를 참조하는 다른 코드가 있다는 뜻이므로 그 파일을 고친다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/models/report.py backend/app/models/__init__.py backend/app/schemas/report.py backend/app/api/reports.py backend/tests/test_reports.py
git commit -m "feat(backend): 신고/건의 type 컬럼 + 대상 이름·학교 텍스트화

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: 마이그레이션

**Files:**
- Create: `backend/alembic/versions/<자동생성>_report_type_target_text.py`

**Interfaces:**
- Consumes: Task 1의 `Report` 모델
- Produces: 없음 (스키마 반영만)

- [ ] **Step 1: 기존 데이터 확인**

`reports` 테이블에 행이 있으면 `type`을 무엇으로 채울지 결정이 필요하다. 먼저 센다.

Run: `cd backend && uv run python -c "from app.database import SessionLocal; from sqlalchemy import text; print(SessionLocal().execute(text('SELECT count(*) FROM reports')).scalar())"`

Expected: `0`

**0이 아니면 여기서 멈추고 사용자에게 처리 방침을 묻는다.** (`User.gender`에서 `server_default="male"`로 기존 행을 일괄 male 처리한 탓에 백필 숙제가 남았다. 같은 실수를 반복하지 않는다.)

- [ ] **Step 2: 리비전 자동생성**

Run: `cd backend && uv run alembic revision --autogenerate -m "report type and text target"`

- [ ] **Step 3: 생성된 파일 대조·수정**

생성된 파일의 `upgrade`/`downgrade`가 아래와 일치하는지 확인하고, 다르면 맞춘다. 특히 autogenerate가 `target_id` FK 제약 삭제를 빠뜨리는 경우가 있다.

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column("type", sa.Enum("report", "suggestion", name="report_type"), nullable=False),
    )
    op.add_column("reports", sa.Column("target_name", sa.String(length=100), nullable=True))
    op.add_column(
        "reports", sa.Column("target_university", sa.String(length=100), nullable=True)
    )
    op.drop_column("reports", "target_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("reports", sa.Column("target_id", sa.Integer(), nullable=False))
    op.drop_column("reports", "target_university")
    op.drop_column("reports", "target_name")
    op.drop_column("reports", "type")
    sa.Enum(name="report_type").drop(op.get_bind(), checkfirst=True)
```

`type`에 `server_default`를 **넣지 않는다.** Step 1에서 테이블이 비었음을 확인했으므로 필요 없고, 넣으면 나중에 뜻 모를 기본값이 남는다.

- [ ] **Step 4: 양방향 동작 확인**

Run:
```bash
cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
```
Expected: 세 명령 모두 에러 없이 완료.

- [ ] **Step 5: 마이그레이션 후 테스트 재확인**

Run: `cd backend && uv run pytest -v`
Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/alembic/versions/
git commit -m "feat(backend): reports 스키마 마이그레이션 (type, target 텍스트)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: 프론트 타입 + API 함수

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts:1-14` (import), 파일 끝(함수 추가)

**Interfaces:**
- Consumes: Task 1의 `POST /reports` 계약
- Produces: `ReportType`, `ReportPayload`, `ReportOut` 타입 / `submitReport(payload: ReportPayload): Promise<ReportOut>`

- [ ] **Step 1: 타입 추가**

`frontend/src/lib/types.ts` 끝에 추가:

```ts
export type ReportType = "report" | "suggestion";

export interface ReportPayload {
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
}

export interface ReportOut {
  id: number;
  type: ReportType;
  target_name: string | null;
  target_university: string | null;
  reason: string;
  created_at: string;
}
```

- [ ] **Step 2: api 함수 추가**

`frontend/src/lib/api.ts`의 import 목록(1~14줄)에 두 줄 추가:

```ts
  ReportPayload,
  ReportOut,
```

파일 끝에 함수 추가:

```ts
export function submitReport(payload: ReportPayload): Promise<ReportOut> {
  return apiFetch<ReportOut>("/reports", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 3: 타입체크**

Run: `cd frontend && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat(frontend): 신고/건의 타입 + submitReport API

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Report 페이지

**Files:**
- Create: `frontend/src/pages/Report/Report.tsx`
- Create: `frontend/src/pages/Report/Report.module.css`
- Test: `frontend/src/pages/Report/Report.test.tsx`

**Interfaces:**
- Consumes: Task 3의 `submitReport`, `ReportType`
- Produces: `export default function Report()` — props 없음

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/pages/Report/Report.test.tsx` 생성:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Report from "./Report";
import * as api from "../../lib/api";

beforeEach(() => vi.clearAllMocks());

const HINT = /대상을 특정할 수 있는 정보/;

describe("Report", () => {
  it("초기 상태: 유형 미선택이면 제출 버튼 비활성", () => {
    render(<Report />);
    expect(screen.getByRole("button", { name: "제출" })).toBeDisabled();
  });

  it("신고 선택 시 대상 입력칸 + 안내문 노출", () => {
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    expect(screen.getByLabelText("신고 대상 이름")).toBeInTheDocument();
    expect(screen.getByLabelText("신고 대상 학교")).toBeInTheDocument();
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "제출" })).toBeEnabled();
  });

  it("건의 선택 시 대상 입력칸 사라짐", () => {
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.click(screen.getByLabelText("건의"));
    expect(screen.queryByLabelText("신고 대상 이름")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("신고 대상 학교")).not.toBeInTheDocument();
    expect(screen.queryByText(HINT)).not.toBeInTheDocument();
  });

  it("신고 제출 성공: strip된 값 전송 + 완료 문구 + 폼 초기화", async () => {
    const spy = vi.spyOn(api, "submitReport").mockResolvedValue({
      id: 1, type: "report", target_name: "대상자",
      target_university: "연세대학교", reason: "사유",
      created_at: "2026-08-02T00:00:00",
    });
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.change(screen.getByLabelText("신고 대상 이름"), {
      target: { value: "  대상자  " },
    });
    fireEvent.change(screen.getByLabelText("신고 대상 학교"), {
      target: { value: "  연세대학교  " },
    });
    fireEvent.change(screen.getByLabelText("내용"), { target: { value: "사유" } });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() =>
      expect(screen.getByText("접수되었습니다")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith({
      type: "report",
      target_name: "대상자",
      target_university: "연세대학교",
      reason: "사유",
    });
    expect(screen.getByLabelText("내용")).toHaveValue("");
    expect(screen.getByRole("button", { name: "제출" })).toBeDisabled();
  });

  it("건의 제출: 대상 필드는 null로 전송", async () => {
    const spy = vi.spyOn(api, "submitReport").mockResolvedValue({
      id: 2, type: "suggestion", target_name: null,
      target_university: null, reason: "건의합니다",
      created_at: "2026-08-02T00:00:00",
    });
    render(<Report />);
    fireEvent.click(screen.getByLabelText("건의"));
    fireEvent.change(screen.getByLabelText("내용"), {
      target: { value: "건의합니다" },
    });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith({
      type: "suggestion",
      target_name: null,
      target_university: null,
      reason: "건의합니다",
    }));
  });

  it("서버 400이면 백엔드 문구를 그대로 표시", async () => {
    vi.spyOn(api, "submitReport").mockRejectedValue(
      new api.ApiError(400, "신고 대상의 이름과 학교를 입력하세요"),
    );
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.change(screen.getByLabelText("내용"), { target: { value: "사유" } });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() =>
      expect(
        screen.getByText("신고 대상의 이름과 학교를 입력하세요"),
      ).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Report/Report.test.tsx`
Expected: FAIL — `Failed to resolve import "./Report"` (파일 없음)

- [ ] **Step 3: 페이지 구현**

`frontend/src/pages/Report/Report.tsx` 생성:

```tsx
import { useState, type FormEvent } from "react";
import { submitReport, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import type { ReportType } from "../../lib/types";
import styles from "./Report.module.css";

export default function Report() {
  const [type, setType] = useState<ReportType | "">("");
  const [targetName, setTargetName] = useState("");
  const [targetUniversity, setTargetUniversity] = useState("");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"" | "sending" | "sent" | "error">("");
  const [error, setError] = useState("");

  const isReport = type === "report";

  function selectType(next: ReportType) {
    setType(next);
    setStatus("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!type) return;
    setStatus("sending");
    setError("");
    try {
      await submitReport({
        type,
        target_name: isReport ? targetName.trim() : null,
        target_university: isReport ? targetUniversity.trim() : null,
        reason,
      });
      setStatus("sent");
      setType("");
      setTargetName("");
      setTargetUniversity("");
      setReason("");
    } catch (err) {
      setStatus("error");
      setError(err instanceof ApiError ? err.message : "접수에 실패했습니다");
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>신고 &amp; 건의</h1>
      <form onSubmit={handleSubmit}>
        <fieldset className={styles.type}>
          <legend>유형</legend>
          <label>
            <input type="radio" name="type" checked={type === "report"}
              onChange={() => selectType("report")} /> 신고
          </label>
          <label>
            <input type="radio" name="type" checked={type === "suggestion"}
              onChange={() => selectType("suggestion")} /> 건의
          </label>
        </fieldset>

        {isReport && (
          <>
            <Input id="target-name" label="신고 대상 이름" value={targetName}
              maxLength={100}
              onChange={(e) => setTargetName(e.target.value)} />
            <Input id="target-university" label="신고 대상 학교" value={targetUniversity}
              maxLength={100}
              onChange={(e) => setTargetUniversity(e.target.value)} />
            <p className={styles.hint}>
              학과·학번·인스타 아이디 등 대상을 특정할 수 있는 정보를 본문에 함께 적어주세요
            </p>
          </>
        )}

        <label htmlFor="reason" className={styles.label}>내용</label>
        <textarea id="reason" className={styles.textarea} value={reason}
          maxLength={2000}
          placeholder={isReport ? "신고 사유를 적어주세요" : "건의 내용을 적어주세요"}
          onChange={(e) => setReason(e.target.value)} />

        {status === "sent" && <p className={styles.ok}>접수되었습니다</p>}
        {status === "error" && <p className={styles.error}>{error}</p>}

        <Button type="submit" disabled={!type || status === "sending"}>
          {status === "sending" ? "전송 중..." : "제출"}
        </Button>
      </form>
    </div>
  );
}
```

라디오 `<label>`이 텍스트를 감싸고 있어 `getByLabelText("신고")`로 잡힌다. `Input` 컴포넌트는 `htmlFor`/`id`로 라벨을 연결한다(`components/Input/Input.tsx:11-12`).

- [ ] **Step 4: 스타일 작성**

`frontend/src/pages/Report/Report.module.css` 생성. 색상은 토큰 변수만 쓴다(`frontend/CLAUDE.md` 규칙).

```css
.wrap { max-width: var(--container-max); margin: 0 auto; padding: var(--space); }

.title { font-size: 22px; margin-bottom: var(--space); color: var(--color-primary); }

.type {
  border: none;
  padding: 0;
  margin: 0 0 var(--space);
}

.type legend {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.type label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: var(--space);
}

.hint {
  font-size: 12px;
  color: var(--color-secondary);
  margin: 0 0 var(--space);
}

.label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.textarea {
  width: 100%;
  min-height: 140px;
  padding: 8px;
  border: 1px solid var(--color-secondary);
  border-radius: var(--radius);
  font: inherit;
  resize: vertical;
  margin-bottom: var(--space);
}

.ok { color: var(--color-primary); font-weight: 600; margin-bottom: 8px; }

.error { color: var(--color-error); font-size: 14px; margin-bottom: 8px; }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Report/Report.test.tsx`
Expected: PASS 6/6

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/pages/Report/
git commit -m "feat(frontend): 신고·건의 폼 페이지

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: 라우트 + MyPage 진입

**Files:**
- Modify: `frontend/src/App.tsx:11`(import), `:63-70` 뒤(라우트 추가)
- Modify: `frontend/src/pages/MyPage/MyPage.tsx:83-90`
- Test: `frontend/src/pages/MyPage/MyPage.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `Report` 페이지 컴포넌트
- Produces: `/report` 경로

- [ ] **Step 1: 실패하는 테스트 추가**

`frontend/src/pages/MyPage/MyPage.test.tsx`의 `describe("MyPage", ...)` 블록 안, 마지막 `it` 뒤에 추가:

```tsx
  it("신고 & 건의 클릭 시 /report 이동", () => {
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /신고 & 건의/ }));
    expect(navigate).toHaveBeenCalledWith("/report");
  });
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/MyPage/MyPage.test.tsx`
Expected: FAIL — `Unable to find an accessible element with the role "button" and name /신고 & 건의/`

- [ ] **Step 3: MyPage에 진입 행 추가**

`frontend/src/pages/MyPage/MyPage.tsx` — 로그아웃 버튼과 회원 탈퇴 버튼 사이(`:86`과 `:87` 사이)에 삽입:

```tsx
        <button className={styles.row} onClick={() => navigate("/report")}>
          <span>신고 &amp; 건의</span><span>›</span>
        </button>
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/MyPage/MyPage.test.tsx`
Expected: PASS

- [ ] **Step 5: 라우트 등록**

`frontend/src/App.tsx` — 11번 줄 `import Admin ...` 아래에 추가:

```tsx
import Report from "./pages/Report/Report";
```

`/profile` 라우트 블록(`:63-70`) 바로 뒤에 추가:

```tsx
      <Route
        path="/report"
        element={
          <ProtectedRoute>
            <Report />
          </ProtectedRoute>
        }
      />
```

`requireStatus`를 붙이지 않는다 — 백엔드가 `get_current_user`라 인증 대기 유저도 제출할 수 있어야 한다.

- [ ] **Step 6: 전체 확인**

Run: `cd frontend && npm run test && npx tsc --noEmit && npm run build`
Expected: 전체 PASS, tsc 무에러, 빌드 성공

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/App.tsx frontend/src/pages/MyPage/
git commit -m "feat(frontend): /report 라우트 + 마이페이지 진입

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: 원 스펙 정합

`CLAUDE.md` 규칙 — 스펙이 진실. 코드가 바뀌었으니 스펙을 맞춘다.

**Files:**
- Modify: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md:142-143`, `:172`

**Interfaces:**
- Consumes: Task 1의 최종 모델·API
- Produces: 없음

- [ ] **Step 1: Report 모델 절 갱신**

142~143번 줄:

```
Report
  id, reporter_id, target_id, reason, created_at
```

을 이렇게 바꾼다:

```
Report
  id, reporter_id, type, target_name, target_university, reason, created_at
  -- type = report | suggestion
  -- 건의(suggestion)는 target_name·target_university = null
  -- target_name·target_university 는 strip 후 저장
```

- [ ] **Step 2: API 목록 갱신**

172번 줄:

```
POST /reports                     -- 신고
```

을 이렇게 바꾼다:

```
POST /reports                     -- 신고 · 건의 (type으로 구분)
```

- [ ] **Step 3: 커밋**

```bash
git add docs/superpowers/specs/2026-05-23-datedrop-korea-design.md
git commit -m "docs(spec): Report 모델·API 절을 신고/건의 설계에 맞춤

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## 완료 확인

- [ ] `cd backend && uv run pytest -v` 전부 PASS
- [ ] `cd frontend && npm run test` 전부 PASS
- [ ] `cd frontend && npx tsc --noEmit` 무에러
- [ ] `cd frontend && npm run build` 성공
- [ ] `cd backend && uv run alembic upgrade head` 후 `downgrade -1` / `upgrade head` 정상
- [ ] 브라우저 확인(`npm run dev`): `/mypage` → "신고 & 건의" → 유형 전환 시 대상 입력칸 나타났다 사라지는지

## 범위 밖 (건드리지 않음)

- `GET /admin/reports` 및 관리자 조회 화면 — `CLAUDE.md` 미결 항목에 등재됨
- 대상 자동완성 — 설계안 §6에서 기각
- `MyPage.tsx:71-73` "가치관 설문 준비중" 잔여물 — 이 작업 종료 후 별건으로 처리
