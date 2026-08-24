"""점수표 → 최적 짝. 유저·설문을 모른다 (설계 §2.1)."""

from collections.abc import Mapping

import networkx as nx

_SCALE = 1000  # 소수점 점수를 정수로. 정수라야 아래 tie-break 계산이 정확하다
_MATCH_BONUS = 1  # 0점 페어도 매칭되게 하는 최소 가중치 (최소 점수 컷 없음)


def optimal_pairs(scores: Mapping[tuple[int, int], float]) -> list[tuple[int, int]]:
    """점수 합이 최대가 되는 짝 목록. 같은 입력은 항상 같은 결과를 낸다.

    가중치를 `점수 × BIG − tie` 형태의 정수로 만든다. tie 항의 총합이 BIG보다
    작으므로 점수 합이 항상 우선하고, 점수가 같을 때만 tie가 승부를 가른다.

    tie는 페어 폭 `(b − a)²`이다. 제곱이라 폭이 넓은 페어가 급격히 손해를 보고,
    그 결과 동점일 때는 작은 id끼리 먼저 묶이는 조합이 이긴다 (설계 §5.2).
    """
    if not scores:
        return []

    normalized = {
        ((a, b) if a < b else (b, a)): value for (a, b), value in scores.items()
    }
    ids = sorted({node for key in normalized for node in key})
    span = ids[-1] + 1
    tie_bound = span * span            # (b − a)² 의 상한
    big = tie_bound * (len(ids) // 2 + 1)  # 한 매칭에 들어갈 수 있는 tie 총합보다 크다

    graph = nx.Graph()
    graph.add_nodes_from(ids)  # 정렬된 순서로 넣어 순회 순서를 고정한다
    for a, b in sorted(normalized):
        base = int(round(normalized[(a, b)] * _SCALE)) + _MATCH_BONUS
        graph.add_edge(a, b, weight=base * big - (b - a) ** 2)

    matched = nx.max_weight_matching(graph, maxcardinality=False)
    return sorted((a, b) if a < b else (b, a) for a, b in matched)
