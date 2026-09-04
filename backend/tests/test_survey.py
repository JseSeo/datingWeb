from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str = "survey@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김설문",
        "university": "서울대학교",
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
        "kakao_id": "register_kakao",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _valid_answers(**overrides):
    ans = {"responses": {"height_self": 175, "height_pref": "175_185"},
           "absolute": []}
    ans.update(overrides)
    return ans


def test_save_survey(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"]["responses"]["height_self"] == 175
    assert data["updated_at"] is not None


def test_get_survey_after_save(client: TestClient):
    headers = _register_and_get_headers(client, "get@test.com")
    client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"]["responses"]["height_pref"] == "175_185"


def test_get_survey_empty_when_none(client: TestClient):
    headers = _register_and_get_headers(client, "empty@test.com")
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {}


def test_update_survey_overwrites(client: TestClient):
    headers = _register_and_get_headers(client, "update@test.com")
    client.put("/me/survey", json={"answers": _valid_answers()}, headers=headers)
    response = client.put("/me/survey", json={
        "answers": _valid_answers(responses={"height_self": 180}, absolute=[])
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"]["responses"] == {"height_self": 180}


def test_put_survey_unauthorized(client: TestClient):
    response = client.put("/me/survey", json={"answers": _valid_answers()})
    assert response.status_code == 401


def test_get_survey_unauthorized(client: TestClient):
    response = client.get("/me/survey")
    assert response.status_code == 401


def test_reject_missing_responses(client: TestClient):
    headers = _register_and_get_headers(client, "r1@test.com")
    res = client.put("/me/survey", json={"answers": {"absolute": []}}, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_not_list(client: TestClient):
    headers = _register_and_get_headers(client, "r2@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1}, "absolute": "nope"}
    }, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_too_many(client: TestClient):
    headers = _register_and_get_headers(client, "r3@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1, "b": 2, "c": 3},
                    "absolute": ["a", "b", "c"]}
    }, headers=headers)
    assert res.status_code == 400


def test_reject_absolute_unknown_id(client: TestClient):
    headers = _register_and_get_headers(client, "r4@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"a": 1}, "absolute": ["ghost"]}
    }, headers=headers)
    assert res.status_code == 400


def test_unknown_question_id_is_dropped_not_rejected(client: TestClient):
    """모르는 문항 id는 400이 아니라 조용히 버린다.

    유일한 클라이언트가 우리 프론트라, 카탈로그가 바뀌는 사이 오래된 탭에서
    저장하는 유저를 400으로 막아버리는 쪽이 더 나쁘다.
    """
    headers = _register_and_get_headers(client, "d1@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"height_self": 175, "ghost_self": "x"},
                    "absolute": []}
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["answers"]["responses"] == {"height_self": 175}


def test_invalid_value_is_dropped(client: TestClient):
    headers = _register_and_get_headers(client, "d2@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"height_pref": "banana"}, "absolute": []}
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["answers"]["responses"] == {}


def test_absolute_is_dropped_when_its_question_value_was_dropped(client: TestClient):
    """값이 버려지면 그 문항을 가리키던 절대질문도 같이 버려야 한다.

    구조 검증(`absolute ⊆ responses`)은 값을 버리기 *전*에 돌기 때문에
    이 고아를 잡지 못한다.
    """
    headers = _register_and_get_headers(client, "d3@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"height_pref": "banana"},
                    "absolute": ["height_pref"]}
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["answers"]["absolute"] == []


def test_absolute_drops_non_pref_question(client: TestClient):
    """절대질문은 '원하는 상대' 문항만 의미가 있다.

    `absolute_ok`가 `_pref`로 끝나지 않는 id를 어차피 무시하므로,
    남겨두면 유저에게 "이 조건이 걸렸다"고 거짓말하는 셈이 된다.
    """
    headers = _register_and_get_headers(client, "d4@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"height_self": 175}, "absolute": ["height_self"]}
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["answers"]["absolute"] == []


def test_unhashable_value_never_reaches_storage(client: TestClient):
    """회귀: 이 값이 저장되면 scoring의 `_table`이 unhashable TypeError로 터진다."""
    headers = _register_and_get_headers(client, "d5@test.com")
    res = client.put("/me/survey", json={
        "answers": {"responses": {"height_pref": {"a": 1},
                                  "style_self": [{"a": 1}],
                                  "priority_rank_self": [1, "a", None, {}]},
                    "absolute": []}
    }, headers=headers)
    assert res.status_code == 200
    assert res.json()["answers"]["responses"] == {}
