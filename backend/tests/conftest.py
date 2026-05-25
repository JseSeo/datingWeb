import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(client: TestClient):
    """관리자 계정으로 로그인된 클라이언트."""
    client.post("/auth/register", json={
        "email": "admin@datedrop.kr",
        "password": "adminpass123",
        "name": "관리자",
        "university": "서울대학교",
    })
    db = TestingSessionLocal()
    from app.models.user import User
    user = db.query(User).filter(User.email == "admin@datedrop.kr").first()
    user.is_admin = True
    db.commit()
    db.close()

    res = client.post("/auth/login", json={
        "email": "admin@datedrop.kr",
        "password": "adminpass123",
    })
    token = res.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
