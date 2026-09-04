# 매칭 예약 실행 — 설계 스펙

작성: 2026-09-05

## 문제

라운드는 `scheduled_at`(매칭 예정 일시)을 갖고 있지만, 그 시각이 돼도 아무 일도 일어나지 않는다.
매칭을 돌리는 유일한 방법은 관리자가 `/admin` 라운드 탭에서 `[매칭 실행]`을 누르는 것이다
(`POST /admin/match-rounds/{id}/run`).

즉 `scheduled_at`은 지금 **관리자용 메모**에 가깝다. 유저의 `/home` D-day는 그 시각을 가리키는데
실제 실행은 관리자가 그 시간에 깨어 있어야 일어난다.

이 스펙은 **예정 시각이 되면 서버가 알아서 매칭을 실행하는 기능**을 정의한다.

## 결정 요약

| 항목 | 결정 |
|------|------|
| 실행 주체 | 서버 자동 (앱 내부 백그라운드 루프) |
| 트리거 방식 | 60초마다 폴링 |
| 놓친 예약 | 유예 1시간 안에서만 만회. 넘기면 실행하지 않고 관리자에게 표시 |
| 실패 | 재시도 없음. 사유를 DB에 기록하고 관리자 화면에 노출 |
| 수동 실행 버튼 | 존치 — 유예를 넘긴 라운드의 폴백 |
| 인프라 추가 | 없음 (별도 cron 서비스·외부 호출 엔드포인트 모두 안 씀) |

### 상위 스펙 변경

`2026-08-21-matching-algorithm-design.md` §1 결정 요약표의

> 실행 방식 | 관리자 버튼 수동

를 다음으로 대체한다.

> 실행 방식 | 예약 자동 실행 (`2026-09-05-matching-schedule-design.md`) + 관리자 수동 폴백

§2.1의 *"나중에 실행 트리거를 스케줄러로 바꿔도 이 두 파일은 손대지 않는다"* 와
*"추후 스케줄러 전환 시 `run_matching()`을 그대로 호출하면 된다"* 는 이 스펙이 그대로 이행한다.

## 왜 앱 내부 루프인가

세 안을 놓고 비교했다.

| 안 | 장 | 단 | 판정 |
|----|----|----|------|
| **앱 내부 루프** | 인프라 추가 0. 배포 그대로. 의존성 추가 0 | 앱 프로세스가 죽으면 스케줄러도 죽는다 | **채택** |
| Railway Cron 서비스 | 웹과 완전 분리 | Railway 서비스 +1(비용·설정), CLI 진입점 + 부팅 코드 신규 | 주 1회·수백 명 규모에 과함 |
| 외부 cron → 보호 엔드포인트 | 어디서든 동작 | `require_admin` 밖의 **새 인증 경로**를 뚫는다. 시크릿 유출 = 임의 매칭 실행 | 보안 표면만 늘어남 |

앱이 죽으면 스케줄러도 죽는 단점은 **유예 1시간 만회**가 덮는다. 배포 재시작은 보통 수십 초다.

APScheduler 같은 라이브러리는 쓰지 않는다. 필요한 것이 "N초마다 깨서 쿼리 한 번"이라
`asyncio.sleep` 루프로 충분하고, 라이브러리를 넣으면 잡 저장소·미스파이어 정책 같은
쓰지 않을 개념이 따라온다.

## 아키텍처

```
main.py (lifespan)
   └─ scheduler_loop()              # 무한 루프: 깨서 부르고 잔다
        └─ run_due_once(db, now)    # 한 번의 점검. 판정 로직 전부 여기
             └─ run_matching(db, round_id)   # 기존 함수 — 손대지 않는다
                  └─ _execute(...)           # 기존 8단계
```

`app/services/scheduler.py` 신규 파일 하나. `matching.py`·`pairing.py`·`scoring.py`는
**한 줄도 바뀌지 않는다** (`run_matching`의 성공 시 `last_error` 초기화 한 줄 제외 — 아래 참조).

### 왜 `run_due_once`를 따로 두나

루프와 판정을 한 함수에 두면 테스트가 `asyncio.sleep`을 기다려야 한다. 판정을
`run_due_once(db, now)`로 떼면 `now`를 인자로 주입해 초 단위 경계를 전부 즉시 검증할 수 있고,
루프에는 테스트할 것이 남지 않는다.

## 데이터 모델

`match_rounds`에 컬럼 하나를 추가한다.

