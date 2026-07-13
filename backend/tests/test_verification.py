import io
import os

from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.config import settings
from app.models.verification import StudentVerification


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


def test_admin_list_includes_name_and_university(admin_client: TestClient):
    admin_client.post("/auth/register", json={
        "email": "namestudent@test.com",
        "password": "password123",
        "name": "김학생",
        "university": "연세대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "namestudent@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    response = admin_client.get("/admin/verifications")
    assert response.status_code == 200
    entry = next(e for e in response.json() if e["name"] == "김학생")
    assert entry["university"] == "연세대학교"


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


def test_upload_stores_in_private_dir_not_public(client: TestClient):
    headers = _register_and_get_headers(client, "priv@test.com")
    res = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"secret-id-bytes"), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 201

    db = TestingSessionLocal()
    try:
        v = db.query(StudentVerification).order_by(StudentVerification.id.desc()).first()
        filename = v.image_url
    finally:
        db.close()

    # DB엔 파일명만 저장 (경로 구분자 없음)
    assert "/" not in filename
    assert "\\" not in filename
    # 비공개 디렉토리에 존재
    assert os.path.exists(os.path.join(settings.verification_dir, filename))
    # 공개 uploads 디렉토리엔 없음
    assert not os.path.exists(os.path.join(settings.upload_dir, filename))


def test_upload_response_has_no_image_url(client: TestClient):
    headers = _register_and_get_headers(client, "noimgurl@test.com")
    res = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 201
    assert "image_url" not in res.json()


def test_admin_can_fetch_verification_image(admin_client: TestClient):
    admin_client.post("/auth/register", json={
        "email": "imgstudent@test.com",
        "password": "password123",
        "name": "학생",
        "university": "서울대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": "imgstudent@test.com", "password": "password123"
    })
    student_token = res.json()["access_token"]
    up = admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"secret-image"), "image/jpeg")},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    vid = up.json()["id"]

    img_res = admin_client.get(f"/admin/verifications/{vid}/image")
    assert img_res.status_code == 200
    assert img_res.content == b"secret-image"


def test_non_admin_cannot_fetch_verification_image(client: TestClient):
    headers = _register_and_get_headers(client, "notadminimg@test.com")
    up = client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"img"), "image/jpeg")},
        headers=headers,
    )
    vid = up.json()["id"]
    res = client.get(f"/admin/verifications/{vid}/image", headers=headers)
    assert res.status_code == 403


def test_fetch_missing_verification_image_404(admin_client: TestClient):
    res = admin_client.get("/admin/verifications/999999/image")
    assert res.status_code == 404


def _upload_as_student(admin_client: TestClient, email: str) -> int:
    """학생 등록·업로드 후 verification id 반환."""
    admin_client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "학생",
        "university": "서울대학교",
    })
    res = admin_client.post("/auth/login", json={
        "email": email, "password": "password123"
    })
    token = res.json()["access_token"]
    up = admin_client.post(
        "/verification/upload",
        files={"file": ("id.jpg", io.BytesIO(b"secret-id"), "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    return up.json()["id"]


def _verification_filepath(verification_id: int) -> str:
    db = TestingSessionLocal()
    try:
        v = db.get(StudentVerification, verification_id)
        return os.path.join(settings.verification_dir, v.image_url)
    finally:
        db.close()


def test_approve_deletes_image_file(admin_client: TestClient):
    vid = _upload_as_student(admin_client, "approvedel@test.com")
    filepath = _verification_filepath(vid)
    assert os.path.exists(filepath)

    res = admin_client.post(f"/admin/verifications/{vid}", json={"action": "approve"})
    assert res.status_code == 200
    assert not os.path.exists(filepath)


def test_reject_deletes_image_file(admin_client: TestClient):
    vid = _upload_as_student(admin_client, "rejectdel@test.com")
    filepath = _verification_filepath(vid)
    assert os.path.exists(filepath)

    res = admin_client.post(f"/admin/verifications/{vid}", json={"action": "reject"})
    assert res.status_code == 200
    assert not os.path.exists(filepath)


def test_review_idempotent_when_image_already_gone(admin_client: TestClient):
    vid = _upload_as_student(admin_client, "idempotent@test.com")
    filepath = _verification_filepath(vid)
    os.remove(filepath)  # 파일이 이미 없는 상황 재현

    res = admin_client.post(f"/admin/verifications/{vid}", json={"action": "approve"})
    assert res.status_code == 200
