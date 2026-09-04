from fastapi.testclient import TestClient


def _reporter_headers(
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
        "kakao_id": "reporter_kakao",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _make_report(client: TestClient, headers: dict, reason: str = "부적절한 사진") -> int:
    res = client.post("/reports", json={
        "type": "report",
        "target_name": "대상자",
        "target_university": "연세대학교",
        "reason": reason,
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def _make_suggestion(client: TestClient, headers: dict) -> int:
    res = client.post("/reports", json={
        "type": "suggestion",
        "target_name": None,
        "target_university": None,
        "reason": "알림 끄는 기능 주세요",
    }, headers=headers)
    assert res.status_code == 201
    return res.json()["id"]


def test_list_excludes_handled_by_default(admin_client: TestClient):
    headers = _reporter_headers(admin_client)
    handled_id = _make_report(admin_client, headers, "처리될 신고")
    _make_report(admin_client, headers, "남아있을 신고")
    admin_client.post(f"/admin/reports/{handled_id}/handle")

    res = admin_client.get("/admin/reports")
    assert res.status_code == 200
    reasons = [r["reason"] for r in res.json()]
    assert "남아있을 신고" in reasons
    assert "처리될 신고" not in reasons


def test_list_include_handled(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r2@test.com")
    handled_id = _make_report(admin_client, headers, "처리될 신고")
    admin_client.post(f"/admin/reports/{handled_id}/handle")

    res = admin_client.get("/admin/reports?include_handled=true")
    assert res.status_code == 200
    reasons = [r["reason"] for r in res.json()]
    assert "처리될 신고" in reasons


def test_list_sorted_newest_first(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r3@test.com")
    _make_report(admin_client, headers, "먼저 쓴 신고")
    _make_report(admin_client, headers, "나중 쓴 신고")

    data = admin_client.get("/admin/reports").json()
    ids = [r["id"] for r in data]
    assert ids == sorted(ids, reverse=True)


def test_list_includes_reporter_and_hides_id(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r4@test.com", "김철수", "고려대학교")
    _make_report(admin_client, headers)

    item = admin_client.get("/admin/reports").json()[0]
    assert item["reporter_name"] == "김철수"
    assert item["reporter_university"] == "고려대학교"
    assert "reporter_id" not in item


def test_list_suggestion_has_null_target(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r5@test.com")
    _make_suggestion(admin_client, headers)

    item = admin_client.get("/admin/reports").json()[0]
    assert item["type"] == "suggestion"
    assert item["target_name"] is None
    assert item["target_university"] is None


def test_handle_marks_handled(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r6@test.com")
    report_id = _make_report(admin_client, headers)

    res = admin_client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 200
    assert res.json()["handled"] is True


def test_handle_is_idempotent(admin_client: TestClient):
    headers = _reporter_headers(admin_client, "r7@test.com")
    report_id = _make_report(admin_client, headers)

    admin_client.post(f"/admin/reports/{report_id}/handle")
    res = admin_client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 200
    assert res.json()["handled"] is True


def test_handle_missing_report(admin_client: TestClient):
    res = admin_client.post("/admin/reports/99999/handle")
    assert res.status_code == 404
    assert res.json()["detail"] == "존재하지 않는 신고입니다"


def test_list_forbidden_for_normal_user(client: TestClient):
    headers = _reporter_headers(client, "normal@test.com")
    res = client.get("/admin/reports", headers=headers)
    assert res.status_code == 403


def test_list_unauthorized(client: TestClient):
    res = client.get("/admin/reports")
    assert res.status_code == 401


def test_handle_forbidden_for_normal_user(client: TestClient):
    headers = _reporter_headers(client, "normal2@test.com")
    report_id = _make_report(client, headers)
    res = client.post(f"/admin/reports/{report_id}/handle", headers=headers)
    assert res.status_code == 403


def test_handle_unauthorized(client: TestClient):
    headers = _reporter_headers(client, "normal3@test.com")
    report_id = _make_report(client, headers)
    res = client.post(f"/admin/reports/{report_id}/handle")
    assert res.status_code == 401
