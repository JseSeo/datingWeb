# `/home` 화면 설계

작성: 2026-08-11

## 목적

로그인 후 착지 화면인 `/home`이 현재 `<h1>홈 (준비 중)</h1>` 한 줄이다. 나머지 화면(설문·게임·마이페이지·관리자)은 모두 구현돼 있고 시작점만 비어 있다.

이 화면은 두 가지에 답한다.

1. **다음 매칭이 언제 도는가** — `MatchRound.scheduled_at` 기반 D-day
2. **내가 참여 가능한 상태인가** — 일시정지 / 설문 미완료 여부

## 범위

### 포함

- 다음 매칭 라운드 조회 엔드포인트 (읽기 전용)
- D-day 카운트다운 + 예정 일시(KST) 표시
- 참여 상태 라벨 + 행동 유도 링크
- 예정 라운드 없을 때의 빈 상태

### 제외

| 항목 | 이유 |
|---|---|
| 매칭 결과 표시 (상대가 누구인지) | 매칭 알고리즘 영역. CLAUDE.md 금지 항목 |
| 라운드 생성·수정·삭제, 관리자 UI | 그 자체로 독립된 관리자 기능. 별도 스펙 |
| 알림(푸시·알림톡) | 카카오 알림톡은 사업자등록 전 금지 |
| 매칭 요일/시간 하드코딩 | 팀 미결. `scheduled_at`을 DB에서 읽기만 함 |

### 알려진 결과

MatchRound를 만드는 코드가 현재 코드베이스에 없다. `app/api/`에 `admin.py`가 없고 `router.py`에는 `reports.admin_router`만 등록돼 있다. 따라서 이 화면은 시드 스크립트나 수동 SQL로 라운드를 넣기 전까지 **항상 빈 상태로 뜬다.** 이는 의도된 상태다 — 라운드 관리 기능은 별도 작업으로 분리했다.

이 때문에 참여 상태 라벨은 라운드 유무와 **무관하게** 표시한다. 라운드가 없어도 유저는 설문을 하거나 일시정지를 풀 수 있고, 그것이 빈 화면에서 유일하게 의미 있는 행동이다.

## 백엔드

### 신규 스키마 — `app/schemas/round.py`

```python
class MatchRoundOut(BaseModel):
    id: int
    scheduled_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

`status`는 내리지 않는다. 쿼리가 `pending`만 뽑으므로 항상 같은 값이라 정보가 없다. `executed_at`도 결과 영역이라 제외한다.

### 신규 라우터 — `app/api/rounds.py`

```python
router = APIRouter(prefix="/match-rounds", tags=["rounds"])

