from fastapi.testclient import TestClient


def test_register_new_user(client: TestClient):
    response = client.post("/auth/register", json={
        "email": "test@korea.ac.kr",
        "password": "password123",
        "name": "김테스트",
        "university": "고려대학교",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@korea.ac.kr"
    assert data["status"] == "pending"
    assert "password_hash" not in data


def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "dup@korea.ac.kr",
        "password": "password123",
        "name": "김중복",
        "university": "고려대학교",
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_register_weak_password(client: TestClient):
    response = client.post("/auth/register", json={
        "email": "weak@korea.ac.kr",
        "password": "123",
        "name": "김약함",
        "university": "고려대학교",
    })
    assert response.status_code == 422


def test_login_success(client: TestClient):
    client.post("/auth/register", json={
        "email": "login@korea.ac.kr",
        "password": "password123",
        "name": "김로그인",
        "university": "고려대학교",
    })
    response = client.post("/auth/login", json={
        "email": "login@korea.ac.kr",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    client.post("/auth/register", json={
        "email": "wrong@korea.ac.kr",
        "password": "password123",
        "name": "김틀림",
        "university": "고려대학교",
    })
    response = client.post("/auth/login", json={
        "email": "wrong@korea.ac.kr",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post("/auth/login", json={
        "email": "noone@korea.ac.kr",
        "password": "password123",
    })
    assert response.status_code == 401
