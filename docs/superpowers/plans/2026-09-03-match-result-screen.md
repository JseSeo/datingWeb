# 인앱 매칭 결과 화면 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매칭된 유저가 홈 화면에서 상대 이름·학교·연락처를 볼 수 있게 한다 (설계 §10 3단계).

**Architecture:** 백엔드에 읽기 전용 엔드포인트 `GET /me/match` 하나를 추가한다 — 가장 최근 `done` 라운드에서 내가 낀 `Match` 행을 찾아 상대 정보를 반환하고, 없으면 `null`. 프론트는 홈에서 이 API를 기존 두 호출과 같은 `Promise.allSettled`에 얹고, 결과가 있으면 D-day 카드 자리에 결과 카드를 대신 그린다. 새 테이블·마이그레이션 없음.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (백엔드), React + Vite + Vitest + Testing Library (프론트)

**Spec:** `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§7.1 `GET /me/match` 정의, §8 화면, §10 3단계)

## Global Constraints

- 결과 화면에 **프로필 사진·자기소개를 표시하지 않는다** (설계 §8, 노출 최소화).
- `Match.score`는 내부 운영용 — 응답에 **절대 포함하지 않는다** (설계 §7.1).
- 지난 라운드 이력은 반환하지 않는다. "이번 주 결과"만 (설계 §7.1).
- 연락처는 `instagram` / `kakao_id` / `phone` 중 **값이 있는 것만** 표시한다.
- 커밋 형식: `<영어prefix>(<scope>): <한국어 제목>` + 본문 끝에 `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- 브랜치: `feat/match-result-screen` (새 기능 + 다중 커밋 → PR 필수)
- 백엔드 테스트: `cd backend && .venv/Scripts/python.exe -m pytest`
- 프론트 테스트: `cd frontend && npm test -- --run`

## 용어

| 이름 | 역할 |
|---|---|
| `MatchResultOut` | `/me/match` 응답 스키마. 상대 이름·학교·연락처 3종 + 라운드 실행시각 |
| `get_my_match` | `/me/match` 핸들러 함수 |
| `getMyMatch` | 프론트 API 래퍼. 매칭 결과 또는 null 반환 |
| `match` | Home 컴포넌트 state. 내 매칭 결과 또는 null |
| `RoundStatus.done` | 실행이 끝난 라운드 상태값 |

---

### Task 0: 브랜치 생성

- [ ] **Step 1: 브랜치를 판다**

```bash
git checkout main
git pull
git checkout -b feat/match-result-screen
```

---

### Task 1: 백엔드 `GET /me/match`

**Files:**
- Modify: `backend/app/schemas/matching.py` (파일 끝에 추가)
- Modify: `backend/app/api/me.py` (import 보강 + 파일 끝에 라우트 추가)
- Test: `backend/tests/test_me_match.py` (신규)

**Interfaces:**
- Consumes: `app.models.match.Match`, `app.models.match.MatchRound`, `app.models.match.RoundStatus`, `app.core.deps.get_current_user`, `app.database.get_db`
- Produces: `MatchResultOut` — 필드 `name: str`, `university: str`, `instagram: str | None`, `kakao_id: str | None`, `phone: str | None`, `executed_at: datetime`. Task 2의 프론트 타입이 이 필드명을 그대로 쓴다. 엔드포인트 경로는 `GET /me/match`, 응답은 `MatchResultOut` 또는 `null`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_me_match.py` 생성:

```python
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.models.match import Match, MatchRound, RoundStatus
from app.models.user import Gender, User, UserStatus
from tests.conftest import TestingSessionLocal


