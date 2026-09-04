from fastapi.testclient import TestClient

SNU = "서울대학교"
YONSEI = "연세대학교"

URL = "/admin/university-weights"


def _create(client: TestClient, **kwargs):
    payload = {"university_a": SNU, "university_b": "", "bonus": 30,
               "active": True, "note": None}
    payload.update(kwargs)
    return client.post(URL, json=payload)


def test_create_single_rule(admin_client: TestClient):
    res = _create(admin_client)
    assert res.status_code == 201
    data = res.json()
    assert data["university_a"] == SNU
    assert data["university_b"] == ""
    assert data["bonus"] == 30
    assert data["active"] is True


def test_pair_is_stored_in_sorted_order(admin_client: TestClient):
    """사전순 정규화 — 순서만 바꾼 중복을 유니크가 잡게 한다 (설계 §4.2)."""
    res = _create(admin_client, university_a=YONSEI, university_b=SNU)
    assert res.status_code == 201
    data = res.json()
    assert (data["university_a"], data["university_b"]) == tuple(sorted([SNU, YONSEI]))


def test_duplicate_single_rule_is_conflict(admin_client: TestClient):
    _create(admin_client)
    assert _create(admin_client).status_code == 409


def test_duplicate_pair_in_swapped_order_is_conflict(admin_client: TestClient):
    _create(admin_client, university_a=SNU, university_b=YONSEI)
    res = _create(admin_client, university_a=YONSEI, university_b=SNU)
    assert res.status_code == 409


def test_blank_university_a_is_rejected(admin_client: TestClient):
    assert _create(admin_client, university_a="   ").status_code == 400


def test_same_university_pair_is_rejected(admin_client: TestClient):
    """(A, A)는 단일 규칙과 겹치는 문서에 없는 경로다 — 대학 B를 비워야 한다."""
    res = _create(admin_client, university_a=SNU, university_b=SNU)
    assert res.status_code == 400


def test_negative_bonus_is_allowed(admin_client: TestClient):
    assert _create(admin_client, bonus=-20).json()["bonus"] == -20


def test_list_returns_all_rules(admin_client: TestClient):
    _create(admin_client)
    _create(admin_client, university_a=YONSEI)
    res = admin_client.get(URL)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_includes_inactive_rules(admin_client: TestClient):
    """끈 규칙도 관리자에겐 보여야 다시 켤 수 있다."""
    _create(admin_client, active=False)
    assert len(admin_client.get(URL).json()) == 1


def test_update_toggles_active(admin_client: TestClient):
    weight_id = _create(admin_client).json()["id"]
    res = admin_client.put(f"{URL}/{weight_id}", json={
        "university_a": SNU, "university_b": "", "bonus": 30,
        "active": False, "note": "이벤트 종료",
    })
    assert res.status_code == 200
    assert res.json()["active"] is False
    assert res.json()["note"] == "이벤트 종료"


def test_update_into_duplicate_is_conflict(admin_client: TestClient):
    _create(admin_client)
    other_id = _create(admin_client, university_a=YONSEI).json()["id"]
    res = admin_client.put(f"{URL}/{other_id}", json={
        "university_a": SNU, "university_b": "", "bonus": 5,
        "active": True, "note": None,
    })
    assert res.status_code == 409


def test_update_missing_is_404(admin_client: TestClient):
    res = admin_client.put(f"{URL}/999", json={
        "university_a": SNU, "university_b": "", "bonus": 5,
        "active": True, "note": None,
    })
    assert res.status_code == 404


def test_delete_removes_rule(admin_client: TestClient):
    weight_id = _create(admin_client).json()["id"]
    assert admin_client.delete(f"{URL}/{weight_id}").status_code == 204
    assert admin_client.get(URL).json() == []


def test_delete_missing_is_404(admin_client: TestClient):
    assert admin_client.delete(f"{URL}/999").status_code == 404


def test_non_admin_is_forbidden(client: TestClient):
    client.post("/auth/register", json={
        "email": "plain@test.com", "password": "password123", "name": "김일반",
        "university": SNU, "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
        "kakao_id": "plain_kakao",
    })
    token = client.post("/auth/login", json={
        "email": "plain@test.com", "password": "password123",
    }).json()["access_token"]
    res = client.get(URL, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
