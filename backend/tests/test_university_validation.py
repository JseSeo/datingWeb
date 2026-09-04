from fastapi.testclient import TestClient

UNLISTED = "없는대학교"


def _register(client: TestClient, university: str, email: str = "v@test.com"):
    return client.post("/auth/register", json={
        "email": email, "password": "password123", "name": "검증",
        "university": university, "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
        "kakao_id": "verify_kakao",
    })


def _auth(client: TestClient, email: str) -> dict:
    _register(client, "서울대학교", email)
    token = client.post("/auth/login", json={
        "email": email, "password": "password123",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_rejects_unlisted_university(client: TestClient):
    res = _register(client, UNLISTED)
    assert res.status_code == 422


def test_register_accepts_listed_university(client: TestClient):
    assert _register(client, "서울대학교").status_code == 201


def test_register_rejects_inactive_university(client: TestClient, admin_client: TestClient):
    """끈 대학으로는 새로 가입할 수 없다 (설계 §5.3)."""
    listed = admin_client.get("/admin/universities").json()
    korea = next(u for u in listed if u["name"] == "고려대학교")
    patch_res = admin_client.patch(f"/admin/universities/{korea['id']}", json={"active": False})
    assert patch_res.status_code == 200
    assert _register(client, "고려대학교", "inactive@test.com").status_code == 422


def test_ojakgyo_rejects_unlisted_university(client: TestClient):
    headers = _auth(client, "oj@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가", "person_a_university": UNLISTED,
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_red_thread_rejects_unlisted_university(client: TestClient):
    headers = _auth(client, "rt@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "갑", "target_university": UNLISTED},
    ]}, headers=headers)
    assert res.status_code == 422


def test_weight_rejects_unlisted_university(admin_client: TestClient):
    res = admin_client.post("/admin/university-weights", json={
        "university_a": UNLISTED, "university_b": "", "bonus": 10,
        "active": True, "note": None,
    })
    assert res.status_code == 422


def test_weight_single_rule_keeps_empty_university_b(admin_client: TestClient):
    """빈 university_b는 단일 대학 규칙 관례라 검증을 건너뛴다 (설계 §5.2)."""
    res = admin_client.post("/admin/university-weights", json={
        "university_a": "서울대학교", "university_b": "", "bonus": 10,
        "active": True, "note": None,
    })
    assert res.status_code == 201


def test_weight_rejects_unlisted_university_b(admin_client: TestClient):
    """university_a뿐 아니라 university_b도 검증돼야 한다."""
    res = admin_client.post("/admin/university-weights", json={
        "university_a": "서울대학교", "university_b": UNLISTED, "bonus": 10,
        "active": True, "note": None,
    })
    assert res.status_code == 422


def test_register_rejects_year_below_range(client: TestClient):
    res = client.post("/auth/register", json={
        "email": "y1@test.com", "password": "password123", "name": "학번",
        "university": "서울대학교", "gender": "male", "kakao_id": "k",
        "admission_year": 1999,
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    assert res.status_code == 422


def test_register_accepts_next_year(client: TestClient):
    """입학 전 학기 가입을 허용한다 (설계 §4.2)."""
    from datetime import datetime
    res = client.post("/auth/register", json={
        "email": "y2@test.com", "password": "password123", "name": "학번",
        "university": "서울대학교", "gender": "male", "kakao_id": "k",
        "admission_year": datetime.utcnow().year + 1,
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
    })
    assert res.status_code == 201


def test_weight_update_rejects_unlisted_university(admin_client: TestClient):
    created = admin_client.post("/admin/university-weights", json={
        "university_a": "서울대학교", "university_b": "", "bonus": 10,
        "active": True, "note": None,
    }).json()
    res = admin_client.put(f"/admin/university-weights/{created['id']}", json={
        "university_a": UNLISTED, "university_b": "", "bonus": 20,
        "active": True, "note": None,
    })
    assert res.status_code == 422

    listed = admin_client.get("/admin/university-weights").json()
    unchanged = next(w for w in listed if w["id"] == created["id"])
    assert unchanged["university_a"] == "서울대학교"
    assert unchanged["university_b"] == ""
