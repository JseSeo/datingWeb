# `/home` 화면 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/home`에 다음 매칭 라운드의 D-day와 유저의 매칭 참여 가능 여부를 표시한다.

**Architecture:** 백엔드에 읽기 전용 엔드포인트 `GET /match-rounds/next`를 추가한다(가장 이른 미래 `pending` 라운드 또는 `null`). 프론트는 이 엔드포인트와 기존 `GET /me/survey`를 `Promise.allSettled`로 병렬 호출하고, `matching_paused`는 이미 auth 컨텍스트에 있는 `user`에서 읽는다. D-day는 KST 달력 날짜 차이로 계산하는 순수 함수가 담당한다.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + pytest / React 19 + Vite + TypeScript + Vitest + Testing Library

**Spec:** `docs/superpowers/specs/2026-08-11-home-screen-design.md`

## Global Constraints

- 매칭 알고리즘 관련 코드 금지. `Match` 테이블을 읽거나 쓰지 않는다. `MatchRound`만 **읽기**로 다룬다
- 매칭 요일/시간을 코드에 하드코딩하지 않는다. `scheduled_at`을 DB에서 읽기만 한다
- 대학 목록 하드코딩 금지
- 색상은 `frontend/src/styles/tokens.css`의 토큰만 사용: `--color-bg` `#FFF5E6`, `--color-primary` `#FF7F5C`, `--color-secondary` `#FF9472`, `--color-text` `#2B2B2B`, `--color-error` `#D64545`. 임의 색상 금지 (회색 `#666`은 기존 페이지에서 쓰이므로 허용)
- API URL 하드코딩 금지. `lib/api.ts`의 `apiFetch`만 사용
- 백엔드 엔드포인트는 Pydantic 스키마로 응답한다. dict 반환 금지
- 프론트 수정 시 `npm run lint`를 직접 실행한다 (build/test와 분리돼 있어 자동으로 안 돌아감)
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **push 금지.** 브랜치 `feat/home-screen`에 커밋만 한다

---

### Task 1: 백엔드 — 다음 라운드 조회 엔드포인트

**Files:**
- Create: `backend/tests/test_rounds.py`
- Create: `backend/app/schemas/round.py`
- Create: `backend/app/api/rounds.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: 기존 `app.models.match.MatchRound`, `RoundStatus`; `app.core.deps.get_current_user`; `app.database.get_db`
- Produces: `GET /match-rounds/next` → `MatchRoundOut | null`, `MatchRoundOut = { id: int, scheduled_at: datetime }`

`MatchRound`는 `app/models/__init__.py`에 이미 re-export 돼 있다. 모델을 추가하지 않으므로 그 파일은 건드리지 않는다. `app/schemas/__init__.py`는 비어 있는 파일이며 다른 스키마도 re-export하지 않으므로 마찬가지로 건드리지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_rounds.py` 생성:

```python
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import MatchRound, RoundStatus
from tests.conftest import TestingSessionLocal


def _register_and_get_headers(client: TestClient, email: str = "round@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김라운드",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _add_rounds(*rounds: MatchRound) -> None:
    db = TestingSessionLocal()
    db.add_all(rounds)
    db.commit()
    db.close()


def _hours(n: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=n)


def test_returns_nearest_future_pending_round(client: TestClient):
    headers = _register_and_get_headers(client)
    _add_rounds(
        MatchRound(scheduled_at=_hours(72), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(24), status=RoundStatus.pending),
        MatchRound(scheduled_at=_hours(48), status=RoundStatus.pending),
    )
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    # 가장 이른 것 = 24시간 뒤
    assert data["scheduled_at"].startswith(_hours(24).strftime("%Y-%m-%dT%H"))
    # 절단선: 결과 영역 필드는 내려가지 않는다
    assert set(data.keys()) == {"id", "scheduled_at"}


def test_returns_null_when_no_rounds(client: TestClient):
    headers = _register_and_get_headers(client, "none@test.com")
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_ignores_past_pending_round(client: TestClient):
    headers = _register_and_get_headers(client, "past@test.com")
    _add_rounds(MatchRound(scheduled_at=_hours(-1), status=RoundStatus.pending))
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_ignores_done_round(client: TestClient):
    headers = _register_and_get_headers(client, "done@test.com")
    _add_rounds(MatchRound(
        scheduled_at=_hours(24),
        executed_at=datetime.utcnow(),
        status=RoundStatus.done,
    ))
    response = client.get("/match-rounds/next", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


def test_requires_auth(client: TestClient):
    response = client.get("/match-rounds/next")
    assert response.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/test_rounds.py -v`