def _register_and_get_headers(client: TestClient, email: str = "me@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김미",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_partner(email: str = "partner@test.com") -> int:
    """상대 유저를 만들고 id를 준다. 연락처는 인스타·카톡만 채운다."""
    db = TestingSessionLocal()
    partner = User(
        email=email, password_hash="x", name="이상대", university="연세대학교",
        gender=Gender.female, status=UserStatus.active,
        instagram="partner_insta", kakao_id="partner_kakao",
    )
    db.add(partner)
    db.commit()
    partner_id = partner.id
    db.close()
    return partner_id


def _make_done_round(executed_at: datetime) -> int:
    db = TestingSessionLocal()
    round_ = MatchRound(
        scheduled_at=executed_at,
        executed_at=executed_at,
        status=RoundStatus.done,
    )
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    return round_id


def _make_match(round_id: int, a_id: int, b_id: int) -> None:
    db = TestingSessionLocal()
    db.add(Match(match_round_id=round_id, user_a_id=a_id, user_b_id=b_id, score=77))
    db.commit()
    db.close()


def _my_id(client: TestClient, headers: dict) -> int:
    return client.get("/me", headers=headers).json()["id"]


def test_no_executed_round_returns_null(client: TestClient):
    headers = _register_and_get_headers(client)
    res = client.get("/me/match", headers=headers)
    assert res.status_code == 200
    assert res.json() is None


def test_matched_returns_partner_and_contacts(client: TestClient):
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, me_id, partner_id)

    res = client.get("/me/match", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "이상대"
    assert data["university"] == "연세대학교"
    assert data["instagram"] == "partner_insta"
    assert data["kakao_id"] == "partner_kakao"
    assert data["phone"] is None
    assert data["executed_at"].startswith("2026-08-14T12:00:00")


def test_partner_found_when_i_am_user_b(client: TestClient):
    """user_a/user_b 어느 쪽에 있든 상대를 찾아야 한다."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, partner_id, me_id)

    res = client.get("/me/match", headers=headers)

    assert res.json()["name"] == "이상대"


def test_score_is_not_exposed(client: TestClient):
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    round_id = _make_done_round(datetime(2026, 8, 14, 12, 0))
    _make_match(round_id, me_id, partner_id)

    assert "score" not in client.get("/me/match", headers=headers).json()


def test_unmatched_in_latest_round_returns_null(client: TestClient):
    """실행된 라운드는 있는데 내 짝이 없으면 null."""
    headers = _register_and_get_headers(client)
    _make_done_round(datetime(2026, 8, 14, 12, 0))

    assert client.get("/me/match", headers=headers).json() is None


def test_previous_round_result_is_not_returned(client: TestClient):
    """지난 라운드에 매칭됐어도 최신 done 라운드에서 미매칭이면 null (설계 §7.1)."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    old_round = _make_done_round(datetime(2026, 8, 7, 12, 0))
    _make_match(old_round, me_id, partner_id)
    _make_done_round(datetime(2026, 8, 14, 12, 0))

    assert client.get("/me/match", headers=headers).json() is None


def test_pending_round_is_ignored(client: TestClient):
    """아직 안 돌린 라운드에 딸린 행은 결과가 아니다."""
    headers = _register_and_get_headers(client)
    me_id = _my_id(client, headers)
    partner_id = _make_partner()
    db = TestingSessionLocal()
    round_ = MatchRound(scheduled_at=datetime.utcnow() + timedelta(hours=1))
    db.add(round_)
    db.commit()
    round_id = round_.id
    db.close()
    _make_match(round_id, me_id, partner_id)

    assert client.get("/me/match", headers=headers).json() is None


def test_requires_auth(client: TestClient):
    assert client.get("/me/match").status_code == 401
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_me_match.py -v`
Expected: FAIL — `/me/match`가 없어서 404 (`test_requires_auth`만 우연히 통과할 수 있다)

- [ ] **Step 3: 응답 스키마를 추가한다**

`backend/app/schemas/matching.py` 최상단에 import를 추가한다:

```python
from datetime import datetime
```

파일 끝에 붙인다:

```python
class MatchResultOut(BaseModel):
    """내 매칭 결과 (설계 §7.1).

    프로필 사진·자기소개·score는 담지 않는다 — 노출 최소화(§8)와
    score 비공개(§7.1) 때문이다.
    """

    name: str
    university: str
    instagram: str | None
    kakao_id: str | None
    phone: str | None
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: 엔드포인트를 구현한다**

`backend/app/api/me.py` — import를 보강한다. `from sqlalchemy.orm import Session` 위에:

```python
from sqlalchemy import or_
```

모델·스키마 import 블록에:

```python
from app.models.match import Match, MatchRound, RoundStatus
from app.schemas.matching import MatchResultOut
```

파일 끝에 라우트를 붙인다:

```python
@router.get("/match", response_model=MatchResultOut | None)
def get_my_match(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """가장 최근에 실행된 라운드의 내 결과. 미매칭이거나 실행된 라운드가 없으면 null.

    이력은 주지 않는다 — 화면이 보여주는 건 "이번 주 결과"뿐이다 (설계 §7.1).
    executed_at이 빈 done 행은 정렬 기준이 없어 제외한다. 정상 실행에서는
    생기지 않지만, 섞이면 최신 라운드 판정이 DB의 NULL 정렬 규칙에 좌우된다.
    """
    latest = (
        db.query(MatchRound)
        .filter(
            MatchRound.status == RoundStatus.done,
            MatchRound.executed_at.isnot(None),
        )
        .order_by(MatchRound.executed_at.desc())
        .first()
    )
    if latest is None:
        return None

    match = (
        db.query(Match)
        .filter(
            Match.match_round_id == latest.id,
            or_(Match.user_a_id == current_user.id, Match.user_b_id == current_user.id),
        )
        .first()
    )
    if match is None:
        return None

    partner_id = (
        match.user_b_id if match.user_a_id == current_user.id else match.user_a_id
    )
    partner = db.get(User, partner_id)
    return MatchResultOut(
        name=partner.name,
        university=partner.university,
        instagram=partner.instagram,
        kakao_id=partner.kakao_id,
        phone=partner.phone,
        executed_at=latest.executed_at,
    )
```

- [ ] **Step 5: 테스트를 돌린다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_me_match.py -v`
Expected: PASS — 9 passed

- [ ] **Step 6: 전체 백엔드 테스트로 회귀를 확인한다**

Run: `cd backend && .venv/Scripts/python.exe -m pytest -q`
Expected: 기존 테스트 전부 PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/app/schemas/matching.py backend/app/api/me.py backend/tests/test_me_match.py
git commit -F- <<'MSG'
feat(backend): GET /me/match — 최근 실행 라운드의 내 매칭 결과

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 2: 프론트 홈 매칭 결과 카드

**Files:**
- Modify: `frontend/src/lib/types.ts` (`MatchingRunOut` 아래)
- Modify: `frontend/src/lib/api.ts` (import 목록 + `getNextRound` 아래)
- Modify: `frontend/src/pages/Home/Home.tsx`
- Modify: `frontend/src/pages/Home/Home.module.css`
- Test: `frontend/src/pages/Home/Home.test.tsx` (기존 파일에 추가)

**Interfaces:**
- Consumes: Task 1의 `GET /me/match` 응답 — 필드 `name`, `university`, `instagram`, `kakao_id`, `phone`, `executed_at`
- Produces: `MatchResultOut` 타입, `getMyMatch()` — 매칭 결과 또는 null을 담은 Promise

- [ ] **Step 1: 타입과 API 래퍼를 추가한다**

`frontend/src/lib/types.ts` — `MatchingRunOut` 아래에 붙인다:

```ts
export interface MatchResultOut {
  name: string;
  university: string;
  instagram: string | null;
  kakao_id: string | null;
  phone: string | null;
  executed_at: string;
}
```

`frontend/src/lib/api.ts` — 최상단 import 목록에 `MatchResultOut`을 넣고, `getNextRound` 바로 아래에 붙인다:

```ts
export function getMyMatch(): Promise<MatchResultOut | null> {
  return apiFetch<MatchResultOut | null>("/me/match", { method: "GET" });
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`frontend/src/pages/Home/Home.test.tsx` — `SURVEY_EMPTY` 아래에 상수를 추가한다:

```tsx
const MATCH = {
  name: "이상대",
  university: "연세대학교",
  instagram: "partner_insta",
  kakao_id: null,
  phone: null,
  executed_at: "2026-08-14T12:00:00",
};
```

기존 테스트들은 `getMyMatch`를 모킹하지 않으면 실제 fetch로 새서 깨진다. 기존 `beforeEach`
맨 끝(`vi.setSystemTime(...)` 다음 줄)에 기본 모킹을 넣어 전부 덮는다:

```tsx
  vi.spyOn(api, "getMyMatch").mockResolvedValue(null);
```

`describe("Home", ...)` 안에 새 테스트를 붙인다:

```tsx
  it("매칭 결과가 있으면 상대 이름·학교·연락처 표시", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({ id: 1, scheduled_at: "2026-08-14T12:00:00" });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    vi.spyOn(api, "getMyMatch").mockResolvedValue(MATCH);
    renderHome();
    expect(await screen.findByText("이상대")).toBeInTheDocument();
    expect(screen.getByText("연세대학교")).toBeInTheDocument();
    expect(screen.getByText("인스타그램 @partner_insta")).toBeInTheDocument();
  });

  it("매칭 결과가 있으면 D-day 카드 대신 결과를 보여준다", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({ id: 1, scheduled_at: "2026-08-14T12:00:00" });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    vi.spyOn(api, "getMyMatch").mockResolvedValue(MATCH);
    renderHome();
    await screen.findByText("이상대");
    expect(screen.queryByText("D-3")).not.toBeInTheDocument();
    expect(screen.getByText("이번 주 매칭 결과")).toBeInTheDocument();
  });

  it("빈 연락처는 줄을 만들지 않는다", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    vi.spyOn(api, "getMyMatch").mockResolvedValue(MATCH);
    renderHome();
    await screen.findByText("이상대");
    expect(screen.queryByText(/카카오톡/)).not.toBeInTheDocument();
    expect(screen.queryByText(/전화번호/)).not.toBeInTheDocument();
  });

  it("매칭 결과가 없으면 기존 D-day 화면 그대로", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({ id: 1, scheduled_at: "2026-08-14T12:00:00" });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    vi.spyOn(api, "getMyMatch").mockResolvedValue(null);
    renderHome();
    expect(await screen.findByText("D-3")).toBeInTheDocument();
    expect(screen.getByText("다음 매칭")).toBeInTheDocument();
  });

  it("매칭 조회가 실패해도 D-day는 뜬다", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({ id: 1, scheduled_at: "2026-08-14T12:00:00" });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    vi.spyOn(api, "getMyMatch").mockRejectedValue(new Error("boom"));
    renderHome();
    expect(await screen.findByText("D-3")).toBeInTheDocument();
  });
```

- [ ] **Step 3: 실패를 확인한다**

Run: `cd frontend && npm test -- --run src/pages/Home/Home.test.tsx`
Expected: FAIL — "이상대"를 못 찾는다 (Home이 아직 결과를 안 그린다)

- [ ] **Step 4: Home을 고친다**

`frontend/src/pages/Home/Home.tsx` — import 두 줄을 바꾼다:

```tsx
import { getNextRound, getSurvey, getMyMatch } from "../../lib/api";
import type { MatchRoundOut, MatchResultOut } from "../../lib/types";
```

state를 하나 추가한다 (`const [loading, setLoading] = useState(true);` 위):

```tsx
  const [match, setMatch] = useState<MatchResultOut | null>(null);
```

`useEffect`를 셋으로 늘린다:

```tsx
  useEffect(() => {
    // 셋은 서로 독립이다. 하나가 실패해도 나머지는 표시돼야 해서 allSettled를 쓴다.
    Promise.allSettled([getNextRound(), getSurvey(), getMyMatch()]).then(([r, s, m]) => {
      if (r.status === "fulfilled") setRound(r.value);
      else setRoundFailed(true);
      if (s.status === "fulfilled") setSurveyDone(s.value.updated_at !== null);
      if (m.status === "fulfilled") setMatch(m.value);
      setLoading(false);
    });
  }, []);
```

제목을 바꾼다:

```tsx
      <h1 className={styles.title}>{match ? "이번 주 매칭 결과" : "다음 매칭"}</h1>
```

카드를 갈래로 나눈다. 결과가 있으면 D-day 카드 **대신** 결과 카드를 그린다 (설계 §8).
기존 `<section className={styles.card}> … </section>` 블록 전체를 아래로 감싼다 — 안쪽
D-day 내용은 한 글자도 바꾸지 않고 `else` 가지에 그대로 둔다:

```tsx
      {!loading && match ? (
        <section className={styles.card}>
          <p className={styles.partner}>{match.name}</p>
          <p className={styles.when}>{match.university}</p>
          <ul className={styles.contacts}>
            {match.instagram && <li>인스타그램 @{match.instagram}</li>}
            {match.kakao_id && <li>카카오톡 {match.kakao_id}</li>}
            {match.phone && <li>전화번호 {match.phone}</li>}
          </ul>
          {!match.instagram && !match.kakao_id && !match.phone && (
            <p className={styles.muted}>상대가 등록한 연락처가 없어요</p>
          )}
        </section>
      ) : (
        <section className={styles.card}>
          {/* 기존 로딩·실패·빈 상태·D-day 내용을 그대로 옮긴다 */}
        </section>
      )}
```

- [ ] **Step 5: 스타일을 추가한다**

`frontend/src/pages/Home/Home.module.css` — `.when` 블록 아래에 붙인다:

```css
.partner {
  font-size: 28px;
  font-weight: bold;
  color: var(--color-primary);
  line-height: 1.2;
}

.contacts {
  list-style: none;
  margin-top: 14px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  color: var(--color-text);
}
```

- [ ] **Step 6: 테스트를 돌린다**

Run: `cd frontend && npm test -- --run src/pages/Home/Home.test.tsx`
Expected: PASS — 새 5건 + 기존 전부

- [ ] **Step 7: 프론트 전체 검증**

Run: `cd frontend && npm test -- --run` 그리고 `npm run build`
Expected: 전부 PASS, 타입 에러 없음

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/pages/Home
git commit -F- <<'MSG'
feat(frontend): 홈에 매칭 결과 카드 — 상대 이름·학교·연락처

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

---

### Task 3: 스펙 갱신 + PR

**Files:**
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§10 작업 분할 표)

- [ ] **Step 1: 3단계를 완료로 표시한다**

§10 표의 3단계 행을 이렇게 바꾼다:

```markdown
| **3. 인앱 결과 화면** | `GET /me/match` + 홈 카드 | 매칭 결과가 나와야 만들 수 있음. ✅ 완료 (2026-09-03) |
```

- [ ] **Step 2: 커밋한다**

```bash
git add docs/superpowers/specs/2026-08-21-matching-algorithm-design.md
git commit -F- <<'MSG'
docs(spec): §10 3단계 완료 표시

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
```

- [ ] **Step 3: 푸시·PR은 사용자 허락 후에만**

CLAUDE.md 규칙 — 허락 없이 push 금지. 허락받은 뒤:

```bash
git push -u origin feat/match-result-screen
gh pr create --title "feat: 인앱 매칭 결과 화면 (GET /me/match + 홈 카드)" --body "설계 §10 3단계. GET /me/match 추가 + 홈 결과 카드."
```

---

## Self-Review

**스펙 커버리지**

| 스펙 항목 | 담당 |
|---|---|
| §7.1 최신 done 라운드 기준 | Task 1 Step 4 정렬 + `test_previous_round_result_is_not_returned` |
| §7.1 미매칭 → null | `test_unmatched_in_latest_round_returns_null` |
| §7.1 실행 라운드 없음 → null | `test_no_executed_round_returns_null` |
| §7.1 이력 미반환 | `test_previous_round_result_is_not_returned` |
| §7.1 score 비노출 | `MatchResultOut`에 필드 없음 + `test_score_is_not_exposed` |
| §8 홈 카드 이름·학교·연락처 | Task 2 Step 4 + 테스트 3건 |
| §8 사진·자기소개 미표시 | `MatchResultOut`이 아예 안 내려줌 |
| §8 결과 없으면 D-day | `"매칭 결과가 없으면 기존 D-day 화면 그대로"` |

**범위 밖 (이 계획에서 안 한다)**

- 대학 가중치 (§10 4단계) — 다음 작업
- 카카오 알림톡 — 사업자등록 후
- 지난 라운드 이력 화면 — 스펙이 명시적으로 배제
