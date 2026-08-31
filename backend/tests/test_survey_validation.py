"""`sanitize_responses` — 카탈로그로 검증한 값만 남긴다.

이 모듈은 순수 함수라 DB·HTTP 없이 단독으로 검증한다.
"""

from app.survey.validation import sanitize_responses


def test_unknown_question_id_is_dropped():
    clean, dropped = sanitize_responses({"height_self": 175, "nope_self": "x"})
    assert clean == {"height_self": 175}
    assert dropped == ["nope_self"]


def test_single_keeps_known_choice_id():
    clean, dropped = sanitize_responses({"height_pref": "175_185"})
    assert clean == {"height_pref": "175_185"}
    assert dropped == []


def test_single_drops_unknown_choice_id():
    clean, dropped = sanitize_responses({"height_pref": "banana"})
    assert clean == {}
    assert dropped == ["height_pref"]


def test_single_drops_non_string_value():
    """dict 값이 그대로 저장되면 scoring의 `_table`에서 unhashable TypeError가 난다."""
    clean, dropped = sanitize_responses({"height_pref": {"a": 1}})
    assert clean == {}
    assert dropped == ["height_pref"]


def test_multi_keeps_known_choice_ids():
    clean, dropped = sanitize_responses({"style_self": ["casual", "street"]})
    assert clean == {"style_self": ["casual", "street"]}
    assert dropped == []


def test_multi_drops_when_any_choice_is_unknown():
    clean, dropped = sanitize_responses({"style_self": ["casual", "banana"]})
    assert clean == {}
    assert dropped == ["style_self"]


def test_multi_drops_unhashable_element():
    """`[{"a": 1}]`이 남으면 scoring의 `_intersects`가 set()에서 터진다."""
    clean, dropped = sanitize_responses({"style_self": [{"a": 1}]})
    assert clean == {}
    assert dropped == ["style_self"]


def test_multi_removes_duplicates_keeping_order():
    clean, _ = sanitize_responses({"style_self": ["casual", "casual", "street"]})
    assert clean == {"style_self": ["casual", "street"]}


def test_multi_drops_bare_string():
    clean, dropped = sanitize_responses({"style_self": "casual"})
    assert clean == {}
    assert dropped == ["style_self"]


def test_scale_keeps_value_in_range():
    clean, dropped = sanitize_responses({"contact_freq_self": 3})
    assert clean == {"contact_freq_self": 3}
    assert dropped == []


def test_scale_drops_value_out_of_range():
    clean, dropped = sanitize_responses({"contact_freq_self": 6})
    assert clean == {}
    assert dropped == ["contact_freq_self"]


def test_scale_drops_bool():
    """bool은 int의 하위형이라 isinstance(True, int)가 참이다. 따로 막아야 한다."""
    clean, dropped = sanitize_responses({"contact_freq_self": True})
    assert clean == {}
    assert dropped == ["contact_freq_self"]


def test_scale_drops_string():
    clean, dropped = sanitize_responses({"contact_freq_self": "3"})
    assert clean == {}
    assert dropped == ["contact_freq_self"]


def test_ranking_keeps_exact_permutation():
    order = ["family", "lover", "self_dev", "friend"]
    clean, dropped = sanitize_responses({"priority_rank_self": order})
    assert clean == {"priority_rank_self": order}
    assert dropped == []


def test_ranking_drops_incomplete_list():
    clean, dropped = sanitize_responses({"priority_rank_self": ["lover", "friend"]})
    assert clean == {}
    assert dropped == ["priority_rank_self"]


def test_ranking_drops_mixed_types():
    """`[1, "a"]`가 남으면 scoring의 `_priority_rank`가 sorted()에서 터진다."""
    clean, dropped = sanitize_responses({"priority_rank_self": [1, "a", None, {}]})
    assert clean == {}
    assert dropped == ["priority_rank_self"]


def test_ranking_drops_duplicate_items():
    clean, dropped = sanitize_responses(
        {"priority_rank_self": ["lover", "lover", "friend", "family"]})
    assert clean == {}
    assert dropped == ["priority_rank_self"]


def test_image_single_keeps_face_type_id():
    clean, dropped = sanitize_responses({"face_self": "type_a"})
    assert clean == {"face_self": "type_a"}
    assert dropped == []


def test_image_single_drops_any_because_face_self_has_no_no_pref():
    """`face_self`는 '나'라서 '상관없음'이 없다. `face_pref`만 any를 받는다."""
    clean, dropped = sanitize_responses({"face_self": "any"})
    assert clean == {}
    assert dropped == ["face_self"]


def test_image_single_drops_unknown_face_type():
    clean, dropped = sanitize_responses({"face_self": "type_z"})
    assert clean == {}
    assert dropped == ["face_self"]


def test_image_multi_keeps_face_type_ids():
    clean, dropped = sanitize_responses({"face_pref": ["type_a", "type_b"]})
    assert clean == {"face_pref": ["type_a", "type_b"]}
    assert dropped == []


def test_image_multi_keeps_any():
    clean, dropped = sanitize_responses({"face_pref": ["any"]})
    assert clean == {"face_pref": ["any"]}
    assert dropped == []


def test_image_multi_drops_unknown_face_type():
    clean, dropped = sanitize_responses({"face_pref": ["type_a", "type_z"]})
    assert clean == {}
    assert dropped == ["face_pref"]


def test_number_keeps_value_in_catalog_range():
    clean, dropped = sanitize_responses({"height_self": 175})
    assert clean == {"height_self": 175}
    assert dropped == []


def test_number_drops_value_above_max():
    clean, dropped = sanitize_responses({"height_self": 9999})
    assert clean == {}
    assert dropped == ["height_self"]


def test_number_drops_value_below_min():
    clean, dropped = sanitize_responses({"height_self": -5})
    assert clean == {}
    assert dropped == ["height_self"]


def test_number_drops_bool():
    clean, dropped = sanitize_responses({"height_self": True})
    assert clean == {}
    assert dropped == ["height_self"]


def test_number_drops_string():
    clean, dropped = sanitize_responses({"height_self": "175"})
    assert clean == {}
    assert dropped == ["height_self"]


def test_every_catalog_type_has_a_rule():
    """규칙 없는 타입은 검증 없이 통과한다. 새 타입이 조용히 뚫는 걸 막는다."""
    from app.survey.catalog import QUESTIONS
    from app.survey.validation import _RULES

    missing = {q.type for q in QUESTIONS} - set(_RULES)
    assert not missing, f"검증 규칙 없는 타입: {missing}"