```python
# 마지막 자동 실행이 실패했거나 유예를 넘겨 건너뛴 사유. 성공하면 지워진다
last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

`String(500)`인 이유: 예외 문자열은 길이 상한이 없다. 스택트레이스 전체가 아니라
`type(exc).__name__: str(exc)` 앞부분만 저장하고, 넘치면 잘라 넣는다.

alembic 마이그레이션 1개. 현재 head는 `663fa9cf7ce5`.

**새 상태값(enum)을 만들지 않는다.** `RoundStatus`에 `failed`/`missed`를 더하면 기존
`pending` 기준 쿼리 — `get_next_round`, `_get_editable_round`, `run_matching`의 선점 UPDATE —
가 전부 새 상태를 어떻게 볼지 다시 정해야 한다. 실패한 라운드는 여전히 "아직 안 돌아간 라운드",
즉 `pending`이 맞다. `last_error`는 그 위에 얹는 부가 정보다.

## 스케줄러 동작

### 상수

| 이름 | 값 | 역할 |
|------|-----|------|
| `POLL_INTERVAL` | 60초 | 루프가 깨는 간격. 최대 60초 지연이 생긴다 |
| `CATCHUP_GRACE` | 1시간 | 예정 시각 + 이 시간까지는 늦어도 실행한다 |

`RUNNING_GRACE`(`api/rounds.py:18`, 5분)와 혼동하지 말 것 — 그쪽은 `running`에 멈춘 라운드를
관리자가 되돌릴 수 있게 되기까지의 대기시간이다.

### 판정 규칙

`now` 기준으로 `status == pending`인 라운드만 본다. `running`·`done`은 건드리지 않는다.

| 조건 | 동작 |
|------|------|
| `now < scheduled_at` | 아무것도 안 함 |
| `scheduled_at <= now < scheduled_at + CATCHUP_GRACE` 이고 `last_error is None` | `run_matching` 호출 |
| `scheduled_at <= now < scheduled_at + CATCHUP_GRACE` 이고 `last_error`가 있음 | 아무것도 안 함 (재시도 금지) |
| `scheduled_at + CATCHUP_GRACE <= now` 이고 `last_error is None` | 놓침 문구 기록 |
| `scheduled_at + CATCHUP_GRACE <= now` 이고 `last_error`가 있음 | 아무것도 안 함 (중복 마킹 금지) |

`last_error`가 실행 조건에 들어가는 것이 **재시도 금지의 구현**이다. 이 조건이 없으면
한 번 실패한 라운드가 유예 1시간 동안 60초마다 재시도되어 로그 60줄과 무의미한 부하를 만든다.

놓침 문구:

```
예정 시각을 놓쳐 자동 실행되지 않았습니다. 수동으로 실행해주세요
```

### 실패 처리

`run_matching`은 내부에서 이미 전체 롤백 후 라운드를 `pending`으로 되돌린다
(`services/matching.py`의 `except` 블록). 스케줄러는 그 위에 사유만 적는다.

```python
try:
    run_matching(db, round_.id)
except RoundNotPending:
    pass          # 다른 워커가 먼저 선점했다. 정상 경로 — 기록하지 않는다
except Exception as exc:
    _record_error(db, round_.id, f"{type(exc).__name__}: {exc}")
```

`RoundNotPending`을 조용히 넘기는 것이 중요하다. Railway 워커가 2개면 루프도 2개이고,
둘이 같은 라운드를 동시에 집으면 진 쪽이 이 예외를 받는다. 이긴 쪽은 정상 실행 중이므로
`last_error`를 쓰면 성공한 라운드에 거짓 에러가 붙는다.

`_record_error`는 **별도 트랜잭션**이다. `run_matching`이 실패하며 세션을 rollback 했으므로
그 세션 상태에 얹지 않고 새로 조회해 쓰고 커밋한다.

### 동시 실행 방어

새로 만들지 않는다. `run_matching`의 조건부 UPDATE(`status == pending`일 때만 `running`으로)가
이미 경쟁 구간 없는 선점이다. 워커가 몇 개든 라운드 하나는 한 번만 실행된다.

### `last_error` 지우기 — 비대칭

| 방향 | 주체 |
|------|------|
| 쓰기 (실패·놓침) | 스케줄러만 |
| 지우기 (성공) | `run_matching` — 자동·수동 공통 |

수동 실행이 실패해도 DB에 남기지 않는다. 관리자가 버튼을 누른 그 화면에서 에러를 즉시 보기 때문이다.
반대로 지우기는 `run_matching` 성공 경로에 두어야 한다 — 관리자가 수동으로 되살린 라운드의
`done` 카드에 옛 실패 문구가 남으면 안 된다.

이것이 `matching.py`에 들어가는 유일한 변경이다 (`_execute` 성공 후, 같은 커밋에 포함).

### 이벤트 루프 블로킹

`run_matching`은 동기 함수이고 최장 실행이 131초다(4,000명 실측, `api/rounds.py:16` 주석).
`await`으로 직접 부르면 그동안 FastAPI 전체가 응답하지 못한다.

```python
await asyncio.to_thread(_tick)     # _tick이 세션을 열고 run_due_once를 부른다
```

### DB 세션

루프는 HTTP 요청이 아니라 `get_db` 의존성을 쓸 수 없다. 매 폴링마다 `SessionLocal()`을
새로 열고 `finally`에서 닫는다. 세션 하나를 몇 주씩 붙들면 커넥션이 끊긴 채로 남는다.

`run_due_once` 전체를 `try/except`로 감싼다 — 폴링 한 번의 실패(DB 일시 단절 등)로
루프 자체가 죽으면 그 뒤 모든 예약이 조용히 사라진다.

## 앱 수명주기

`main.py`를 `lifespan`으로 바꾼다 (현재는 startup 훅이 하나도 없다).

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler_loop()) if settings.scheduler_enabled else None
    yield
    if task is not None:
        task.cancel()
```

