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
    """점수 합이 최대가 되는 짝 목록. 같은 입력은 항상 같은 결과를 낸다 — 행렬이
    입력만으로 완전히 결정되고 `linear_sum_assignment`가 결정적이기 때문이다.

    가중치를 `점수 × big − tie` 형태의 정수로 만든다. tie 항의 총합이 big보다
    작으므로 점수 합이 항상 우선한다.

    tie는 두 사람의 **등장 순번** 차이의 제곱이다. 제곱이라 순번이 먼 페어가
    급격히 손해를 봐 앞 순번끼리 묶이는 쪽으로 편향된다. 다만 이 편향이 승부를
    유일하게 결정하지는 않는다 — 간선이 빠진 그래프에서 3쌍 이상이면 점수 합과
    tie 합이 둘 다 같은 경우가 생길 수 있고, 그때는 scipy 내부 규칙이 남은
    동점을 가른다.

    raw user id로 tie를 계산하면 가중치가 float64의 정확 정수 범위를 넘어
    tie 항이 실제 점수 차이를 삼켜버린다 — 그래서 순번을 쓴다.

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

    if max(abs(_base(v)) for v in normalized.values()) * big > _EXACT_INT_LIMIT:
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