@router.get("/next", response_model=MatchRoundOut | None)
def get_next_round(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

`app/api/router.py`에 `include_router(rounds.router)` 한 줄을 추가한다.

### 설계 판단

| 항목 | 결정 | 근거 |
|---|---|---|
| 경로 | `/match-rounds/next` (`/me` 아래 아님) | 라운드는 유저와 무관한 전역 자원이다. `me.py`는 이미 196줄이고 리소스 단위로 구성돼 있다 |
| 과거 `pending` 라운드 | `scheduled_at >= utcnow()`로 **제외** | 관리자가 실행하지 않고 지나간 라운드가 "다음 매칭"으로 뜨면 D-day가 음수가 된다. 대신 예정 시각이 지나는 순간 홈은 빈 상태로 돌아간다 — 결과를 표시하지 않는 이 범위에서는 이게 옳다 |
| 응답 없음 표현 | `null` (200) | `GET /me/verification`이 `VerificationOut \| None`을 반환하는 기존 전례를 따른다. 404는 "리소스 없음"이 정상 상태인 경우에 부적절 |
| 인증 | `get_current_user` | 라운드 일정은 민감정보가 아니다. `me.py` 전체가 쓰는 의존성과 동일 |

## 프론트엔드

### 데이터 흐름

```
Home
 ├ useAuth().user                      → matching_paused (추가 호출 없음)
 └ useEffect → allSettled([getNextRound(), getSurvey()])
```

`Promise.all`이 아니라 **`Promise.allSettled`** 를 쓴다. 라운드 조회가 실패해도 참여 상태 경고는 떠야 하고, 그 반대도 마찬가지다. 두 정보는 서로 독립이다.

`getSurvey()`는 `lib/api.ts:180`에 이미 있다. 신규 API 함수는 `getNextRound()` 하나다.

### 상태 판정 규칙

| 항목 | 규칙 |
|---|---|
| 설문 완료 | `SurveyOut.updated_at !== null` (= 저장 이력 있음) |
| 일시정지 | `user.matching_paused === true` |
| 동시 해당 | 둘 다 표시한다. 각각 다른 행동(`/survey`, `/mypage`)이 필요해 하나로 합칠 수 없다 |
| 라운드 조회 실패 | 카드 자리에 "일정을 불러오지 못했어요". 참여 상태는 정상 표시 |
| 설문 조회 실패 | 설문 경고를 **숨긴다**. 실제로는 완료한 유저에게 "설문 안 했어요"를 띄우는 오탐이 더 나쁘다 |

**설문 완료 판정에 대해:** `Survey.tsx`의 `handleSave`는 부분 저장을 허용한다 — 전 문항 응답을 강제하지 않는다. 따라서 "완료"의 엄밀한 정의가 코드에 존재하지 않는다. 홈은 저장 이력만 본다. 문항 전수 검증을 하려면 홈이 설문 문항 정의를 import해야 해서 결합이 늘어나고, 설문 화면 자체가 부분 저장을 허용하는 이상 일관되지도 않다.

### D-day 계산 — `lib/datetime.ts` 확장

```ts
export function daysUntilKST(iso: string, now?: Date): number | null
```

**KST 달력 날짜 차이**를 반환한다. 시각 차이가 아니다 — "D-1"은 24시간 후가 아니라 *내일*을 뜻해야 한다. 기존 `formatKST`의 `Intl` 포맷터를 재사용해 양쪽의 KST 날짜를 뽑아 뺀다.

- `0` → `D-DAY`, `3` → `D-3`
- 파싱 실패 → `null` → 카운트다운을 숨기고 예정 일시만 표시. `formatKST`가 실패 시 원문을 반환하는 기존 방어 스타일과 같은 태도
- **음수**: 함수는 차이를 그대로 반환한다(음수 가능). 서버 쿼리가 과거 라운드를 걸러내지만, 유저가 화면을 열어둔 채 예정 시각이 지나면 클라이언트에서 음수가 나올 수 있다. 이때 화면은 카운트다운을 숨기고 예정 일시만 표시한다 — 판정은 함수가 아니라 `Home`이 한다
- `now` 인자는 생략 시 `new Date()`. 주입 가능하게 해 테스트가 시스템 시계에 묶이지 않게 한다

### 화면

```
다음 매칭
  D-3
  2026-08-14 21:00          ← formatKST 재사용
────────────────────────
⚠ 설문을 아직 안 했어요
   [설문 하러가기]           → /survey
⏸ 매칭 일시정지 중
   [마이페이지에서 해제]     → /mypage
```

- 둘 다 해당 없으면 `✓ 매칭 참여 중`
- 라운드가 없거나 조회에 실패해도 `다음 매칭` 헤더는 유지하고 그 아래 내용만 바뀐다. 라운드 없음 → "아직 예정된 매칭이 없어요 / 일정이 정해지면 여기에 표시돼요"
- `/home`은 `MainLayout` 안에 있으므로(`App.tsx`) 내비게이션은 이미 있다. 콘텐츠만 만든다

### 파일

`Home.tsx` + `Home.module.css`. 기존 페이지 폴더 패턴 그대로다. 컴포넌트를 더 쪼개지 않는다 — 120줄 내외로 예상되고 두 블록이 같이만 쓰인다. 색은 디자인 토큰(`#FFF5E6`, `#FF7F5C`)만 사용한다.

## 검증

TDD로 진행한다 (CLAUDE.md 스킬 경합 규칙: `test-driven-development` 우선). 테스트를 먼저 쓴다.

### 백엔드 — `tests/test_rounds.py` (신규)

- 미래 `pending` 라운드가 있으면 그것을 반환
- 라운드가 하나도 없으면 `null`
- 과거 `pending` 라운드는 무시
- `done` 라운드는 무시
- 여러 개면 `scheduled_at`이 가장 이른 것
- 토큰 없이 호출하면 401

### 프론트엔드 — `lib/datetime.test.ts` (기존 파일에 추가)

- 당일 → `0`
- 3일 후 → `3`
- **KST 자정 경계**: UTC로는 같은 날이지만 KST로는 날짜가 넘어가는 시각
- 과거 시각 → 음수
- 깨진 문자열 → `null`

### 프론트엔드 — `pages/Home/Home.test.tsx` (신규)

- 라운드 있음 → D-day와 일시 표시
- 라운드 없음 → 빈 상태 문구
- 설문 미완 → 경고 + `/survey` 링크
- 일시정지 → 경고 + `/mypage` 링크
- 둘 다 해당 없음 → "매칭 참여 중"
- 라운드 조회만 실패 → 에러 문구 + 참여 상태는 정상

### 완료 게이트

```
npm run lint
npx tsc --noEmit
npm test
uv run pytest
```

`npm run lint`는 build/test와 분리돼 있어 자동으로 돌지 않는다. 프론트를 건드렸으면 직접 실행한다.

## 후속 (이번 범위 밖)

- **라운드 관리 기능** — 생성·수정·삭제·실행. 이게 없으면 홈은 실서비스에서 계속 빈 상태다. 다음 우선순위 후보
- `/admin` 하단 빈 스크롤 제거(`Admin.module.css`의 `min-height: 100vh` 삭제)가 브라우저 육안 확인이 안 된 채 main에 있다. 이번에 `npm run dev`를 띄울 때 함께 확인한다
- 라운드 관리 기능을 만들 때 `match_rounds.scheduled_at`은 반드시 UTC-naive로 저장해야 한다. 프론트는 타임존 접미사 없는 `scheduled_at`을 UTC로 간주하고(`frontend/src/lib/datetime.ts:44`, `formatKST`와 동일 규칙), 백엔드 조회 쿼리도 naive `datetime.utcnow()`와 비교한다. KST로 저장하면 필터링과 D-day가 조용히 9시간씩 밀린다
