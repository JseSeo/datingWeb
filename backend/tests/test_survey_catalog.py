from fastapi.testclient import TestClient

from app.survey.catalog import (
    FACE_ANY_ID,
    FACE_TYPES,
    QUESTIONS,
    Category,
)

QUESTION_BY_ID = {q.id: q for q in QUESTIONS}
QUESTION_TYPES = {"single", "multi", "scale", "number", "ranking", "image-single", "image-multi"}


def test_총_45문항():
    assert len(QUESTIONS) == 45


def test_id_중복_없음():
    ids = [q.id for q in QUESTIONS]
    assert len(set(ids)) == len(ids)


def test_section과_type은_허용값만():
    for q in QUESTIONS:
        assert q.section in ("self", "partner"), q.id
        assert q.type in QUESTION_TYPES, q.id


def test_single_multi_문항은_choices_보유():
    for q in QUESTIONS:
        if q.type in ("single", "multi"):
            assert q.choices, f"{q.id}에 choices가 없다"


def test_ranking_문항은_rank_items_보유():
    for q in QUESTIONS:
        if q.type == "ranking":
            assert q.rank_items, f"{q.id}에 rank_items가 없다"


def test_scale_문항은_scale_labels_보유():
    for q in QUESTIONS:
        if q.type == "scale":
            assert q.scale_labels and len(q.scale_labels) == 2


def test_no_pref_id는_partner_문항에만():
    for q in QUESTIONS:
        if q.no_pref_id:
            assert q.section == "partner", f"{q.id}는 self인데 no_pref_id가 있다"


def test_no_pref_id가_choices에_실재한다_비face():
    for q in QUESTIONS:
        if q.no_pref_id and not q.face:
            assert any(c.id == q.no_pref_id for c in q.choices or [])


def test_face_문항의_no_pref_id는_FACE_ANY_ID():
    for q in QUESTIONS:
        if q.face and q.no_pref_id:
            assert q.no_pref_id == FACE_ANY_ID


def test_grooming_self만_male_only():
    assert [q.id for q in QUESTIONS if q.male_only] == ["grooming_self"]


def test_모든_문항이_카테고리를_갖는다():
    for q in QUESTIONS:
        assert isinstance(q.category, Category)


def test_카테고리별_문항수():
    counts = {c: 0 for c in Category}
    for q in QUESTIONS:
        counts[q.category] += 1
    assert counts == {
        Category.APPEARANCE: 11,
        Category.VALUES: 4,
        Category.RELATIONSHIP: 12,
        Category.LIFESTYLE: 18,
    }


def test_모든_pref_문항은_짝이_되는_self_문항을_갖는다():
    """매칭 점수는 `X_pref` ↔ `X_self` 명명 규칙으로 짝을 찾는다.
    이 규칙이 깨지면 2단계 점수 계산이 조용히 그 문항을 건너뛴다."""
    for q in QUESTIONS:
        if q.id.endswith("_pref"):
            mate = q.id[: -len("_pref")] + "_self"
            assert mate in QUESTION_BY_ID, f"{q.id}의 짝 {mate}가 없다"


def test_짝없는_self는_grooming_self뿐():
    orphans = [
        q.id
        for q in QUESTIONS
        if q.id.endswith("_self")
        and (q.id[: -len("_self")] + "_pref") not in QUESTION_BY_ID
    ]
    assert orphans == ["grooming_self"]


def test_pref와_self는_같은_카테고리():
    for q in QUESTIONS:
        if q.id.endswith("_pref"):
            mate = QUESTION_BY_ID[q.id[: -len("_pref")] + "_self"]
            assert q.category == mate.category, f"{q.id}와 {mate.id}의 카테고리가 다르다"


def test_얼굴상_목록():
    assert len(FACE_TYPES) >= 2
    for f in FACE_TYPES:
        assert f.id and f.label and f.image


def test_FACE_ANY_ID는_얼굴상_목록과_겹치지_않는다():
    assert not any(f.id == FACE_ANY_ID for f in FACE_TYPES)


def _headers(client: TestClient, email: str = "catalog@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김카탈",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
        "kakao_id": "register_kakao",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_카탈로그_조회는_로그인_필요(client: TestClient):
    res = client.get("/survey/questions")
    assert res.status_code == 401


def test_카탈로그_45문항_반환(client: TestClient):
    res = client.get("/survey/questions", headers=_headers(client))
    assert res.status_code == 200
    body = res.json()
    assert len(body["questions"]) == 45


def test_카탈로그_응답에_얼굴상_포함(client: TestClient):
    body = client.get("/survey/questions", headers=_headers(client)).json()
    assert len(body["face_types"]) == 4
    assert body["face_any_id"] == "any"
    assert body["face_types"][0]["image"].startswith("/faces/")


def test_카탈로그_문항_필드_형태(client: TestClient):
    body = client.get("/survey/questions", headers=_headers(client)).json()
    by_id = {q["id"]: q for q in body["questions"]}

    height = by_id["height_self"]
    assert height["type"] == "number"
    assert height["unit"] == "cm"
    assert height["section"] == "self"

    pref = by_id["height_pref"]
    assert pref["no_pref_id"] == "any"
    assert [c["id"] for c in pref["choices"]][0] == "u165"

    scale = by_id["contact_freq_self"]
    assert scale["scale_labels"] == ["가끔", "자주"]

    ranking = by_id["priority_rank_self"]
    assert [i["id"] for i in ranking["rank_items"]] == [
        "lover", "friend", "self_dev", "family",
    ]

    assert by_id["grooming_self"]["male_only"] is True
    assert by_id["face_pref"]["face"] is True


def test_카탈로그_응답에_category는_노출하지_않는다(client: TestClient):
    """카테고리 가중치는 내부 매칭 로직 전용이다. 프론트에 흘리지 않는다."""
    body = client.get("/survey/questions", headers=_headers(client)).json()
    assert "category" not in body["questions"][0]


def test_number_question_declares_range():
    """number 문항은 검증 범위를 카탈로그에 선언해야 한다 (검증기가 이걸 읽는다)."""
    from app.survey.catalog import QUESTIONS

    for q in QUESTIONS:
        if q.type == "number":
            assert q.min is not None, f"{q.id}에 min이 없다"
            assert q.max is not None, f"{q.id}에 max가 없다"


def test_catalog_response_exposes_number_range(client: TestClient):
    """프론트 input이 min/max를 그대로 받아야 한다.

    서버만 범위를 알면, 범위를 벗어난 값은 조용히 버려지고 유저는
    저장했다고 믿는다 (이 API는 위반 값을 400으로 되돌리지 않는다).
    """
    res = client.get("/survey/questions", headers=_headers(client))
    assert res.status_code == 200
    height = next(q for q in res.json()["questions"] if q["id"] == "height_self")
    assert height["min"] == 120
    assert height["max"] == 220
