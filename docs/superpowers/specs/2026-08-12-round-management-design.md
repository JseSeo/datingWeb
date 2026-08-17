# 라운드 관리 — 설계 스펙

작성: 2026-08-12

## 문제

`MatchRound`를 만드는 코드가 코드베이스에 없다. `app/api/`에 관리자용 라운드 엔드포인트가 없고, `router.py`에 등록된 관리 라우터는 `reports.admin_router` 하나뿐이다. 그래서 `/home`의 D-day는 실서비스에서 항상 빈 상태이고, 지금은 수동 SQL로만 라운드를 넣을 수 있다.

이 스펙은 관리자가 라운드를 **생성·수정·삭제**하는 기능과 `/admin`의 라운드 탭을 정의한다.

## 범위

포함:

- 관리자 전용 라운드 CRUD API (`/admin/match-rounds`)
- `/admin`에 "라운드" 탭 추가 — 목록 · 생성 · 인라인 수정 · 삭제
- KST 입력을 UTC로 변환하는 프론트 유틸

제외:

| 항목 | 이유 |
|------|------|
| 라운드 **실행** (status → done, `Match` 생성) | 매칭 알고리즘 영역. `CLAUDE.md` 금지 항목 — "매칭 알고리즘 설계 시작해" 명령 전까지 착수 금지 |
| `status` / `executed_at` 쓰기 | 위와 같은 이유. 실행만이 이 두 필드를 바꾼다 |
| 라운드 이름 · 메모 필드 | 주 1회 서비스에서 날짜가 곧 식별자. 추가하면 모델 변경 + 마이그레이션 + `/home` 노출 여부 결정이 딸려온다. YAGNI |
| soft delete | `pending` 라운드에는 `Match`가 붙을 수 없어 hard delete가 FK상 안전하다. soft로 가면 `deleted_at` 컬럼과 **모든** 조회 필터(`/match-rounds/next` 포함)가 따라온다 |
| 페이지네이션 | 주 1회 = 연간 약 50행 |
| `/home` 변경 | 기존 화면은 그대로 동작한다 |
| ~~모델 변경 · alembic 마이그레이션~~ | ~~기존 `MatchRound` 컬럼으로 충분~~ → **2026-08-17 철회.** 중복 방지를 DB 보증으로 올리려 유니크 인덱스 1개를 추가했다. 컬럼은 그대로 (아래 "중복 방지의 두 층") |

## 절단선 — 실행과 CRUD의 경계

`status`와 `executed_at`은 **읽기 전용**이다.

- 생성 시 `status`는 항상 모델 default(`pending`). 클라이언트가 무엇을 보내든 버린다
- `executed_at`은 어느 경로에서도 읽지도 쓰지도 않는다. 관리자 응답 스키마에도 없다
- `done` 라운드는 수정·삭제가 잠긴다

이렇게 하면 실행 경로가 코드에 존재하지 않으므로 알고리즘 영역과 물리적으로 분리된다. 나중에 실행을 붙일 때 이 CRUD 스펙을 뒤집을 필요가 없다.

**실행을 붙일 때 같이 볼 것 — `Match` FK와 hard delete.** `Match.match_round_id`는 `nullable=False`에 `ondelete` 정책이 없고, `delete_round`는 hard delete다. 지금은 `done` 잠금이 둘 사이를 막지만, 실행이 `Match`를 만든 뒤 `status`를 늦게 커밋하면 그 창에서 삭제가 FK 위반 500이 된다. CASCADE냐 RESTRICT냐는 "라운드를 지우면 성사된 매칭도 사라지는가"라는 제품 결정이라 실행 설계와 함께 정한다.

### `scheduled_at`의 의미 — 알려진 모호성

현재 `scheduled_at` 한 필드가 서로 다른 세 시각을 겸하고 있다.

1. 매칭 알고리즘이 도는 시각
2. 유저에게 결과가 공개되는 시각
3. 신청 · 설문 마감 시각

유저는 `/home`의 D-day를 2번으로 읽고, 관리자는 1번으로 읽는다. 실행 기능이 없는 지금은 차이가 드러나지 않는다.

**이번 범위에서는 1필드를 유지하고 셋을 동일시한다.** 필드를 쪼개려면 매칭 요일/시간(팀 미결)이 확정돼야 하고, 그 전에 나누면 추측 설계가 된다. 매칭 알고리즘 설계 시점에 재검토한다.

관리 UI 라벨은 **"매칭 예정 일시"** 로 통일한다.

## 백엔드

### 파일 배치

`app/api/rounds.py`에 `admin_router`를 추가한다. `reports.py`(`router` + `admin_router`가 한 파일)와 같은 구성 — 한 리소스, 한 파일. 새 `admin.py`는 만들지 않는다. 현재 29줄 → 약 120줄로, `reports.py`(108줄)와 같은 규모다.

