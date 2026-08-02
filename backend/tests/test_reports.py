from fastapi.testclient import TestClient


def _register_and_get_headers(
    client: TestClient,
    email: str = "reporter@test.com",
    name: str = "신고자",
    university: str = "서울대학교",
) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": name,
        "university": university,
        "gender": "male",
        "agreed_terms": True,
        "agreed_privacy": True,
        "agreed_age_14": True,
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_create_report_strips_target(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "  대상자  ",
        "target_university": "  연세대학교  ",
        "reason": "부적절한 프로필 사진",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "report"
    assert data["target_name"] == "대상자"
    assert data["target_university"] == "연세대학교"
    assert data["reason"] == "부적절한 프로필 사진"
    assert "id" in data
    assert "created_at" in data


def test_report_requires_target(client: TestClient):
    headers = _register_and_get_headers(client, "r2@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "   ",
        "reason": "학교를 안 적음",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "신고 대상의 이름과 학교를 입력하세요"


def test_suggestion_ignores_target(client: TestClient):
    headers = _register_and_get_headers(client, "r3@test.com")
    response = client.post("/reports", json={
        "type": "suggestion",
        "target_name": "무시되어야 함",
        "target_university": "무시되어야 함",
        "reason": "알림을 꺼두는 기능이 있으면 좋겠어요",
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "suggestion"
    assert data["target_name"] is None
    assert data["target_university"] is None


def test_report_blank_reason(client: TestClient):
    headers = _register_and_get_headers(client, "r4@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": "   ",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "내용을 입력하세요"


def test_report_empty_reason(client: TestClient):
    headers = _register_and_get_headers(client, "r5@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": "",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "내용을 입력하세요"


def test_report_requires_target_name(client: TestClient):
    headers = _register_and_get_headers(client, "r6@test.com")
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "   ",
        "target_university": "연세대학교",
        "reason": "이름을 안 적음",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "신고 대상의 이름과 학교를 입력하세요"


def test_report_self_forbidden(client: TestClient):
    headers = _register_and_get_headers(
        client, "self@test.com", name="자기자신", university="고려대학교",
    )
    response = client.post("/reports", json={
        "type": "report",
        "target_name": " 자기자신 ",
        "target_university": " 고려대학교 ",
        "reason": "자기신고",
    }, headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "자기 자신을 신고할 수 없습니다"


def test_report_unauthorized(client: TestClient):
    response = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": "x",
    })
    assert response.status_code == 401