Expected: FAIL — 5건 모두 404 (라우트 없음). `test_requires_auth`도 401이 아니라 404로 실패해야 정상이다.

- [ ] **Step 3: 스키마 작성**

`backend/app/schemas/round.py` 생성:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: 라우터 작성**

`backend/app/api/rounds.py` 생성:

```python
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.match import MatchRound, RoundStatus
from app.models.user import User
from app.schemas.round import MatchRoundOut

router = APIRouter(prefix="/match-rounds", tags=["rounds"])


@router.get("/next", response_model=MatchRoundOut | None)
def get_next_round(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """다음에 실행될 매칭 라운드. 예정된 것이 없으면 null."""
    return (
        db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.pending,
            MatchRound.scheduled_at >= datetime.utcnow(),
        )
        .order_by(MatchRound.scheduled_at.asc())
        .first()
    )
```

- [ ] **Step 5: 라우터 등록**

`backend/app/api/router.py` 수정. import 줄에 `rounds`를 추가하고, `include_router` 한 줄을 추가한다:

```python
from fastapi import APIRouter
from app.api import auth, game, me, reports, rounds, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
router.include_router(reports.router)
router.include_router(game.router)
router.include_router(rounds.router)
router.include_router(reports.admin_router)
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/test_rounds.py -v`
Expected: PASS 5건

- [ ] **Step 7: 백엔드 전체 회귀 확인**

Run: `cd backend && uv run pytest`
Expected: 기존 테스트 전부 PASS. 실패가 있으면 이 태스크의 변경 때문인지 먼저 확인한다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/schemas/round.py backend/app/api/rounds.py backend/app/api/router.py backend/tests/test_rounds.py
git commit -m "feat(backend): 다음 매칭 라운드 조회 엔드포인트

GET /match-rounds/next — 가장 이른 미래 pending 라운드 또는 null.
과거 pending과 done 라운드는 제외한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: 프론트 — `daysUntilKST` 유틸

**Files:**
- Modify: `frontend/src/lib/datetime.ts`
- Modify: `frontend/src/lib/datetime.test.ts`

**Interfaces:**
- Consumes: 같은 파일의 기존 `TZ_SUFFIX` 상수
- Produces: `daysUntilKST(iso: string, now?: Date): number | null`