`router.py`에 `rounds.admin_router`를 등록한다.

### 스키마 (`app/schemas/round.py`)

```python
class MatchRoundIn(BaseModel):
    scheduled_at: datetime


class AdminMatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime
    status: RoundStatus

    model_config = ConfigDict(from_attributes=True)
```

생성과 수정은 필드가 같으므로 입력 스키마 하나를 공유한다.

기존 `MatchRoundOut`(`id`, `scheduled_at`)은 **손대지 않는다.** `backend/tests/test_rounds.py`의 `set(data.keys()) == {"id", "scheduled_at"}`가 유저 응답 경계를 고정하고 있고, `status`가 필요한 쪽은 관리자 응답뿐이다.

### 타임존 정규화

프론트가 `toISOString()`으로 보내면 값은 `2026-08-20T12:00:00.000Z` — **tz-aware**다. Pydantic은 이를 aware `datetime`으로 파싱하는데, naive `DateTime` 컬럼에 그대로 넣으면 백엔드에 따라 결과가 갈린다.

- PostgreSQL: 드라이버가 UTC로 변환해 저장
- SQLite(현재 `dev.db`): offset이 포함된 문자열이 그대로 저장 → 이후 `datetime.utcnow()` 비교가 조용히 깨진다

저장 직전 한 곳에서 강제 정규화한다.

```python
def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt  # 타임존 없으면 UTC로 간주 — 프론트 규칙과 동일
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
```

`match_rounds.scheduled_at`은 항상 **UTC-naive**다. 프론트는 타임존 접미사 없는 값을 UTC로 간주하고(`frontend/src/lib/datetime.ts`), 백엔드 조회는 naive `datetime.utcnow()`와 비교한다. KST로 저장하면 필터와 D-day가 9시간씩 밀린다.

### 검증

모두 정규화 **후** 판정한다. 경로마다 적용 규칙이 다르다.

- 생성: 과거 → 중복
- 수정: 404 → `done` 잠금 → 과거 → 중복(자기 자신 제외)
- 삭제: 404 → `done` 잠금 (시각 규칙은 적용하지 않는다 — 지나간 `pending` 라운드도 지울 수 있어야 한다)

| 규칙 | 코드 | 문구 |
|------|------|------|
| 저장하려는 값이 현재 이하 | 400 | `예정 시각은 현재보다 미래여야 합니다` |
| 같은 `scheduled_at`이 이미 존재 (수정 시 자기 자신 제외) | 409 | `같은 시각의 라운드가 이미 있습니다` |
| 대상 라운드 없음 | 404 | `존재하지 않는 라운드입니다` |
| 대상이 `done` — 수정 | 409 | `완료된 라운드는 수정할 수 없습니다` |
| 대상이 `done` — 삭제 | 409 | `완료된 라운드는 삭제할 수 없습니다` |

검증은 **백엔드에만** 둔다. 프론트는 `required`만 걸고 서버 `detail`을 그대로 표시한다. 규칙을 두 곳에 두면 드리프트가 확실히 온다 — 과거 판정만 해도 프론트는 브라우저 시계, 백엔드는 서버 시계라 경계에서 이미 어긋난다. `apiFetch`가 `ApiError`에 `detail`을 담아 던지므로(`frontend/src/lib/api.ts`) UX 손실도 없다.

**"과거 거부"는 기존 값이 아니라 저장하려는 새 값을 본다.** 그래서 생성과 수정이 같은 규칙 하나로 끝난다. 관리자가 실행하지 못하고 지나간 `pending` 라운드를 다음 주로 옮기는 것은 새 값이 미래이므로 통과한다.

### 중복 방지의 두 층 (2026-08-17 추가)

`_reject_duplicate`의 SELECT와 INSERT 사이에 다른 요청이 끼어들면 같은 `scheduled_at` 2건이 통과한다(TOCTOU). 그래서 두 층으로 막는다.

| 층 | 수단 | 역할 |
|----|------|------|
| 앱 | `_reject_duplicate` SELECT | 정상 경로. 쓰기 전에 409 + 문구 |
| DB | `uq_match_rounds_scheduled_at` 유니크 인덱스 (`9c9c633d854d`) | 경쟁 구간의 최후 방어선 |

DB가 막으면 `IntegrityError`가 나는데, `_commit_or_conflict`가 이를 rollback 후 **같은 409 + 같은 문구**로 바꾼다. 클라이언트 입장에서 두 층은 구분되지 않는다.

