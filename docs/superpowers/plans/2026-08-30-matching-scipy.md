# 매칭 엔진 scipy 교체 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `optimal_pairs`(점수표를 받아 총점 최대인 짝 목록을 내는 함수)의 엔진을 networkx에서 scipy로 바꿔 1,000명 매칭을 185초에서 1초 미만으로 줄인다.

**Architecture:** 목적함수는 그대로 두고 계산 엔진만 교체한다. 헝가리안은 작은 쪽 전원을 강제로 짝지우므로, 미매칭을 0점 선택지로 넣은 정사각 패딩 행렬을 써서 "총점이 더 크면 사람을 남긴다"는 현재 성질을 보존한다. tie-break 항은 raw user id 대신 등장 순번으로 계산한다 — raw id는 float64의 정확 정수 범위를 넘겨 tie가 반올림에 먹힌다.

**Tech Stack:** Python 3, scipy(`linear_sum_assignment`), numpy, SQLAlchemy, pytest, uv

**Spec:** `docs/superpowers/specs/2026-08-30-matching-performance-design.md`
(상위 스펙: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` §5.1·§5.2·§12)

## Global Constraints

- `optimal_pairs`의 반환 형태는 바뀌지 않는다 — `list[tuple[int, int]]`, 각 튜플은 `(작은 id, 큰 id)`, 전체는 정렬된 상태
- API·프론트·DB 스키마 변경 없음
- `pairing.py`는 User 객체나 성별 enum을 모른다. 정수와 정수 집합만 받는다
- 커밋은 각각 그 자체로 통과 상태여야 한다 (`CLAUDE.md` 브랜치 기준)
- `-BIG` 상수는 `-1e18`, float64 정확 정수 한계는 `2 ** 53`
- 브랜치: `feat/matching-scipy`, base `main`, 병합은 PR

---

### Task 1: scipy 의존성 추가

networkx는 아직 남겨둔다. 이 커밋 시점에는 scipy를 아무도 쓰지 않으므로 전부 통과 상태다.

**Files:**
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: 없음
- Produces: `scipy.optimize.linear_sum_assignment`, `numpy`를 Task 2가 import할 수 있는 상태

- [ ] **Step 1: 브랜치 생성**

```bash
git checkout main
git checkout -b feat/matching-scipy
```

- [ ] **Step 2: 의존성 추가**

`backend/pyproject.toml`의 `dependencies` 목록에서 `networkx>=3.6.1` 아래에 한 줄 추가한다.

```toml
    "networkx>=3.6.1",
    "scipy>=1.18",
```

numpy는 scipy가 끌고 오므로 명시하지 않는다.

- [ ] **Step 3: 설치**

Run: `cd backend && uv sync`
Expected: `scipy`, `numpy`가 설치됨

- [ ] **Step 4: import 확인**

Run: `cd backend && uv run python -c "from scipy.optimize import linear_sum_assignment; import numpy; print('ok')"`
Expected: `ok`

- [ ] **Step 5: 기존 테스트가 그대로 통과하는지**

Run: `cd backend && uv run pytest -q`
Expected: 이전과 같은 개수 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(backend): scipy 의존성 추가"
```

---

### Task 2: `optimal_pairs`를 scipy로 교체

이 태스크는 한 커밋이어야 한다. 시그니처가 바뀌므로 구현·호출부·기존 테스트가 동시에 움직이지 않으면 중간 상태가 깨진다.

**Files:**
- Modify: `backend/app/services/pairing.py` (전체 교체)
- Modify: `backend/app/services/matching.py:248` (호출부 1줄)
- Modify: `backend/tests/test_pairing.py` (기존 8개 시그니처 + 신규 6개)

**Interfaces:**
- Consumes: Task 1이 설치한 `scipy.optimize.linear_sum_assignment`, `numpy`
- Produces: `optimal_pairs(scores: Mapping[tuple[int, int], float], male_ids: Collection[int]) -> list[tuple[int, int]]`
  - `scores` — 페어별 궁합 점수표. 키가 정규화돼 있지 않아도 된다 (함수가 다시 정규화한다)
  - `male_ids` — 남성 유저 id 집합. 행렬의 행이 될 쪽을 정하는 데만 쓴다
  - 반환 — 정렬된 `(작은 id, 큰 id)` 튜플 목록
  - 예외 — 가중치가 `2 ** 53`을 넘으면 `ValueError`

- [ ] **Step 1: 신규 테스트 6개를 작성한다**

`backend/tests/test_pairing.py` 끝에 붙인다. 파일 맨 위 import에 `import pytest`를 추가한다.

설계 §8이 나열한 6개 중 "같은 입력 반복 시 같은 결과"는 기존 `test_is_deterministic`이
이미 덮고 있어 중복이다. 그 자리를 `male_ids` 대칭성 테스트로 바꾼다 — 새로 생긴 인자가
결과를 바꾸지 않는다는 것이 이번 교체에서 실제로 검증이 필요한 성질이다.

```python
def test_forbidden_pairs_are_never_matched():
    """간선이 없는 조합은 짝이 될 수 없다 — 짝을 더 만들 수 있어도 마찬가지.

    행렬의 빈 칸(-1e18)이 미매칭 슬롯(0점)에 밀리는지 확인한다.
    2와 4를 붙이면 한 쌍이 늘지만, 둘 사이엔 점수가 없으므로 붙으면 안 된다.
    """
    scores = {(1, 3): 50.0}
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 3)]


def test_leaves_people_unmatched_when_total_score_is_higher():
    """총점이 더 크면 사람을 남긴다 (목적함수 보존).

    1-3 한 쌍(90점)이 1-4 + 2-3 두 쌍(2점)보다 낫다. 패딩이 빠져 전원 강제
    매칭으로 퇴화하면 두 쌍짜리가 나온다.
    """
    scores = {(1, 3): 90.0, (1, 4): 1.0, (2, 3): 1.0}
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 3)]


def test_handles_one_against_many():
    """한쪽이 1명이어도 동작한다 — 직사각 처리 (설계 §5.3)."""
    scores = {(1, 2): 10.0, (1, 3): 30.0, (1, 4): 20.0}
    assert optimal_pairs(scores, male_ids={1}) == [(1, 3)]


def test_works_with_large_sparse_ids():
    """실제 user id는 크고 띄엄띄엄하다.

    tie 항을 raw id로 계산하면 가중치가 float64 정확 범위를 넘어 정밀도
    가드에 걸린다. 순번으로 계산해야 통과한다.
    """
    scores = {
        (50_000, 123_456): 50.0,
        (50_000, 777_777): 50.0,
        (90_000, 123_456): 50.0,
        (90_000, 777_777): 50.0,
    }
    result = optimal_pairs(scores, male_ids={50_000, 90_000})
    # 전부 동점이므로 순번이 가까운 쪽끼리 묶인다
    assert result == [(50_000, 123_456), (90_000, 777_777)]


def test_rejects_weights_beyond_float64_exact_range():
    """가중치가 2**53을 넘으면 tie가 반올림에 먹혀 tie-break가 조용히 무력화된다.

    노드 2개에 거대한 점수를 줘서 곱을 넘긴다 — 그 규모를 만들 필요가 없다.
    """
    with pytest.raises(ValueError):
        optimal_pairs({(1, 2): 1e12}, male_ids={1})


def test_result_is_the_same_whichever_side_is_male():
    """male_ids는 행렬의 축을 정할 뿐 결과를 바꾸지 않는다."""
    scores = {(1, 3): 10.0, (1, 4): 30.0, (2, 3): 20.0, (2, 4): 5.0}
    assert (
        optimal_pairs(scores, male_ids={1, 2})
        == optimal_pairs(scores, male_ids={3, 4})
    )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_pairing.py -q`
Expected: 신규 6개 전부 FAIL. 현재 `optimal_pairs`는 인자를 하나만 받으므로 `TypeError`가 난다.

- [ ] **Step 3: `pairing.py`를 통째로 교체한다**

```python
"""점수표 → 최적 짝. 유저·설문을 모른다 (설계 §2.1)."""

from collections.abc import Collection, Mapping

import numpy as np
from scipy.optimize import linear_sum_assignment

_SCALE = 1000  # 소수점 점수를 정수로. 정수라야 아래 tie-break 계산이 정확하다
_MATCH_BONUS = 1  # 0점 페어도 매칭되게 하는 최소 가중치 (최소 점수 컷 없음)
_FORBIDDEN = -1e18  # 행렬의 빈 칸. 미매칭(0점)에 항상 밀려 절대 선택되지 않는다
_EXACT_INT_LIMIT = 2 ** 53  # float64가 정수를 정확히 담는 한계


def optimal_pairs(
    scores: Mapping[tuple[int, int], float],
    male_ids: Collection[int],
) -> list[tuple[int, int]]:
    """점수 합이 최대가 되는 짝 목록. 같은 입력은 항상 같은 결과를 낸다.

    가중치를 `점수 × big − tie` 형태의 정수로 만든다. tie 항의 총합이 big보다
    작으므로 점수 합이 항상 우선하고, 점수가 같을 때만 tie가 승부를 가른다.

    tie는 두 사람의 **등장 순번** 차이의 제곱이다. 제곱이라 순번이 먼 페어가
    급격히 손해를 보고, 동점일 때는 앞 순번끼리 먼저 묶이는 조합이 이긴다
    (설계 §5.2). raw user id로 계산하면 가중치가 float64의 정확 정수 범위를
    넘어 tie가 반올림에 먹힌다.

    행렬은 미매칭 슬롯까지 포함한 정사각이다. 미매칭이 항상 0점으로 가능하므로
    헝가리안이 강제하는 전원 매칭이 목적함수를 바꾸지 않는다.
    """
    if not scores:
        return []

    normalized = {
        ((a, b) if a < b else (b, a)): value for (a, b), value in scores.items()
    }
    ids = sorted({node for key in normalized for node in key})
    rank = {user_id: index for index, user_id in enumerate(ids)}
    men = [i for i in ids if i in male_ids]
    women = [i for i in ids if i not in male_ids]

    total = len(ids)
    tie_bound = (total + 1) ** 2        # (순번 차이)² 의 상한
    big = tie_bound * (total // 2 + 1)  # 한 매칭에 들어갈 수 있는 tie 총합보다 크다

    def _base(value: float) -> int:
        return int(round(value * _SCALE)) + _MATCH_BONUS

    if max(_base(v) for v in normalized.values()) * big > _EXACT_INT_LIMIT:
        raise ValueError(
            f"가중치가 float64 정확 정수 범위를 넘는다 (풀 {total}명). "
            "점수 스케일을 줄여야 한다"
        )

    n, m = len(men), len(women)
    row = {user_id: index for index, user_id in enumerate(men)}
    col = {user_id: index for index, user_id in enumerate(women)}

    # 왼쪽 위 n×m 이 실제 점수, 나머지는 미매칭 슬롯이다
    profit = np.full((n + m, n + m), _FORBIDDEN)
    profit[n:, m:] = 0.0                      # 남는 슬롯끼리 만나는 칸
    for (a, b), value in normalized.items():
        man, woman = (a, b) if a in row else (b, a)
        profit[row[man], col[woman]] = _base(value) * big - (rank[b] - rank[a]) ** 2
    for index in range(n):
        profit[index, m + index] = 0.0        # 남 index 를 미매칭으로 두는 선택
    for index in range(m):
        profit[n + index, index] = 0.0        # 여 index 를 미매칭으로 두는 선택

    rows, cols = linear_sum_assignment(profit, maximize=True)
    pairs = []
    for i, j in zip(rows, cols):
        if i < n and j < m:
            assert profit[i, j] != _FORBIDDEN, "간선 없는 페어가 선택됐다"
            pairs.append((men[i], women[j]))
    return sorted((a, b) if a < b else (b, a) for a, b in pairs)
```

- [ ] **Step 4: 호출부를 고친다**

`backend/app/services/matching.py:248`. 바로 위 줄에 `male_ids`가 이미 있다.

```python
    male_ids = {user.id for user in men}
    pairs = guaranteed + optimal_pairs(remaining, male_ids)
```

- [ ] **Step 5: 기존 테스트 8개에 `male_ids`를 붙인다**

기존 호출을 아래처럼 바꾼다. **기대값은 하나도 바꾸지 않는다** — 바꿔야 한다면 그건 교체가 동작을 바꿨다는 뜻이므로 멈추고 보고한다.

```python
def test_empty_input():
    assert optimal_pairs({}, male_ids=set()) == []


def test_single_pair():
    assert optimal_pairs({(1, 2): 50.0}, male_ids={1}) == [(1, 2)]


# test_beats_greedy 안
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 4), (2, 3)]


def test_zero_score_pairs_are_still_matched():
    assert optimal_pairs({(1, 2): 0.0}, male_ids={1}) == [(1, 2)]


# test_prefers_matching_more_people 안
# 간선이 (1,2) (1,3) (2,4) 이므로 1과 4가 같은 쪽이다
    assert optimal_pairs(scores, male_ids={1, 4}) == [(1, 3), (2, 4)]


# test_ties_prefer_smaller_ids 안
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 3), (2, 4)]


# test_is_deterministic 안 — 6-사이클 1-2-4-6-5-3-1 의 한쪽은 {1, 4, 5}
    assert optimal_pairs(scores, male_ids={1, 4, 5}) == optimal_pairs(
        reversed_scores, male_ids={1, 4, 5}
    )


# test_leftover_when_counts_differ 안
    assert optimal_pairs(scores, male_ids={1, 2, 3}) == [(2, 4)]
```

- [ ] **Step 6: pairing 테스트를 통과시킨다**

Run: `cd backend && uv run pytest tests/test_pairing.py -q`
Expected: 14개 전부 통과 (기존 8 + 신규 6)

- [ ] **Step 7: 매칭 테스트가 그대로 통과하는지 확인한다**

Run: `cd backend && uv run pytest tests/test_matching.py -q`
Expected: 29개 전부 통과. **기대값을 고쳐야 하는 테스트가 하나라도 있으면 멈추고 보고한다** — 촘촘한 id(1..N)에서는 순번 압축 전후의 가중치가 수학적으로 동일하므로 결과가 달라질 이유가 없다.

- [ ] **Step 8: 신규 테스트가 실제로 무언가를 잡는지 뮤테이션으로 확인한다**

각각 `pairing.py`를 일시적으로 고쳐 해당 테스트가 FAIL하는지 보고, 확인 후 되돌린다.

| 뮤테이션 | FAIL해야 하는 테스트 |
|---|---|
| `profit[index, m + index] = 0.0` 줄 삭제 (남 미매칭 슬롯 제거) | `test_leaves_people_unmatched_when_total_score_is_higher` |
| `rank[b] - rank[a]` → `b - a` (순번 → raw id) | `test_works_with_large_sparse_ids` |
| 정밀도 가드 `if` 블록 삭제 | `test_rejects_weights_beyond_float64_exact_range` |

Run(예): `cd backend && uv run pytest tests/test_pairing.py -q -k "unmatched or sparse or float64"`

- [ ] **Step 9: 전체 스위트**

Run: `cd backend && uv run pytest -q`
Expected: 전부 통과

- [ ] **Step 10: 실제 코드로 속도를 확인한다**

임시 스크립트를 스크래치패드에 만들어 돌린다 (커밋하지 않는다).

```python
import random, time
from app.services.pairing import optimal_pairs

rnd = random.Random(7)
men, women = list(range(1, 251)), list(range(251, 501))
scores = {(a, b): rnd.uniform(0, 100) for a in men for b in women if rnd.random() > 0.2}
t = time.perf_counter()
optimal_pairs(scores, set(men))
print(f"500명 {time.perf_counter() - t:.3f}s")
```

Expected: 1초 미만. 교체 전 같은 조건이 14초대였다.

- [ ] **Step 11: 커밋**

```bash
git add backend/app/services/pairing.py backend/app/services/matching.py backend/tests/test_pairing.py
git commit -m "perf(backend): 매칭 엔진 networkx → scipy"
```

---

### Task 3: networkx 의존성 제거

**Files:**
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Consumes: Task 2가 `pairing.py`에서 networkx를 걷어낸 상태
- Produces: 없음

- [ ] **Step 1: 사용처가 정말 없는지 확인한다**

Run: `cd backend && grep -rn "networkx" app tests --include=*.py`
Expected: 출력 없음

- [ ] **Step 2: 의존성 제거**

`backend/pyproject.toml`의 `dependencies`에서 `"networkx>=3.6.1",` 줄을 지운다.

- [ ] **Step 3: 재설치**

Run: `cd backend && uv sync`
Expected: networkx 제거됨

- [ ] **Step 4: 전체 스위트**

Run: `cd backend && uv run pytest -q`
Expected: 전부 통과

- [ ] **Step 5: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(backend): networkx 의존성 제거"
```

---

### Task 4: `eligible_users` N+1 제거 (후속 티켓 M1)

**Files:**
- Modify: `backend/app/services/matching.py` (`eligible_users` 함수, 상단 import 1줄)
- Test: `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: 없음 (Task 2·3과 독립)
- Produces: 없음. `eligible_users(db) -> list[User]` 시그니처와 반환은 그대로

`eligible_users`(매칭 대상자 조회 함수)가 돌려준 User를 `_execute`가 `user.survey.answers`로 하나씩 읽는다. 지연 로딩이라 유저 수만큼 추가 쿼리가 나간다 — 1,000명이면 1,001번이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_matching.py` 끝에 붙인다.

```python
def test_eligible_users_loads_surveys_in_one_query():
    """설문을 유저마다 따로 읽으면 1,000명에 쿼리가 1,001번 나간다 (후속 티켓 M1).

    joinedload가 빠지면 아래 설문 접근이 추가 SELECT를 일으켜 카운트가 늘어난다.
    """
    from sqlalchemy import event

    db = TestingSessionLocal()
    for i in range(5):
        make_user(db, f"n{i}@test.com", responses=NIGHT)

    statements = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", record)
    try:
        users = matching.eligible_users(db)
        _ = [u.survey.answers for u in users]  # 설문을 실제로 만진다
    finally:
        event.remove(db.bind, "before_cursor_execute", record)

    selects = [s for s in statements if s.strip().upper().startswith("SELECT")]
    assert len(selects) == 1, f"쿼리 {len(selects)}번: {selects}"
    db.close()
```

`event.remove`는 `event.listen`에 넘긴 것과 **같은 함수 객체**를 요구한다. 람다를 두 번 쓰면 제거에 실패하므로 위처럼 이름 있는 함수로 쓴다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd backend && uv run pytest tests/test_matching.py::test_eligible_users_loads_surveys_in_one_query -q`
Expected: FAIL — `쿼리 6번` (목록 1 + 유저별 설문 5)

- [ ] **Step 3: joinedload를 붙인다**

`backend/app/services/matching.py` 상단 import를 바꾼다.

```python
from sqlalchemy.orm import Session, joinedload
```

`eligible_users`의 쿼리에 옵션을 건다.

```python
    return (
        db.query(User)
        .options(joinedload(User.survey))
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd backend && uv run pytest tests/test_matching.py::test_eligible_users_loads_surveys_in_one_query -q`
Expected: PASS

- [ ] **Step 5: 전체 스위트**

Run: `cd backend && uv run pytest -q`
Expected: 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add backend/app/services/matching.py backend/tests/test_matching.py
git commit -m "perf(backend): eligible_users 설문 N+1 제거"
```

---

### Task 5: 매칭 알고리즘 스펙에 반영

**Files:**
- Modify: `docs/superpowers/specs/2026-08-21-matching-algorithm-design.md` (§5.1, §5.2, §12)

**Interfaces:**
- Consumes: Task 2가 확정한 구현
- Produces: 없음

스펙은 하나다. §5.1이 아직 "networkx를 고른 이유"를 설명하고 있어 코드와 어긋난다.

- [ ] **Step 1: §5.1을 교체한다**

`### 5.1 알고리즘` 아래의 선택 근거 문단과 성능표를 아래로 바꾼다.

    ### 5.1 알고리즘

    `scipy.optimize.linear_sum_assignment`(헝가리안)를 사용한다.

    남↔여 간선만 존재하는 이분 그래프라 행렬로 표현할 수 있다. 헝가리안은 C 구현이라
    순수 Python인 `networkx.max_weight_matching`보다 두세 자릿수 빠르다.

    헝가리안은 작은 쪽 전원을 강제로 짝지우므로, 미매칭을 0점 선택지로 넣은
    `(남 + 여)` 정사각 패딩 행렬을 쓴다. 미매칭이 항상 0점으로 가능하므로
    금지 페어(음수)는 절대 선택되지 않고, 남녀 인원이 달라도 남는 쪽이 자기
    미매칭 슬롯으로 흘러간다. 목적함수는 §4·§5.2 그대로다.

    **성능** (2026-08-30 실측):

    | 풀 규모 | 점수 계산 | 짝 계산 |
    |---|---|---|
    | 200명 | 0.3s | 0.004s |
    | 500명 | 1.9s | 0.034s |
    | 1,000명 | ~8s | 0.14s |
    | 2,000명 | — | 0.68s |

    병목은 이제 짝 계산이 아니라 점수 계산이다 (O(n²)). 2,000명대에서 다시 검토한다.

    **한계.** float64는 정수를 2⁵³까지만 정확히 담는다. 가중치가 이를 넘으면 tie 항이
    반올림에 먹혀 §5.2의 결정론이 조용히 깨지므로, 넘으면 예외를 던진다. 풀 약 4,100명이
    한계이며 그때는 점수 스케일 축소가 필요하다.

    교체 이력과 실측 근거: `2026-08-30-matching-performance-design.md`

- [ ] **Step 2: §5.2를 정정한다**

`### 5.2 결정론성` 본문을 아래로 바꾼다.

    ### 5.2 결정론성

    점수가 같은 조합이 여럿일 때 라이브러리가 임의로 고르면 실행할 때마다 결과가 달라져
    테스트가 불안정해진다. `user_id` 기준 정렬 + 동점 시 **앞 순번 우선**으로 고정한다.
    **같은 입력은 항상 같은 결과를 낸다.**

    순번은 그 라운드 풀 안에서의 등장 순서(0부터)다. id 순서는 보존하되 간격은 무시한다 —
    raw id 간격으로 계산하면 가중치가 float64의 정확 정수 범위를 넘는다 (§5.1 한계).

- [ ] **Step 3: §12에서 해소된 항목을 정리한다**

`| 대규모 실행 (§5.1) | 풀 1,000명대 도달 전 필수 — 비동기 실행(백그라운드 + 진행 폴링) 또는 scipy 교체 |` 줄을 아래로 바꾼다.

    | ~~대규모 실행 (§5.1)~~ | ✅ scipy 교체 완료 (2026-08-30). 다음 한계는 점수 계산 O(n²), 2,000명대에서 재검토 |

- [ ] **Step 4: 커밋**

```bash
git add docs/superpowers/specs/2026-08-21-matching-algorithm-design.md
git commit -m "docs(spec): 5.1 scipy 교체 반영, 5.2 tie-break 기준 정정"
```

---

### Task 6: 검증 후 PR

**Files:** 없음

- [ ] **Step 1: 백엔드 전체**

Run: `cd backend && uv run pytest -q`
Expected: 전부 통과 (main 기준 242 + 이 브랜치 신규 7)

- [ ] **Step 2: 프론트가 영향받지 않았는지**

Run: `cd frontend && npx vitest run && npx tsc --noEmit && npx eslint src --max-warnings 0`
Expected: 전부 통과. 이 브랜치는 프론트를 건드리지 않는다

- [ ] **Step 3: 사용자에게 push·PR 허락을 받는다**

`CLAUDE.md` — 커밋/브랜치/푸시는 반드시 허락 후만 실행

- [ ] **Step 4: push + PR**

```bash
git push -u origin feat/matching-scipy
gh pr create --base main --head feat/matching-scipy --title "perf: 매칭 엔진 networkx → scipy"
```

---

## 되돌리기

`pairing.py` 하나가 되돌림 지점이다. `optimal_pairs`의 반환 형태가 그대로라
Task 2의 커밋을 revert하고 networkx 의존성을 되살리면 이전 동작으로 돌아간다.
DB 스키마·API·프론트가 안 바뀌므로 마이그레이션 되돌림은 없다.