**계산 규칙:** 시각 차이가 아니라 **KST 달력 날짜 차이**를 반환한다. "D-1"은 24시간 후가 아니라 *내일*을 뜻한다. 반환값은 음수일 수 있다 — 숨김 판정은 이 함수가 아니라 호출부(`Home`)가 한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/datetime.test.ts`의 1번째 줄 import를 `import { formatKST, daysUntilKST } from "./datetime";`로 바꾸고, 파일 끝(기존 `describe("formatKST", ...)` 블록 뒤)에 아래를 추가한다:

```ts
describe("daysUntilKST", () => {
  it("3일 뒤면 3", () => {
    expect(
      daysUntilKST("2026-08-14T12:00:00", new Date("2026-08-11T12:00:00Z")),
    ).toBe(3);
  });

  it("같은 KST 날짜면 0", () => {
    expect(
      daysUntilKST("2026-08-11T12:00:00", new Date("2026-08-11T00:00:00Z")),
    ).toBe(0);
  });

  it("UTC로는 같은 날이어도 KST로 날짜가 넘어가면 1", () => {
    // 대상: UTC 08-11 15:00 = KST 08-12 00:00
    // 기준: UTC 08-11 14:00 = KST 08-11 23:00
    expect(
      daysUntilKST("2026-08-11T15:00:00Z", new Date("2026-08-11T14:00:00Z")),
    ).toBe(1);
  });

  it("과거 시각이면 음수", () => {
    expect(
      daysUntilKST("2026-08-10T12:00:00", new Date("2026-08-11T12:00:00Z")),
    ).toBe(-1);
  });

  it("파싱 불가한 입력은 null", () => {
    expect(daysUntilKST("어제", new Date("2026-08-11T12:00:00Z"))).toBeNull();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: FAIL — `daysUntilKST is not a function` 또는 타입 에러

- [ ] **Step 3: 구현**

`frontend/src/lib/datetime.ts` 끝에 추가한다. 기존 `TZ_SUFFIX`와 `formatKST`는 건드리지 않는다:

```ts
// en-CA 로케일은 YYYY-MM-DD 형태를 준다 — 날짜만 비교하기 위해 사용.
const KST_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** KST 자정 기준 UTC 밀리초. 날짜만 비교하려고 시각을 버린다. */
function kstDayStart(date: Date): number {
  const [year, month, day] = KST_DATE.format(date).split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

/**
 * KST 달력 기준 남은 "날짜" 수. 시각 차이가 아니라 날짜 차이다.
 * 과거면 음수. 파싱 실패하면 null.
 */
export function daysUntilKST(iso: string, now: Date = new Date()): number | null {
  const target = new Date(TZ_SUFFIX.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(target.getTime())) return null;
  const MS_PER_DAY = 86_400_000;
  return Math.round((kstDayStart(target) - kstDayStart(now)) / MS_PER_DAY);
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/lib/datetime.test.ts`
Expected: PASS 10건 (기존 `formatKST` 5건 + 신규 5건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/datetime.ts frontend/src/lib/datetime.test.ts
git commit -m "feat(frontend): KST 달력 기준 D-day 계산 유틸

daysUntilKST — 시각 차이가 아니라 KST 날짜 차이를 반환한다.
now를 주입받아 테스트가 시스템 시계에 묶이지 않게 한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: 프론트 — `/home` 화면

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/Home/Home.tsx`
- Create: `frontend/src/pages/Home/Home.module.css`
- Create: `frontend/src/pages/Home/Home.test.tsx`

**Interfaces:**
- Consumes: Task 2의 `daysUntilKST(iso, now?)`; 기존 `formatKST(iso)`, `getSurvey()`(`lib/api.ts:180`), `useAuth()`, Task 1의 `GET /match-rounds/next`
- Produces: `MatchRoundOut = { id: number; scheduled_at: string }`, `getNextRound(): Promise<MatchRoundOut | null>`

**패턴 참고:** 이 코드베이스의 페이지는 전부 `useNavigate` + `<button>`으로 이동한다 (`Link`를 쓰는 페이지가 없다). 그대로 따른다. 테스트도 `MyPage.test.tsx`의 `useAuth`/`useNavigate` mock 패턴을 따른다.

**상태 판정:**

| 상황 | 화면 |
|---|---|
| 설문 조회 성공 + `updated_at === null` | ⚠ 설문 경고 + `/survey` 버튼 |
| `user.matching_paused === true` | ⏸ 일시정지 경고 + `/mypage` 버튼 |
| 둘 다 아님 | ✓ 매칭 참여 중 |
| **설문 조회 실패** | 설문 경고를 숨긴다. "참여 중"도 띄우지 않는다 (오탐 방지) |

- [ ] **Step 1: 타입과 API 함수 추가**

`frontend/src/lib/types.ts` 끝에 추가:

```ts
export interface MatchRoundOut {
  id: number;
  scheduled_at: string;
}
```

`frontend/src/lib/api.ts`의 import 목록(1~17줄) 맨 끝 항목 뒤에 `MatchRoundOut,`을 추가하고, 파일 끝에 함수를 추가한다:

```ts
export function getNextRound(): Promise<MatchRoundOut | null> {
  return apiFetch<MatchRoundOut | null>("/match-rounds/next", { method: "GET" });
}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`frontend/src/pages/Home/Home.test.tsx` 생성:

```tsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "./Home";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김홈", university: "서울대학교",
  gender: "male" as const, status: "active" as const, profile_photo: null,
  bio: null, instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

let currentUser = { ...user };
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user: currentUser, logout: vi.fn(), refreshUser: vi.fn() }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

const SURVEY_DONE = { answers: { responses: {}, absolute: [] }, updated_at: "2026-08-01T00:00:00" };
const SURVEY_EMPTY = { answers: {}, updated_at: null };

beforeEach(() => {
  vi.clearAllMocks();
  currentUser = { ...user };
  // Home은 daysUntilKST를 now 없이 호출하므로 시계를 고정해야 D-3이 확정된다.
  // shouldAdvanceTime이 없으면 findBy*의 대기 타이머가 멈춰 타임아웃 난다.
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-08-11T12:00:00Z"));
});

afterEach(() => vi.useRealTimers());

function renderHome() {
  render(<MemoryRouter><Home /></MemoryRouter>);
}

describe("Home", () => {
  it("라운드가 있으면 D-day와 예정 일시 표시", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({
      id: 1, scheduled_at: "2026-08-14T12:00:00",
    });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText("D-3")).toBeInTheDocument();
    expect(screen.getByText("2026-08-14 21:00")).toBeInTheDocument();
  });

  it("라운드가 없으면 빈 상태 문구", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText("아직 예정된 매칭이 없어요")).toBeInTheDocument();
  });

  it("설문 미완이면 경고와 설문 이동 버튼", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_EMPTY);
    renderHome();
    const button = await screen.findByRole("button", { name: /설문 하러가기/ });
    fireEvent.click(button);
    expect(navigate).toHaveBeenCalledWith("/survey");
  });

  it("일시정지면 경고와 마이페이지 이동 버튼", async () => {
    currentUser = { ...user, matching_paused: true };
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    const button = await screen.findByRole("button", { name: /해제/ });
    fireEvent.click(button);
    expect(navigate).toHaveBeenCalledWith("/mypage");
  });

  it("설문 완료 + 일시정지 아님이면 참여 중 표시", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText(/매칭 참여 중/)).toBeInTheDocument();
  });

  it("라운드 조회만 실패해도 참여 상태는 표시", async () => {
    vi.spyOn(api, "getNextRound").mockRejectedValue(new api.ApiError(500, "서버 오류"));
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_EMPTY);
    renderHome();
    expect(await screen.findByText("일정을 불러오지 못했어요")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /설문 하러가기/ })).toBeInTheDocument();
  });

  it("설문 조회만 실패하면 설문 경고를 띄우지 않음", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockRejectedValue(new api.ApiError(500, "서버 오류"));
    renderHome();
    await waitFor(() =>
      expect(screen.getByText("아직 예정된 매칭이 없어요")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /설문 하러가기/ })).toBeNull();
    expect(screen.queryByText(/매칭 참여 중/)).toBeNull();
  });
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd frontend && npx vitest run src/pages/Home/Home.test.tsx`
Expected: FAIL — 현재 `Home`은 `<h1>홈 (준비 중)</h1>`뿐이라 모든 단언이 "Unable to find element"로 실패

- [ ] **Step 4: 화면 구현**

`frontend/src/pages/Home/Home.tsx` 전체를 아래로 교체:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { getNextRound, getSurvey } from "../../lib/api";
import { formatKST, daysUntilKST } from "../../lib/datetime";
import type { MatchRoundOut } from "../../lib/types";
import styles from "./Home.module.css";

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [round, setRound] = useState<MatchRoundOut | null>(null);
  const [roundFailed, setRoundFailed] = useState(false);
  // null = 조회 실패. 실패했으면 설문 관련 안내를 아예 띄우지 않는다.
  const [surveyDone, setSurveyDone] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 두 정보는 독립이다. 하나가 실패해도 나머지는 표시돼야 해서 allSettled를 쓴다.
    Promise.allSettled([getNextRound(), getSurvey()]).then(([r, s]) => {
      if (r.status === "fulfilled") setRound(r.value);
      else setRoundFailed(true);
      if (s.status === "fulfilled") setSurveyDone(s.value.updated_at !== null);
      setLoading(false);
    });
  }, []);

  const days = round ? daysUntilKST(round.scheduled_at) : null;

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>다음 매칭</h1>

      <section className={styles.card}>
        {loading && <p className={styles.muted}>불러오는 중…</p>}
        {!loading && roundFailed && (
          <p className={styles.error}>일정을 불러오지 못했어요</p>
        )}
        {!loading && !roundFailed && !round && (
          <>
            <p className={styles.empty}>아직 예정된 매칭이 없어요</p>
            <p className={styles.muted}>일정이 정해지면 여기에 표시돼요</p>
          </>
        )}
        {!loading && round && (
          <>
            {days !== null && days >= 0 && (
              <p className={styles.dday}>{days === 0 ? "D-DAY" : `D-${days}`}</p>
            )}
            <p className={styles.when}>{formatKST(round.scheduled_at)}</p>
          </>
        )}
      </section>

      {!loading && (
        <section className={styles.status}>
          {surveyDone === false && (
            <div className={styles.notice}>
              <p className={styles.noticeText}>⚠ 설문을 아직 안 했어요</p>
              <button
                type="button"
                className={styles.cta}
                onClick={() => navigate("/survey")}
              >
                설문 하러가기
              </button>
            </div>
          )}
          {user?.matching_paused && (
            <div className={styles.notice}>
              <p className={styles.noticeText}>⏸ 매칭 일시정지 중</p>
              <button
                type="button"
                className={styles.cta}
                onClick={() => navigate("/mypage")}
              >
                마이페이지에서 해제
              </button>
            </div>
          )}
          {surveyDone === true && !user?.matching_paused && (
            <p className={styles.ok}>✓ 매칭 참여 중</p>
          )}
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 스타일 작성**

`frontend/src/pages/Home/Home.module.css` 생성:

```css
.wrap { padding-top: 24px; }

.title {
  font-size: 16px;
  color: #666;
  margin-bottom: 12px;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 28px 20px;
  text-align: center;
  margin-bottom: 20px;
}

.dday {
  font-size: 40px;
  font-weight: bold;
  color: var(--color-primary);
  line-height: 1.2;
}

.when {
  font-size: 14px;
  color: var(--color-text);
  margin-top: 8px;
}

.empty { font-size: 16px; font-weight: bold; }
.muted { font-size: 13px; color: #666; margin-top: 6px; }
.error { font-size: 14px; color: var(--color-error); }

.status { display: flex; flex-direction: column; gap: 12px; }

.notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
}

.noticeText { font-size: 14px; }

.cta {
  flex-shrink: 0;
  font-size: 13px;
  padding: 8px 12px;
  border: none;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
}

.ok {
  font-size: 14px;
  color: #666;
  text-align: center;
  padding: 8px 0;
}
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd frontend && npx vitest run src/pages/Home/Home.test.tsx`
Expected: PASS 7건

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Home/
git commit -m "feat(frontend): /home 화면 — D-day와 매칭 참여 상태

다음 라운드 D-day + 예정 일시, 설문 미완/일시정지 안내와 이동 버튼.
라운드 조회와 설문 조회는 서로 독립이라 allSettled로 부분 실패를 허용한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: 통합 검증

**Files:** (레포 코드 변경 없음. 실패가 나오면 해당 태스크로 돌아간다)
- Create → Delete: `backend/seed_round.py` — 육안 확인용 임시 스크립트. Step 5에서 지운다. **커밋하지 않는다**

**Interfaces:**
- Consumes: Task 1~3의 결과 전부

- [ ] **Step 1: 프론트 전체 게이트**

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm test
```
Expected: lint 경고 0건, 타입 에러 0건, 기존 114건 + 신규 12건 = 126건 PASS

- [ ] **Step 2: 백엔드 전체 게이트**

Run: `cd backend && uv run pytest`
Expected: 전부 PASS

- [ ] **Step 3: 시드 스크립트로 라운드 하나 넣기**

라운드를 만드는 코드가 아직 없으므로(범위 밖) 육안 확인용으로 직접 넣는다. `backend/seed_round.py`를 만든다 — **커밋하지 않는다. Step 5에서 지운다**:

```python
import sqlite3
from datetime import datetime, timedelta

DB = r"C:\workSpace\datingWeb\backend\dev.db"
scheduled = (datetime.utcnow() + timedelta(days=3)).isoformat(sep=" ")

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute(
    "insert into match_rounds (scheduled_at, status) values (?, 'pending')",
    (scheduled,),
)
conn.commit()
print("round id:", cur.lastrowid, "scheduled_at(UTC):", scheduled)
```

Run: `cd backend && uv run python seed_round.py`

- [ ] **Step 4: 개발 서버 띄우고 육안 확인**

```bash
cd backend && uv run uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

확인 항목:
1. `/home`에 `D-3`과 KST 예정 일시가 뜬다
2. 마이페이지에서 매칭 일시정지를 켜고 `/home`으로 돌아오면 ⏸ 안내와 버튼이 뜬다. 버튼이 `/mypage`로 간다
3. 설문을 한 번도 저장 안 한 계정으로는 ⚠ 안내가 뜨고 버튼이 `/survey`로 간다
4. **덤:** `/admin` 하단에 빈 스크롤이 없는지 확인한다 (이전 작업에서 육안 확인을 못 한 채 머지된 CSS 1줄 변경)

- [ ] **Step 5: 시드 라운드 정리**

Run: `cd backend && uv run python -c "import sqlite3; c=sqlite3.connect(r'C:\workSpace\datingWeb\backend\dev.db'); c.execute('delete from match_rounds'); c.commit(); print('cleared')"`

개발 DB를 원래 상태(라운드 없음)로 되돌린다. 빈 상태 화면도 이 김에 한 번 확인한다. 그 다음 시드 스크립트를 지운다:

Run: `rm backend/seed_round.py`

- [ ] **Step 6: 워킹트리 확인**

Run: `git status --short`
Expected: `?? .mcp.json`만 남아 있어야 한다. `seed_round.py`가 보이면 Step 5의 삭제가 안 된 것이다.

---

## 완료 후

브랜치 `feat/home-screen`에 커밋 4개(스펙 1 + 구현 3)가 쌓인다. push와 PR 생성은 **사용자 허락 후**에만 한다.

## 이번 범위 밖으로 남기는 것

- **라운드 관리 기능** (생성·수정·삭제·실행 + 관리자 UI). 이게 없으면 홈은 실서비스에서 계속 빈 상태다. 다음 우선순위 후보
- `MyPage.module.css`가 `var(--color-accent)`를 쓰는데 `tokens.css`에 그 토큰이 없다. 기존 코드의 문제라 이번에 안 건드린다 — 언급만
- `npm install` 취약점 경고 9건 (5 moderate / 3 high / 1 critical) 미확인
