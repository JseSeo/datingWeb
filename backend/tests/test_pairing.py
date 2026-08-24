from app.services.pairing import optimal_pairs


def test_empty_input():
    assert optimal_pairs({}) == []


def test_single_pair():
    assert optimal_pairs({(1, 2): 50.0}) == [(1, 2)]


def test_beats_greedy():
    """그리디였다면 틀렸을 케이스 (설계 §11).

    가장 비싼 간선 1-3(10점)을 먼저 집으면 2-4(1점)밖에 안 남아 합 11.
    최적은 1-4(9) + 2-3(9) = 18.
    """
    scores = {
        (1, 3): 10.0,
        (1, 4): 9.0,
        (2, 3): 9.0,
        (2, 4): 1.0,
    }
    assert optimal_pairs(scores) == [(1, 4), (2, 3)]


def test_zero_score_pairs_are_still_matched():
    """최소 점수 컷이 없다 — 0점짜리도 짝지어야 한다 (설계 §1)."""
    assert optimal_pairs({(1, 2): 0.0}) == [(1, 2)]


def test_prefers_matching_more_people():
    """1-2를 붙이면 3,4가 남는다. 셋 다 붙는 조합이 이긴다."""
    scores = {(1, 2): 40.0, (1, 3): 20.0, (2, 4): 20.0}
    assert optimal_pairs(scores) == [(1, 3), (2, 4)]


def test_ties_prefer_smaller_ids():
    """동점이면 작은 id 우선 (설계 §5.2)."""
    scores = {(1, 3): 50.0, (1, 4): 50.0, (2, 3): 50.0, (2, 4): 50.0}
    assert optimal_pairs(scores) == [(1, 3), (2, 4)]


def test_is_deterministic():
    """입력 dict의 키 삽입 순서가 달라도 결과가 같아야 한다 (설계 §5.2).

    1-2-4-6-5-3-1 6-사이클: 모든 간선이 동점(50.0)이라 완전 매칭이 정확히
    둘 존재하고 tie-break 값도 정확히 같다 — 진짜 동점. 내부에서 입력을
    정규화하지 않으면(간선 삽입 순서를 그대로 쓰면) 어느 쪽이 뽑힐지
    입력 순서에 좌우된다는 것을 확인했다(정규화 제거 뮤테이션 시 FAIL).
    """
    scores = {
        (1, 2): 50.0, (2, 4): 50.0, (4, 6): 50.0,
        (5, 6): 50.0, (3, 5): 50.0, (1, 3): 50.0,
    }
    reversed_scores = dict(reversed(list(scores.items())))
    assert optimal_pairs(scores) == optimal_pairs(reversed_scores)


def test_leftover_when_counts_differ():
    """3명 대 1명 — 한 쌍만 나오고 나머지는 미매칭 (설계 §5.3)."""
    scores = {(1, 4): 10.0, (2, 4): 30.0, (3, 4): 20.0}
    assert optimal_pairs(scores) == [(2, 4)]
