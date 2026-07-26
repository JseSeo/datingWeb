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
