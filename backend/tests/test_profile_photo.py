import io
from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str) -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "테스터",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_upload_profile_photo(client: TestClient):
    headers = _register_and_get_headers(client, "photo@test.com")
    response = client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile_photo"] is not None
    assert data["profile_photo"].startswith("/uploads/")


def test_upload_profile_photo_wrong_type(client: TestClient):
    headers = _register_and_get_headers(client, "photowrong@test.com")
    response = client.post(
        "/me/profile-photo",
        files={"file": ("doc.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_profile_photo_too_large(client: TestClient):
    headers = _register_and_get_headers(client, "photobig@test.com")
    big = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    response = client.post(
        "/me/profile-photo",
        files={"file": ("big.jpg", big, "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_profile_photo_unauthenticated(client: TestClient):
    response = client.post(
        "/me/profile-photo",
        files={"file": ("me.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert response.status_code == 401
