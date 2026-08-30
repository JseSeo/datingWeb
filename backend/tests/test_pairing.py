import pytest

from app.services.pairing import optimal_pairs


def test_empty_input():
    assert optimal_pairs({}, male_ids=set()) == []


def test_single_pair():
    assert optimal_pairs({(1, 2): 50.0}, male_ids={1}) == [(1, 2)]


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
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 4), (2, 3)]


def test_zero_score_pairs_are_still_matched():
    """최소 점수 컷이 없다 — 0점짜리도 짝지어야 한다 (설계 §1)."""
    assert optimal_pairs({(1, 2): 0.0}, male_ids={1}) == [(1, 2)]


def test_prefers_matching_more_people():
    """1-2를 붙이면 3,4가 남는다. 셋 다 붙는 조합이 이긴다."""
    scores = {(1, 2): 40.0, (1, 3): 20.0, (2, 4): 20.0}
    # 간선이 (1,2) (1,3) (2,4) 이므로 1과 4가 같은 쪽이다
    assert optimal_pairs(scores, male_ids={1, 4}) == [(1, 3), (2, 4)]


def test_ties_prefer_smaller_ids():
    """동점이면 작은 id 우선 (설계 §5.2)."""
    scores = {(1, 3): 50.0, (1, 4): 50.0, (2, 3): 50.0, (2, 4): 50.0}
    assert optimal_pairs(scores, male_ids={1, 2}) == [(1, 3), (2, 4)]


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
    # 6-사이클 1-2-4-6-5-3-1 의 한쪽은 {1, 4, 5}
    assert optimal_pairs(scores, male_ids={1, 4, 5}) == optimal_pairs(
        reversed_scores, male_ids={1, 4, 5}
    )


def test_leftover_when_counts_differ():
    """3명 대 1명 — 한 쌍만 나오고 나머지는 미매칭 (설계 §5.3)."""
    scores = {(1, 4): 10.0, (2, 4): 30.0, (3, 4): 20.0}
    assert optimal_pairs(scores, male_ids={1, 2, 3}) == [(2, 4)]


def test_ignores_male_ids_absent_from_scores():
    """`male_ids`에 점수표에 없는 id가 섞여도 무시된다.

    노드 집합은 `male_ids`가 아니라 `scores`에서 뽑는다. 실제 라운드마다 이 상황이
    생긴다 — `matching.py`는 그 라운드의 남성 전원을 `male_ids`로 넘기는데,
    `remaining`에서는 확정 페어가 이미 빠져 있기 때문이다. 2는 행렬에 들어가지
    않아야 하고, 유령 짝이 생겨서도 안 된다.
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

    노드 2개에 거대한 점수를 줘서 곱을 넘긴다 — 5,600명을 만들 필요가 없다.
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
