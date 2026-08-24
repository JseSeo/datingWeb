import pytest

from app.services.scoring import PAIRS, satisfaction


def sat(base, pref, self_):
    """문항 하나만 담은 responses 두 개로 만족도를 구한다."""
    return satisfaction(base, pref, self_)


def test_every_pref_question_has_a_self_pair():
    """카탈로그 정합성 — grooming_self만 짝이 없다 (설계 §3.1)."""
    self_ids = {self_q.id for _, self_q in PAIRS.values()}
    assert "grooming_self" not in self_ids
    assert "height" in PAIRS and "living" in PAIRS


def test_height_bucket_distance():
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 180}) == 1.0
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 170}) == 0.5
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 160}) == 0.0
    # 경계: 175는 175_185 구간, 185는 o185 구간
    assert sat("height", {"height_pref": "175_185"}, {"height_self": 175}) == 1.0
    assert sat("height", {"height_pref": "o185"}, {"height_self": 185}) == 1.0


def test_no_pref_and_missing_are_excluded():
    assert sat("height", {"height_pref": "any"}, {"height_self": 180}) is None
    assert sat("height", {}, {"height_self": 180}) is None
    assert sat("height", {"height_pref": "175_185"}, {}) is None
    # 다중선택에 '상관없음'이 섞여 있으면 다른 값과 함께 골랐어도 제외 (설계 §3.1)
    assert sat("style", {"style_pref": ["casual", "any"]}, {"style_self": ["formal"]}) is None


def test_multi_select_rules():
    assert sat("face", {"face_pref": ["type_a", "type_b"]}, {"face_self": "type_b"}) == 1.0
    assert sat("face", {"face_pref": ["type_a"]}, {"face_self": "type_b"}) == 0.0
    assert sat("style", {"style_pref": ["casual"]}, {"style_self": ["casual", "street"]}) == 1.0
    assert sat("style", {"style_pref": ["formal"]}, {"style_self": ["casual"]}) == 0.0


def test_tattoo_and_piercing():
    assert sat("tattoo", {"tattoo_pref": "ok"}, {"tattoo_self": "yes"}) == 1.0
    assert sat("tattoo", {"tattoo_pref": "none"}, {"tattoo_self": "no"}) == 1.0
    assert sat("tattoo", {"tattoo_pref": "none"}, {"tattoo_self": "yes"}) == 0.0
    assert sat("piercing", {"piercing_pref": "none"}, {"piercing_self": "yes"}) == 0.0


def test_politics_ordinal_and_unknown():
    assert sat("politics", {"politics_pref": "moderate"}, {"politics_self": "moderate"}) == 1.0
    assert sat("politics", {"politics_pref": "moderate"}, {"politics_self": "progressive"}) == 0.5
    assert sat("politics", {"politics_pref": "progressive"}, {"politics_self": "conservative"}) == 0.0
    assert sat("politics", {"politics_pref": "progressive"}, {"politics_self": "unknown"}) == 0.5


def test_religion_other_is_half():
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "none"}) == 1.0
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "buddhist"}) == 0.0
    assert sat("religion", {"religion_pref": ["none"]}, {"religion_self": "other"}) == 0.5


def test_scale_questions():
    assert sat("contact_freq", {"contact_freq_pref": 3}, {"contact_freq_self": 3}) == 1.0
    assert sat("contact_freq", {"contact_freq_pref": 3}, {"contact_freq_self": 4}) == 0.75
    assert sat("affection", {"affection_pref": 1}, {"affection_self": 5}) == 0.0


def test_conflict_style_and_sleep_are_exact_match():
    assert sat("conflict_style", {"conflict_style_pref": "later"}, {"conflict_style_self": "later"}) == 1.0
    assert sat("conflict_style", {"conflict_style_pref": "later"}, {"conflict_style_self": "alone"}) == 0.0
    assert sat("sleep", {"sleep_pref": "night"}, {"sleep_self": "night"}) == 1.0
    assert sat("sleep", {"sleep_pref": "night"}, {"sleep_self": "morning"}) == 0.0


