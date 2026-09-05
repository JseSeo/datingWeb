"""setup_db teardown이 누수된 세션을 정리하는지 확인한다.

테스트가 `db = TestingSessionLocal()`로 세션을 열고 마지막 줄에서 `db.close()`
하는 패턴은 이 저장소 전반에 87곳 있다. assert가 실패하면 close()에 도달하지
못해 열린 트랜잭션이 남고, 그게 drop_all을 막는다. 테이블이 살아남은 채 다음
테스트가 BASELINE_UNIVERSITIES를 다시 넣어 UNIQUE constraint failed로 터지며,
원인과 아무 상관 없는 테스트가 ERROR로 뜬다.

87곳을 고치는 대신 teardown 한 곳에서 끊는다. 이 파일은 그 방어가 살아 있는지
지킨다 — conftest의 close_all_sessions()를 지우면 아래 두 테스트가 깨진다.
"""
from app.models.university import University
from tests.conftest import TestingSessionLocal


def test_leaked_write_transaction_does_not_break_teardown():
    """커밋도 close도 하지 않은 채 세션을 버린다 (assert 실패 시의 실제 상태)."""
    db = TestingSessionLocal()
    db.add(University(name="누수대"))
    db.flush()  # 쓰기 락을 잡는다. 일부러 close()하지 않는다


def test_next_test_gets_a_clean_seed():
    """앞 테스트의 누수에도 시드가 한 번만 들어가야 한다."""
    db = TestingSessionLocal()
    try:
        names = [u.name for u in db.query(University).all()]
    finally:
        db.close()

    assert "누수대" not in names, "누수된 트랜잭션이 커밋됐다"
    assert len(names) == len(set(names)), f"시드가 중복 삽입됐다: {names}"
