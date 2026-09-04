from fastapi.testclient import TestClient

from app.models.game import Ojakgyo, RedThread
from app.models.match import MatchingUniversityWeight
from app.models.user import User
from tests.conftest import TestingSessionLocal

URL = "/admin/universities"


def _admin_id(db) -> int:
    return db.query(User).filter(User.email == "admin@datedrop.kr").first().id


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


def test_delete_referenced_by_ojakgyo_is_conflict(admin_client: TestClient):
    """스펙 §12: 4개 참조 지점 전부 delete 409 가드 대상이다 — 오작교 쪽."""
    listed = admin_client.get(URL).json()
    yonsei = next(u for u in listed if u["name"] == "연세대학교")

    db = TestingSessionLocal()
    db.add(Ojakgyo(
        recommender_id=_admin_id(db),
        person_a_name="가", person_a_university="연세대학교",
        person_b_name="나", person_b_university="B대",
    ))
    db.commit()
    db.close()

    res = admin_client.delete(f"{URL}/{yonsei['id']}")
    assert res.status_code == 409


def test_delete_referenced_by_red_thread_is_conflict(admin_client: TestClient):
    """스펙 §12: 4개 참조 지점 전부 delete 409 가드 대상이다 — 붉은 실 쪽."""
    listed = admin_client.get(URL).json()
    korea = next(u for u in listed if u["name"] == "고려대학교")

    db = TestingSessionLocal()
    db.add(RedThread(
        user_id=_admin_id(db), target_name="다", target_university="고려대학교",
    ))
    db.commit()
    db.close()

    res = admin_client.delete(f"{URL}/{korea['id']}")
    assert res.status_code == 409


def test_delete_referenced_by_university_weight_is_conflict(admin_client: TestClient):
    """스펙 §12: 4개 참조 지점 전부 delete 409 가드 대상이다 — 대학 가중치 쪽."""
    listed = admin_client.get(URL).json()
    sungkyunkwan = next(u for u in listed if u["name"] == "성균관대학교")

    db = TestingSessionLocal()
    db.add(MatchingUniversityWeight(
        university_a="성균관대학교", university_b="", bonus=10,
    ))
    db.commit()
    db.close()

    res = admin_client.delete(f"{URL}/{sungkyunkwan['id']}")
    assert res.status_code == 409


def test_delete_missing_is_404(admin_client: TestClient):
    assert admin_client.delete(f"{URL}/99999").status_code == 404


def test_requires_admin(client: TestClient):
    assert client.get(URL).status_code in (401, 403)