def test_priority_rank_distance():
    same = ["lover", "friend", "self_dev", "family"]
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": same}) == 1.0
    reversed_ = list(reversed(same))
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": reversed_}) == 0.0
    swapped = ["friend", "lover", "self_dev", "family"]
    assert sat("priority_rank", {"priority_rank_pref": same}, {"priority_rank_self": swapped}) == 0.75


def test_budget_and_exercise_ordinal():
    assert sat("date_budget", {"date_budget_pref": "10_20"}, {"date_budget_self": "10_20"}) == 1.0
    assert sat("date_budget", {"date_budget_pref": "10_20"}, {"date_budget_self": "5_10"}) == 0.5
    assert sat("date_budget", {"date_budget_pref": "u5"}, {"date_budget_self": "o30"}) == 0.0
    assert sat("exercise", {"exercise_pref": "w3"}, {"exercise_self": "w1_2"}) == 0.5
    assert sat("exercise", {"exercise_pref": "w3"}, {"exercise_self": "none"}) == 0.0


def test_mapping_tables():
    assert sat("cost_share", {"cost_share_pref": "partner"}, {"cost_share_self": "me"}) == 1.0
    assert sat("cost_share", {"cost_share_pref": "partner"}, {"cost_share_self": "dutch"}) == 0.0
    assert sat("cost_share", {"cost_share_pref": "dutch"}, {"cost_share_self": "richer"}) == 0.5
    assert sat("smoking", {"smoking_pref": "none_only"}, {"smoking_self": "sometimes"}) == 0.0
    assert sat("smoking", {"smoking_pref": "sometimes_ok"}, {"smoking_self": "sometimes"}) == 1.0
    assert sat("smoking", {"smoking_pref": "sometimes_ok"}, {"smoking_self": "yes"}) == 0.0
    assert sat("drinking", {"drinking_pref": "none"}, {"drinking_self": "sometimes"}) == 0.5
    assert sat("drinking", {"drinking_pref": "sometimes_ok"}, {"drinking_self": "often"}) == 0.5
    assert sat("hobby", {"hobby_pref": "indoor"}, {"hobby_self": "both"}) == 1.0
    assert sat("hobby", {"hobby_pref": "indoor"}, {"hobby_self": "outdoor"}) == 0.0


def test_living():
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "independent"}) == 1.0
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "dorm"}) == 0.5
    assert sat("living", {"living_pref": "prefer_independent"}, {"living_self": "home"}) == 0.0


@pytest.mark.parametrize(
    "pref, mine, theirs, expected",
    [
        ("h1", "서울", "서울", 1.0),    # 0홉
        ("h1", "서울", "경기", 0.5),    # 1홉
        ("h1", "서울", "강원", 0.0),    # 2홉
        ("h2", "서울", "강원", 0.5),    # 서울-경기-강원 … 2홉 (브리프 오타 수정: 1.0→0.5, 아래와 동일 패턴)
        ("h2", "서울", "충남", 0.5),    # 서울-경기-충남 … 2홉
        ("h3", "서울", "부산", 0.0),    # 4홉 이상
        ("h3", "서울", "충북", 1.0),    # 2홉
        ("h1", "제주", "제주", 1.0),    # 제주끼리는 0홉
        ("h3", "제주", "서울", 0.0),    # 육로 연결 없음
    ],
)
def test_residence_hops(pref, mine, theirs, expected):
    """거주지는 '내' 거주지도 필요하다 — pref 쪽 responses에서 함께 읽는다 (설계 §3.3)."""
    assert sat("residence", {"residence_pref": pref, "residence_self": mine},
               {"residence_self": theirs}) == expected


def test_residence_needs_my_own_residence():
    assert sat("residence", {"residence_pref": "h1"}, {"residence_self": "서울"}) is None
