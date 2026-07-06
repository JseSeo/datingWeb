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


def test_upload_student_id(client: TestClient):
    headers = _register_and_get_headers(client, "upload@test.com")
    response = client.post(
        "/verification/upload",
        files={"file": ("student_id.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["user_id"] is not None


def test_upload_wrong_file_type(client: TestClient):
    headers = _register_and_get_headers(client, "wrong@test.com")
    response = client.post(
        "/verification/upload",
        files={"file": ("file.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 400


def test_upload_unauthenticated(client: TestClient):
    response = client.post(
        "/verification/upload",
        files={"file": ("student_id.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert response.status_code == 401


def test_admin_list_verifications(admin_client: TestClient):
    # 일반 유저 등록 + 학생증 업로드
    admin_client.post("/auth/register", json={
        "email": "student@test.com",
        "password": "password123",
        "name": "학생",
        "university": "서울대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "student@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    # 관리자로 목록 조회
    response = admin_client.get("/admin/verifications")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["status"] == "pending"


def test_admin_approve_verification(admin_client: TestClient):
    admin_client.post("/auth/register", json={
        "email": "approve@test.com",
        "password": "password123",
        "name": "승인대기",
        "university": "서울대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "approve@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    upload_res = admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    verification_id = upload_res.json()["id"]

    response = admin_client.post(
        f"/admin/verifications/{verification_id}",
        json={"action": "approve"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    # 유저 status가 active로 변경됐는지 확인
    me_res = admin_client.get(
        "/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert me_res.json()["status"] == "active"


def test_non_admin_cannot_list_verifications(client: TestClient):
    headers = _register_and_get_headers(client, "notadmin@test.com")
    response = client.get("/admin/verifications", headers=headers)
    assert response.status_code == 403


def test_get_my_verification_none(client):
    headers = _register_and_get_headers(client, "noverif@test.com")
    res = client.get("/me/verification", headers=headers)
    assert res.status_code == 200
    assert res.json() is None


def test_get_my_verification_after_upload(client):
    headers = _register_and_get_headers(client, "hasverif@test.com")
    client.post(
        "/verification/upload",
        files={"file": ("s.jpg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    )
    res = client.get("/me/verification", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_get_my_verification_unauthenticated(client):
    res = client.get("/me/verification")
    assert res.status_code == 401
