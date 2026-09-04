from fastapi.testclient import TestClient

from app.models.game import Ojakgyo
from app.models.user import User
from tests.conftest import TestingSessionLocal


def _auth(client: TestClient, email="user@test.com", name="홍길동", university="서울대학교",
          admission_year=None) -> dict:
    body = {
        "email": email, "password": "password123",
        "name": name, "university": university, "gender": "male",
        "agreed_terms": True, "agreed_privacy": True, "agreed_age_14": True,
        "kakao_id": "auth_kakao",
    }
    if admission_year is not None:
        body["admission_year"] = admission_year
    client.post("/auth/register", json=body)
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_ojakgyo_create(client: TestClient):
    headers = _auth(client)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "연세대학교",
        "person_b_name": "이영희", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert "created_at" in data
    assert {data["person_a_name"], data["person_b_name"]} == {"김철수", "이영희"}


def test_ojakgyo_empty_field(client: TestClient):
    headers = _auth(client, "empty@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_ojakgyo_unauthorized(client: TestClient):
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    })
    assert res.status_code == 401


def test_ojakgyo_self_forbidden(client: TestClient):
    headers = _auth(client, "self@test.com", "나본인", "서울대학교")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "나본인", "person_a_university": "서울대학교",
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_same_pair_forbidden(client: TestClient):
    headers = _auth(client, "same@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동일", "person_a_university": "연세대학교",
        "person_b_name": "동일", "person_b_university": "연세대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_duplicate_pair_conflict(client: TestClient):
    headers = _auth(client, "dup@test.com")
    body1 = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body1, headers=headers).status_code == 201
    body2 = {
        "person_a_name": "나", "person_a_university": "B대",
        "person_b_name": "가", "person_b_university": "A대",
    }
    assert client.post("/game/ojakgyo", json=body2, headers=headers).status_code == 409


def test_ojakgyo_different_recommender_same_pair_ok(client: TestClient):
    h1 = _auth(client, "rec1@test.com")
    h2 = _auth(client, "rec2@test.com")
    body = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body, headers=h1).status_code == 201
    assert client.post("/game/ojakgyo", json=body, headers=h2).status_code == 201


def test_red_thread_create_one(client: TestClient):
    headers = _auth(client, "rt1@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "상대", "target_university": "고려대학교"},
    ]}, headers=headers)
    assert res.status_code == 200
    targets = res.json()["targets"]
    assert len(targets) == 1
    assert targets[0]["target_name"] == "상대"


def test_red_thread_create_two(client: TestClient):
    headers = _auth(client, "rt2@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "갑", "target_university": "A대"},
        {"target_name": "을", "target_university": "B대"},
    ]}, headers=headers)
    assert res.status_code == 200
    assert len(res.json()["targets"]) == 2


def test_red_thread_too_many(client: TestClient):
    headers = _auth(client, "rt3@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "갑", "target_university": "A대"},
        {"target_name": "을", "target_university": "B대"},
        {"target_name": "병", "target_university": "C대"},
    ]}, headers=headers)
    assert res.status_code == 422


def test_red_thread_empty_list(client: TestClient):
    headers = _auth(client, "rt4@test.com")
    res = client.post("/game/red-thread", json={"targets": []}, headers=headers)
    assert res.status_code == 422


def test_red_thread_self_forbidden(client: TestClient):
    headers = _auth(client, "rtself@test.com", "본인", "서울대학교")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "본인", "target_university": "서울대학교"},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_duplicate_target_forbidden(client: TestClient):
    headers = _auth(client, "rtdup@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "같은이", "target_university": "A대"},
        {"target_name": "같은이", "target_university": "A대"},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_strip_whitespace(client: TestClient):
    headers = _auth(client, "rtstrip@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "  상대  ", "target_university": " 고려대학교 "},
    ]}, headers=headers)
    assert res.status_code == 200
    t = res.json()["targets"][0]
    assert t["target_name"] == "상대"
    assert t["target_university"] == "고려대학교"


def test_red_thread_whitespace_only_forbidden(client: TestClient):
    headers = _auth(client, "rtws@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "   ", "target_university": "A대"},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_overwrite_replaces_list(client: TestClient):
    headers = _auth(client, "rtover@test.com")
    client.post("/game/red-thread", json={"targets": [
        {"target_name": "갑", "target_university": "A대"},
        {"target_name": "을", "target_university": "B대"},
    ]}, headers=headers)
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "병", "target_university": "C대"},
    ]}, headers=headers)
    assert res.status_code == 200
    got = client.get("/game/red-thread", headers=headers)
    targets = got.json()["targets"]
    assert len(targets) == 1
    assert targets[0]["target_name"] == "병"


