from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str = "survey@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김설문",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_save_survey(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.put("/me/survey", json={
        "answers": {"q1": 3, "q2": "강아지파"},
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"] == {"q1": 3, "q2": "강아지파"}
    assert data["updated_at"] is not None


def test_get_survey_after_save(client: TestClient):
    headers = _register_and_get_headers(client, "get@test.com")
    client.put("/me/survey", json={"answers": {"q1": 5}}, headers=headers)
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {"q1": 5}


def test_get_survey_empty_when_none(client: TestClient):
    headers = _register_and_get_headers(client, "empty@test.com")
    response = client.get("/me/survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {}


def test_update_survey_overwrites(client: TestClient):
    headers = _register_and_get_headers(client, "update@test.com")
    client.put("/me/survey", json={"answers": {"q1": 1}}, headers=headers)
    response = client.put("/me/survey", json={"answers": {"q1": 2, "q2": "수정"}}, headers=headers)
    assert response.status_code == 200
    assert response.json()["answers"] == {"q1": 2, "q2": "수정"}


def test_put_survey_unauthorized(client: TestClient):
    response = client.put("/me/survey", json={"answers": {"q1": 1}})
    assert response.status_code == 401


def test_get_survey_unauthorized(client: TestClient):
    response = client.get("/me/survey")
    assert response.status_code == 401
