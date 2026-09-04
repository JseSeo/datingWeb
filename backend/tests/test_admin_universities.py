from fastapi.testclient import TestClient

URL = "/admin/universities"


def test_create(admin_client: TestClient):
    res = admin_client.post(URL, json={"name": "한양대학교"})
    assert res.status_code == 201
    assert res.json()["name"] == "한양대학교"
    assert res.json()["active"] is True


def test_create_trims_whitespace(admin_client: TestClient):
    res = admin_client.post(URL, json={"name": "  중앙대학교  "})
    assert res.status_code == 201
    assert res.json()["name"] == "중앙대학교"


def test_duplicate_name_is_conflict(admin_client: TestClient):
    admin_client.post(URL, json={"name": "한양대학교"})
    assert admin_client.post(URL, json={"name": "한양대학교"}).status_code == 409


def test_admin_list_includes_inactive(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    admin_client.patch(f"{URL}/{created['id']}", json={"active": False})
    names = [u["name"] for u in admin_client.get(URL).json()]
    assert "한양대학교" in names


def test_toggle_active(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    res = admin_client.patch(f"{URL}/{created['id']}", json={"active": False})
    assert res.status_code == 200
    assert res.json()["active"] is False


def test_delete_unreferenced(admin_client: TestClient):
    created = admin_client.post(URL, json={"name": "한양대학교"}).json()
    assert admin_client.delete(f"{URL}/{created['id']}").status_code == 204


def test_delete_referenced_by_user_is_conflict(admin_client: TestClient):
    """admin_client 자신이 서울대학교로 가입돼 있다 (conftest 시드)."""
    listed = admin_client.get(URL).json()
    snu = next(u for u in listed if u["name"] == "서울대학교")
    res = admin_client.delete(f"{URL}/{snu['id']}")
    assert res.status_code == 409


def test_delete_missing_is_404(admin_client: TestClient):
    assert admin_client.delete(f"{URL}/99999").status_code == 404


def test_requires_admin(client: TestClient):
    assert client.get(URL).status_code in (401, 403)
