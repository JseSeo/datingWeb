from fastapi.testclient import TestClient

from tests.conftest import TestingSessionLocal
from app.models.university import University


def _seed(name: str, active: bool = True):
    db = TestingSessionLocal()
    db.add(University(name=name, active=active))
    db.commit()
    db.close()


def test_public_list_needs_no_auth(client: TestClient):
    """가입 폼이 로그인 전에 호출한다 (설계 §8)."""
    _seed("한양대학교")
    res = client.get("/universities")
    assert res.status_code == 200
    assert "한양대학교" in [u["name"] for u in res.json()]


def test_public_list_hides_inactive(client: TestClient):
    _seed("꺼진대학교", active=False)
    res = client.get("/universities")
    assert "꺼진대학교" not in [u["name"] for u in res.json()]


def test_public_list_is_sorted_by_name(client: TestClient):
    names = [u["name"] for u in client.get("/universities").json()]
    assert names == sorted(names)