`settings.scheduler_enabled: bool = True` — 기본값이 `True`인 이유는 Railway에서 환경변수를
빠뜨렸을 때 기능이 조용히 죽는 쪽보다 켜져 있는 쪽이 안전하기 때문이다. 테스트는
`conftest.py`에서 `False`로 내린다.

## API

`AdminMatchRoundOut`에 `last_error: str | None`을 추가한다.

유저용 `MatchRoundOut`(`id`, `scheduled_at`)은 **손대지 않는다.** 실패 사유는 관리자 정보다.

새 엔드포인트는 없다. 예약은 기존 라운드 생성(`POST /admin/match-rounds`)이 곧 예약이다.

## 프론트엔드

| 파일 | 변경 |
|------|------|
| `lib/types.ts` | `AdminMatchRoundOut`에 `last_error: string \| null` |
| `pages/Admin/RoundTab.tsx` | 카드에 `last_error`가 있으면 빨간 한 줄 표시 (`styles.error` 재사용) |

- **상태 배지는 안 건드린다.** `STATUS_LABEL`은 서버 `RoundStatus`와 1:1이다. 여기에
  "실패"·"놓침"을 섞으면 배지가 enum이 아닌 파생 상태를 표현하게 되고 그 순간 드리프트가 시작된다
- 수동 폴백은 이미 있다. `pending` 카드의 `[매칭 실행]`이 유예를 넘긴 라운드를 돌리는 수단이다
- **자동 갱신 없음.** 관리자 화면은 새로고침해야 최신 상태를 본다. 폴링 UI를 붙이면
  프론트에도 타이머가 하나 더 생긴다

## 테스트

`backend/tests/test_scheduler.py` (신규) — 전부 `run_due_once(db, now)`에 `now`를 주입한다.
실제 시간을 기다리는 테스트는 없다.

| 케이스 | 기대 |
|--------|------|
| `now == scheduled_at` | 실행 → `done` |
| `now = scheduled_at + 59분` | 실행 (유예 내) |
| `now = scheduled_at + 61분` | 실행 안 함 + `last_error`에 놓침 문구 |
| 놓침 마킹된 라운드 재점검 | 문구 그대로, 실행도 안 함 |
| `now < scheduled_at` | 변화 없음 |
| `running` / `done` 라운드 | 무시 |
| `run_matching`이 예외 (monkeypatch) | `last_error` 기록 + `status`는 `pending` |
| `RoundNotPending` (monkeypatch) | `last_error` 안 씀 |
| `last_error`가 있고 유예 내인 라운드 | 실행 안 함 (재시도 금지) |
| 여러 라운드가 동시에 due | 전부 처리 |

| 파일 | 추가 |
|------|------|
| `backend/tests/test_admin_rounds.py` | 응답에 `last_error` 포함 1건 |
| `backend/tests/test_matching.py` | 실행 성공 시 `last_error` 초기화 1건 |
| `frontend/src/pages/Admin/RoundTab.test.tsx` | `last_error` 있는 카드에 문구 렌더 1건 |

**`scheduler_loop`은 테스트하지 않는다.** `asyncio.sleep` 타이밍 테스트는 반드시 flaky해진다.
판정은 전부 `run_due_once`에 있고 루프에 남는 것은 "깨서 부르고 잔다" 뿐이다.

## 검증 기준

```
cd backend  && uv run pytest        # 전부 통과
cd frontend && npm run lint         # 경고 0
cd frontend && npx tsc --noEmit     # 오류 0
cd frontend && npm test             # 전부 통과
```

육안: 로컬 서버를 띄우고 2분 뒤 시각으로 라운드를 만든 다음 **아무것도 누르지 않고** 기다린다.
카드가 `완료`로 바뀌고 `/me/match`에 결과가 뜬다.

## 범위 밖

| 항목 | 이유 |
|------|------|
| 실패 시 관리자 알림 (메일·알림톡) | 알림톡은 사업자등록 전 금지(CLAUDE.md). 메일은 인프라 신규 |
| 재시도 | 결정: 하지 않는다. 결정적 버그면 유예 내내 같은 실패를 반복한다 |
| `scheduled_at` 분할 (실행 시각 / 결과 공개 시각) | 라운드 관리 스펙이 예고한 재검토 항목이지만, 자동 실행이 붙어도 셋은 여전히 같은 시각이다. 나누려면 매칭 요일·시간(팀 미결)이 먼저 확정돼야 한다 |
| 관리자 화면 자동 갱신 | 프론트 타이머 추가. 새로고침으로 충분 |
| 반복 예약 (매주 자동 생성) | 라운드 생성은 여전히 관리자 수동. 이 스펙은 "만들어 둔 라운드가 제 시간에 도는가"만 다룬다 |

## 후속

- 반복 예약(주간 자동 라운드 생성)은 이 기능이 실서비스에서 몇 주 돈 뒤에 판단한다
- Railway 워커를 2개 이상으로 늘릴 일이 생기면, 선점 방어는 이미 있으므로 코드 변경은 없다