def test_red_thread_get_empty(client: TestClient):
    headers = _auth(client, "rtempty@test.com")
    res = client.get("/game/red-thread", headers=headers)
    assert res.status_code == 200
    assert res.json()["targets"] == []


def test_red_thread_post_unauthorized(client: TestClient):
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "x", "target_university": "y"},
    ]})
    assert res.status_code == 401


def test_red_thread_get_unauthorized(client: TestClient):
    res = client.get("/game/red-thread")
    assert res.status_code == 401


def test_red_thread_received_count(client: TestClient):
    hb = _auth(client, "target@test.com", "타깃", "성균관대학교")
    h1 = _auth(client, "p1@test.com")
    h2 = _auth(client, "p2@test.com")
    body = {"targets": [{"target_name": "타깃", "target_university": "성균관대학교"}]}
    assert client.post("/game/red-thread", json=body, headers=h1).status_code == 200
    assert client.post("/game/red-thread", json=body, headers=h2).status_code == 200
    res = client.get("/game/red-thread/received", headers=hb)
    assert res.status_code == 200
    assert res.json()["count"] == 2


def test_red_thread_received_counts_distinct_people(client: TestClient):
    hb = _auth(client, "target2@test.com", "타깃2", "성균관대학교")
    h1 = _auth(client, "q1@test.com")
    body = {"targets": [
        {"target_name": "타깃2", "target_university": "성균관대학교"},
        {"target_name": "딴사람", "target_university": "B대"},
    ]}
    client.post("/game/red-thread", json=body, headers=h1)
    res = client.get("/game/red-thread/received", headers=hb)
    assert res.json()["count"] == 1


def test_red_thread_received_zero(client: TestClient):
    headers = _auth(client, "nobody@test.com")
    res = client.get("/game/red-thread/received", headers=headers)
    assert res.status_code == 200
    assert res.json()["count"] == 0


def test_red_thread_received_unauthorized(client: TestClient):
    res = client.get("/game/red-thread/received")
    assert res.status_code == 401


def test_ojakgyo_strip_dedup(client: TestClient):
    headers = _auth(client, "ojstrip@test.com")
    body1 = {
        "person_a_name": "가", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }
    assert client.post("/game/ojakgyo", json=body1, headers=headers).status_code == 201
    # 같은 쌍을 앞뒤 공백 붙여 재지목 → strip 후 동일 → 409
    body2 = {
        "person_a_name": "  가  ", "person_a_university": " A대 ",
        "person_b_name": " 나", "person_b_university": "B대 ",
    }
    assert client.post("/game/ojakgyo", json=body2, headers=headers).status_code == 409


def test_ojakgyo_whitespace_only_field(client: TestClient):
    headers = _auth(client, "ojws@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "   ", "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_name_too_long(client: TestClient):
    headers = _auth(client, "ojlong@test.com")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "가" * 101, "person_a_university": "A대",
        "person_b_name": "나", "person_b_university": "B대",
    }, headers=headers)
    assert res.status_code == 422


def test_red_thread_name_too_long(client: TestClient):
    headers = _auth(client, "rtlong@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "상" * 101, "target_university": "A대"},
    ]}, headers=headers)
    assert res.status_code == 422


def test_ojakgyo_self_after_strip(client: TestClient):
    headers = _auth(client, "ojself@test.com", "본인", "서울대학교")
    # 본인 이름+학교를 공백 붙여 넣어도 strip 후 본인으로 판정 → 400
    res = client.post("/game/ojakgyo", json={
        "person_a_name": " 본인 ", "person_a_university": " 서울대학교 ",
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_namesake_different_year_allowed(client: TestClient):
    """이름+학교가 같아도 양쪽 다 학번이 있고 다르면 다른 사람 — 지목 성립 (설계 §6)."""
    headers = _auth(client, "namesake_rec@test.com", "지목자")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "김철수", "person_b_university": "서울대학교",
        "person_b_admission_year": 2022,
    }, headers=headers)
    assert res.status_code == 201


def test_ojakgyo_namesake_same_year_forbidden(client: TestClient):
    headers = _auth(client, "namesake_same@test.com", "지목자")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "김철수", "person_b_university": "서울대학교",
        "person_b_admission_year": 2021,
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_namesake_missing_year_forbidden(client: TestClient):
    """한쪽이라도 학번이 없으면 구분할 수 없다 — 안전한 방향인 동일인 취급 (설계 §6)."""
    headers = _auth(client, "namesake_missing@test.com", "지목자")
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "김철수", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "김철수", "person_b_university": "서울대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_self_different_year_allowed(client: TestClient):
    """본인과 이름+학교가 같아도 학번이 다르면 다른 사람 — 지목 가능 (설계 §6)."""
    headers = _auth(client, "self_diffyear@test.com", "동명이인", "서울대학교",
                     admission_year=2020)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동명이인", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 201