UNIQUE 제약이 아니라 **유니크 인덱스**를 쓴다 — SQLite에서 제약을 붙이려면 테이블 재생성(batch)이 필요하고, 그 과정이 `matches.match_round_id` FK 참조를 건드릴 수 있다. 인덱스는 재생성 없이 붙고 강제력은 같다. 모델도 `__table_args__`의 `Index(..., unique=True)`로 선언해 마이그레이션과 형태를 맞췄다.

**중복은 초 단위 정확 일치만 본다.** "KST 같은 날 두 개 금지"가 주 1회 도메인에는 더 맞지만, 그러려면 백엔드가 KST 오프셋을 알아야 한다(UTC `[전날 15:00, 당일 15:00)` 범위 쿼리). 타임존 지식은 프론트에만 두는 이 설계의 원칙이 깨지고, 그 상수가 이후 다른 곳으로 퍼질 위험이 있다. 같은 날 중복은 예정일 내림차순 목록에서 두 행이 붙어 보이므로 관리자 눈으로 잡힌다.

### 엔드포인트

전부 `require_admin` 의존성을 쓴다. 접두사는 `/admin/match-rounds`.

| 메서드 | 경로 | 응답 |
|--------|------|------|
| GET | `/admin/match-rounds` | 200 · `list[AdminMatchRoundOut]`, `scheduled_at` 내림차순 |
| POST | `/admin/match-rounds` | 201 · `AdminMatchRoundOut` |
| PUT | `/admin/match-rounds/{id}` | 200 · `AdminMatchRoundOut` |
| DELETE | `/admin/match-rounds/{id}` | 204 · 본문 없음 |

수정에 `PUT`을 쓰는 것은 코드베이스 관례를 따른 것이다(`me.py`의 `/profile`, `/matching-pause`, `/survey`가 모두 `PUT`이고 `PATCH`는 한 곳도 없다). 삭제 204도 `me.py`의 탈퇴와 같다.

목록은 필터 없이 전체를 준다 — 과거·미래·`done` 모두. 연간 50행 규모라 필터 UI가 이득보다 비싸다.

## 프론트엔드

### `lib/datetime.ts` — 변환 함수 2개 추가

```ts
/** datetime-local 값(KST)을 UTC ISO로. 잘못된 값이면 null. */
export function kstInputToUtcISO(local: string): string | null

/** UTC ISO를 datetime-local 초기값("YYYY-MM-DDTHH:mm")으로. */
export function utcISOToKstInput(iso: string): string
```

`kstInputToUtcISO`는 `datetime-local` 값에 `+09:00`을 붙여 파싱한 뒤 `toISOString()`을 반환한다. 초 유무가 브라우저마다 다르므로(`2026-08-20T21:00` / `2026-08-20T21:00:00`) 초가 없으면 붙인 뒤 오프셋을 잇는다.

접미사 없이 `new Date("2026-08-20T21:00")`으로 파싱하면 **브라우저 로컬 시각**이 되어 KST가 아닌 환경에서 조용히 틀린다. 오프셋을 명시하는 것이 이 함수의 핵심이다. KST는 서머타임이 없어 고정 `+09:00`으로 충분하다.

`utcISOToKstInput`은 기존 `formatKST`가 주는 `"YYYY-MM-DD HH:mm"`의 공백을 `T`로 바꾼다. 새 포맷터를 만들지 않는다.

왕복 불변식: `"YYYY-MM-DDTHH:mm"` 형태의 `x`에 대해 `utcISOToKstInput(kstInputToUtcISO(x)!) === x`. 초를 포함한 입력(`"...T21:00:00"`)은 왕복 결과에서 초가 떨어진다 — `datetime-local`이 다시 받을 수 있는 형태이므로 문제되지 않지만, 불변식은 분 단위 형태에만 성립한다.

### 타입 · API 클라이언트

```ts
export interface AdminMatchRoundOut {
  id: number;
  scheduled_at: string;
  status: "pending" | "done";
}
```

`api.ts`에 네 함수를 추가한다: `listMatchRounds()` · `createMatchRound(utcISO)` · `updateMatchRound(id, utcISO)` · `deleteMatchRound(id)`. 기존 `getNextRound`는 그대로 둔다.

### `pages/Admin/RoundTab.tsx`

상단에 생성 폼 한 줄(`datetime-local` + `[추가]`), 아래에 카드 목록. 각 카드에 `[수정]` `[삭제]`. `[수정]`을 누르면 그 카드가 입력칸으로 바뀌고 `[저장]` `[취소]`가 뜬다. 모달은 쓰지 않는다 — 재사용 가능한 모달 컴포넌트가 없어 포커스 트랩·Esc·백드롭·`aria-modal`을 전부 새로 만들어야 하고, 기존 두 탭도 카드 나열 방식이다.

상태는 넷: `items` · `form`(생성 폼 값) · `editingId` · `editValue`. 로딩·에러 처리는 `ReportTab`과 같은 형태를 따른다.

| 동작 | 흐름 |
|------|------|
| 생성 | 폼값 → `kstInputToUtcISO` → `null`이면 로컬 에러 문구, 아니면 POST → 목록에 삽입 후 `scheduled_at` 내림차순 재정렬 → 폼 비움 |
| 수정 시작 | `editingId` 세팅, `editValue = utcISOToKstInput(기존 값)` |
| 수정 저장 | PUT → 응답으로 해당 항목 교체 → 재정렬 → `editingId = null` |
| 수정 취소 | `editingId = null`, 목록 불변 |
| 삭제 | `window.confirm` 확인(취소하면 아무 일도 없음) → DELETE → 목록에서 제거 |
| 에러 | `ApiError`면 그 메시지를 그대로 표시, 아니면 기본 문구 |

**낙관적 갱신을 하지 않는다.** 서버 응답을 받은 뒤에만 목록 상태를 바꾼다. `/home` 작업에서 낙관적 갱신 후 롤백 경로가 버그를 만든 전례가 있다.

`window.confirm`은 `MyPage`의 탈퇴 확인과 같은 방식이다.

`done` 라운드는 `[수정]` `[삭제]` 버튼을 렌더하지 않는다. 백엔드도 409로 막지만, 누를 수 없는 버튼을 두지 않는다. 배지는 `pending` → "예정", `done` → "완료".

스타일은 `Admin.module.css`의 `card` · `actions` · `badge` · `when` · `error`를 재사용하고, 생성 폼 한 줄에 필요한 클래스만 추가한다.

### `pages/Admin/Admin.tsx` 변경

`Tab` 타입에 `"round"`를 더하고 탭 버튼을 하나 추가한다. 현재 패널 렌더는 삼항 하나인데 탭이 셋이 되면 중첩 삼항이 되므로, `{tab === "..." && <div role="tabpanel" …/>}` 세 개로 편다. 렌더 결과와 ARIA 속성은 그대로다.

## 에러 처리 요약

| 상황 | 화면 |
|------|------|
| 목록 조회 실패 | "목록을 불러오지 못했어요." — 폼은 그대로 사용 가능 |
| 생성·수정 400/409 | 서버 `detail` 문구를 그대로 표시. 입력값 유지 |
| 삭제 실패 | 에러 문구 표시, 목록 불변 |
| 입력값 파싱 실패 | "올바른 일시를 입력하세요." — 요청을 보내지 않음 |

## 테스트

| 파일 | 케이스 |
|------|--------|
| `backend/tests/test_admin_rounds.py` (신규) | 목록 내림차순 · 생성 201 · **aware ISO 입력이 UTC-naive로 저장되는지 DB 값으로 직접 확인** · 과거 400 · 중복 409 · 없는 id 404 · `done` 수정 409 · `done` 삭제 409 · 수정 200 · 삭제 204 후 조회에서 사라짐 · 비관리자 403 |
| `backend/tests/test_rounds.py` (기존) | 변경 없음. 유저 응답 경계 고정 테스트 유지 |
| `frontend/src/lib/datetime.test.ts` | 초 있는/없는 두 입력 형식 · 왕복 불변식 · 잘못된 입력 `null` · 다른 타임존 환경에서도 같은 결과 |
| `frontend/src/pages/Admin/RoundTab.test.tsx` (신규) | 목록 렌더 · 생성 후 목록 반영 · 인라인 수정 저장 · 수정 취소 시 원값 유지 · `confirm` 취소 시 삭제 안 됨 · 409 문구 표시 · `done` 행에 버튼 없음 |
| `frontend/src/pages/Admin/Admin.test.tsx` (기존) | 탭 3개 ARIA로 갱신 |

## 검증 기준

- `cd backend && uv run pytest` 전부 통과
- `cd frontend && npm run lint` 경고 0
- `cd frontend && npx tsc --noEmit` 오류 0
- `cd frontend && npm test` 전부 통과
- 육안: `/admin` 라운드 탭에서 생성 → `/home`에 D-day가 뜬다 → 수정하면 D-day가 따라 바뀐다 → 삭제하면 `/home`이 빈 상태로 돌아간다

## 후속

- **라운드 실행** — 팀 미결 3건(매칭 요일/시간, 16개 대학 목록, 알고리즘 상세)이 확정되고 "매칭 알고리즘 설계 시작해" 명령이 나온 뒤에만
- 실행을 설계할 때 `scheduled_at`을 실행 시각 / 공개 시각으로 쪼갤지 재검토