def test_ojakgyo_self_matching_year_forbidden(client: TestClient):
    headers = _auth(client, "self_sameyear@test.com", "동명이인2", "서울대학교",
                     admission_year=2021)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동명이인2", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_self_missing_year_forbidden(client: TestClient):
    """대상 학번이 없으면 구분할 수 없다 — 안전한 방향인 자기지목 차단 유지 (설계 §6)."""
    headers = _auth(client, "self_noyear@test.com", "동명이인3", "서울대학교",
                     admission_year=2021)
    res = client.post("/game/ojakgyo", json={
        "person_a_name": "동명이인3", "person_a_university": "서울대학교",
        "person_b_name": "남", "person_b_university": "고려대학교",
    }, headers=headers)
    assert res.status_code == 400


def test_red_thread_namesake_different_year_allowed(client: TestClient):
    """이름+학교가 같아도 양쪽 다 학번이 있고 다르면 다른 사람 — 둘 다 저장된다 (설계 §6)."""
    headers = _auth(client, "rt_namesake_diff@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "김철수", "target_university": "서울대학교", "target_admission_year": 2021},
        {"target_name": "김철수", "target_university": "서울대학교", "target_admission_year": 2022},
    ]}, headers=headers)
    assert res.status_code == 200
    assert len(res.json()["targets"]) == 2


def test_red_thread_namesake_same_year_forbidden(client: TestClient):
    headers = _auth(client, "rt_namesake_same@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "김철수", "target_university": "서울대학교", "target_admission_year": 2021},
        {"target_name": "김철수", "target_university": "서울대학교", "target_admission_year": 2021},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_namesake_missing_year_forbidden(client: TestClient):
    """한쪽이라도 학번이 없으면 구분할 수 없다 — 안전한 방향인 동일인 취급 (설계 §6)."""
    headers = _auth(client, "rt_namesake_missing@test.com")
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "김철수", "target_university": "서울대학교", "target_admission_year": 2021},
        {"target_name": "김철수", "target_university": "서울대학교"},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_self_different_year_allowed(client: TestClient):
    """본인과 이름+학교가 같아도 학번이 다르면 다른 사람 — 지목 가능 (설계 §6)."""
    headers = _auth(client, "rt_self_diffyear@test.com", "동명이인", "서울대학교",
                     admission_year=2020)
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "동명이인", "target_university": "서울대학교", "target_admission_year": 2021},
    ]}, headers=headers)
    assert res.status_code == 200


def test_red_thread_self_matching_year_forbidden(client: TestClient):
    headers = _auth(client, "rt_self_sameyear@test.com", "동명이인2", "서울대학교",
                     admission_year=2021)
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "동명이인2", "target_university": "서울대학교", "target_admission_year": 2021},
    ]}, headers=headers)
    assert res.status_code == 400


def test_red_thread_self_missing_year_forbidden(client: TestClient):
    """대상 학번이 없으면 구분할 수 없다 — 안전한 방향인 자기지목 차단 유지 (설계 §6)."""
    headers = _auth(client, "rt_self_noyear@test.com", "동명이인3", "서울대학교",
                     admission_year=2021)
    res = client.post("/game/red-thread", json={"targets": [
        {"target_name": "동명이인3", "target_university": "서울대학교"},
    ]}, headers=headers)
    assert res.status_code == 400


def test_ojakgyo_namesake_reversed_order_conflict(client: TestClient):
    """정규화가 학번까지 비교해야 한다 (설계 §6 리뷰 지적).

    (name, university)만으로 정렬하면 학번만 다른 동명이인 쌍은 제출 순서를 그대로
    유지해 (A, B)와 (B, A)가 서로 다른 정규화 결과로 남고, 같은 지목이 두 번 저장된다.
    """
    headers = _auth(client, "namesake_reorder@test.com", "지목자")
    body1 = {
        "person_a_name": "김철수", "person_a_university": "서울대학교",
        "person_a_admission_year": 2021,
        "person_b_name": "김철수", "person_b_university": "서울대학교",
        "person_b_admission_year": 2022,
    }
    assert client.post("/game/ojakgyo", json=body1, headers=headers).status_code == 201

    # 같은 두 사람, person_a/person_b 순서만 뒤집어 재지목
    body2 = {
        "person_a_name": "김철수", "person_a_university": "서울대학교",
        "person_a_admission_year": 2022,
        "person_b_name": "김철수", "person_b_university": "서울대학교",
        "person_b_admission_year": 2021,
    }
    res = client.post("/game/ojakgyo", json=body2, headers=headers)
    assert res.status_code == 409

    db = TestingSessionLocal()
    recommender = db.query(User).filter(User.email == "namesake_reorder@test.com").first()
    count = db.query(Ojakgyo).filter(Ojakgyo.recommender_id == recommender.id).count()
    db.close()
    assert count == 1
