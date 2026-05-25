# DateDrop Korea — Plan 1: Backend Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** git repo initialized, FastAPI backend running with auth (register/login/JWT), student ID upload, `/me`, and admin verification endpoints — all covered by passing pytest tests.

**Architecture:** Monorepo root `C:\workSpace\datingWeb`. Backend in `backend/`. FastAPI + SQLAlchemy 2.0 (sync) + Alembic. JWT via python-jose. Student ID images stored locally in dev (S3-ready interface). PostgreSQL in prod, SQLite in tests.

**Tech Stack:** Python 3.11+, FastAPI 0.115+, SQLAlchemy 2.0, Alembic, psycopg2-binary, python-jose[cryptography], passlib[bcrypt], python-multipart, pydantic-settings, email-validator, pytest, httpx

---

## File Map

```
C:\workSpace\datingWeb\
├── .gitignore
├── README.md
├── CLAUDE.md
├── frontend/                          (empty placeholder, Plan 2)
├── docs/superpowers/plans/
│   └── 2026-05-25-backend-foundation.md   (this file)
└── backend/
    ├── pyproject.toml
    ├── alembic.ini
    ├── .env.example
    ├── CLAUDE.md
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                    FastAPI app factory + CORS
    │   ├── config.py                  pydantic-settings env loader
    │   ├── database.py                SQLAlchemy engine + session + Base
    │   ├── models/
    │   │   ├── __init__.py            re-exports all models
    │   │   ├── user.py                User, UserStatus enum
    │   │   ├── verification.py        StudentVerification, VerificationStatus
    │   │   ├── survey.py              Survey (JSONB answers)
    │   │   ├── match.py               Match, MatchRound, RoundStatus
    │   │   ├── game.py                Ojakgyo, RedThread
    │   │   └── report.py              Report
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   ├── auth.py                RegisterRequest, LoginRequest, TokenResponse
    │   │   ├── user.py                UserOut, ProfileUpdate, MatchingPauseUpdate
    │   │   └── verification.py        VerificationOut, VerificationAction
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── router.py              includes all sub-routers
    │   │   ├── auth.py                POST /auth/register, /auth/login
    │   │   ├── me.py                  GET/PUT /me, /me/profile, /me/matching-pause
    │   │   └── verification.py        POST /verification/upload, GET/POST /admin/verifications
    │   └── core/
    │       ├── __init__.py
    │       ├── security.py            hash_password, verify_password, create_token, decode_token
    │       └── deps.py                get_current_user, get_active_user, require_admin
    └── tests/
        ├── __init__.py
        ├── conftest.py                TestClient, SQLite override, fixtures
        ├── test_main.py
        ├── test_security.py
        ├── test_auth.py
        ├── test_me.py
        └── test_verification.py
```

---

### Task 1: Initialize Repository

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `CLAUDE.md`
- Create: `frontend/` (empty dir placeholder)

- [ ] **Step 1: Initialize git**

```powershell
cd C:\workSpace\datingWeb
git init
git branch -M main
```

- [ ] **Step 2: Create `.gitignore`**

Create `C:\workSpace\datingWeb\.gitignore`:
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
build/

# Env
.env
.env.local

# Node
node_modules/
frontend/dist/
frontend/.vite/

# Uploads (local dev)
backend/uploads/

# Test DB
backend/test.db

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/settings.json
.idea/

# Pytest / coverage
.pytest_cache/
htmlcov/
.coverage
```

- [ ] **Step 3: Create `README.md`**

Create `C:\workSpace\datingWeb\README.md`:
```markdown
# DateDrop Korea

한국 대학생 대상 주간 소개팅 매칭 웹서비스.

## 구조
- `frontend/` — React (Vite), Vercel 배포
- `backend/` — Python FastAPI, Railway 배포
- `docs/` — 설계 문서, 구현 계획

## 로컬 개발

### 백엔드
```bash
cd backend
uv sync
cp .env.example .env   # DB URL 등 설정 후 편집
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

## 테스트
```bash
cd backend
uv run pytest -v
```
```

- [ ] **Step 4: Create root `CLAUDE.md`**

Create `C:\workSpace\datingWeb\CLAUDE.md`:
```markdown
# DateDrop Korea

한국 대학생 소개팅 매칭 서비스.

## 디렉토리
- `frontend/` — React (Vite)
- `backend/` — Python FastAPI
- `docs/superpowers/specs/` — 설계 문서
- `docs/superpowers/plans/` — 구현 계획

## 규칙
- 각 디렉토리의 CLAUDE.md 함께 읽을 것
- 설계 원본: `docs/superpowers/specs/2026-05-23-datedrop-korea-design.md`
- YAGNI: 설계 문서에 없는 기능 추가 금지
```

- [ ] **Step 5: Create frontend placeholder**

```powershell
New-Item -ItemType Directory -Path frontend -Force
New-Item -ItemType File -Path frontend\.gitkeep
```

- [ ] **Step 6: Commit**

```powershell
git add .
git commit -m "chore: initialize repository"
```

---

### Task 2: Backend Python Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/CLAUDE.md`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing health check test**

Create `backend/tests/test_main.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
cd backend
uv run pytest tests/test_main.py -v
```
Expected: `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Create `pyproject.toml`**

Create `backend/pyproject.toml`:
```toml
[project]
name = "datedrop-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "psycopg2-binary>=2.9",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "python-multipart>=0.0.12",
    "pydantic-settings>=2.6",
    "email-validator>=2.2",
    "python-dotenv>=1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: Install dependencies**

```powershell
uv sync
```

- [ ] **Step 5: Create `.env.example`**

Create `backend/.env.example`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/datedrop
SECRET_KEY=changethis-use-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
UPLOAD_DIR=uploads
```

- [ ] **Step 6: Create `.env`**

```powershell
Copy-Item .env.example .env
```

Edit `backend/.env`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/datedrop
SECRET_KEY=dev-secret-key-do-not-use-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
UPLOAD_DIR=uploads
```

- [ ] **Step 7: Create `app/config.py`**

Create `backend/app/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7일
    upload_dir: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

- [ ] **Step 8: Create `app/database.py`**

Create `backend/app/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 9: Create `app/__init__.py`** (empty file)

Create `backend/app/__init__.py`:
```python
```

- [ ] **Step 10: Create `app/main.py`**

Create `backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DateDrop Korea API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 11: Create `tests/__init__.py`** (empty file)

Create `backend/tests/__init__.py`:
```python
```

- [ ] **Step 12: Create `tests/conftest.py`**

Create `backend/tests/conftest.py`:
```python
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
    # 테스트 DB에서 직접 admin 플래그 설정
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
```

- [ ] **Step 13: Run test to verify it passes**

```powershell
uv run pytest tests/test_main.py -v
```
Expected:
```
PASSED tests/test_main.py::test_health_check
1 passed
```

- [ ] **Step 14: Create `backend/CLAUDE.md`**

Create `backend/CLAUDE.md`:
```markdown
# Backend — DateDrop Korea

FastAPI + SQLAlchemy 2.0 + PostgreSQL.

## 명령
- 서버: `uv run uvicorn app.main:app --reload`
- 테스트: `uv run pytest -v`
- 마이그레이션 생성: `uv run alembic revision --autogenerate -m "설명"`
- 마이그레이션 적용: `uv run alembic upgrade head`

## 규칙
- 엔드포인트마다 Pydantic 스키마 사용 (dict 반환 금지)
- DB 접근: `get_db` 의존성 주입 사용
- 인증: `get_current_user` / `get_active_user` / `require_admin` (app.core.deps)
- 비밀번호: 반드시 `hash_password` (app.core.security) 사용, 평문 저장 절대 금지
- 모델 추가 시 `app/models/__init__.py` re-export 목록 업데이트
```

- [ ] **Step 15: Commit**

```powershell
cd ..
git add backend/
git commit -m "chore(backend): FastAPI boilerplate + health check test"
```

---

### Task 3: Database Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/verification.py`
- Create: `backend/app/models/survey.py`
- Create: `backend/app/models/match.py`
- Create: `backend/app/models/game.py`
- Create: `backend/app/models/report.py`

(Models exercised via API tests — no separate model unit tests needed.)

- [ ] **Step 1: Create `models/user.py`**

Create `backend/app/models/user.py`:
```python
import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    university: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.pending, nullable=False
    )
    profile_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kakao_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    matching_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    verification: Mapped["StudentVerification | None"] = relationship(
        "StudentVerification", foreign_keys="StudentVerification.user_id",
        back_populates="user", uselist=False
    )
    survey: Mapped["Survey | None"] = relationship(
        "Survey", back_populates="user", uselist=False
    )
```

- [ ] **Step 2: Create `models/verification.py`**

Create `backend/app/models/verification.py`:
```python
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class StudentVerification(Base):
    __tablename__ = "student_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        default=VerificationStatus.pending,
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="verification"
    )
```

- [ ] **Step 3: Create `models/survey.py`**

Create `backend/app/models/survey.py`:
```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    answers: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="survey")
```

- [ ] **Step 4: Create `models/match.py`**

Create `backend/app/models/match.py`:
```python
import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RoundStatus(str, enum.Enum):
    pending = "pending"
    done = "done"


class MatchRound(Base):
    __tablename__ = "match_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[RoundStatus] = mapped_column(
        Enum(RoundStatus, name="round_status"), default=RoundStatus.pending, nullable=False
    )

    matches: Mapped[list["Match"]] = relationship("Match", back_populates="round")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_a_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    match_round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("match_rounds.id"), nullable=False
    )
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    round: Mapped["MatchRound"] = relationship("MatchRound", back_populates="matches")
```

- [ ] **Step 5: Create `models/game.py`**

Create `backend/app/models/game.py`:
```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ojakgyo(Base):
    """오작교: referrer 추천 → referee 가입 시 referrer 매칭 확률 +33%"""
    __tablename__ = "ojakgyo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    referrer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    referee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    invite_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class RedThread(Base):
    """붉은 실: 양쪽이 서로 이름+학교 입력 시 100% 매칭"""
    __tablename__ = "red_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_university: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 6: Create `models/report.py`**

Create `backend/app/models/report.py`:
```python
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
```

- [ ] **Step 7: Create `models/__init__.py`**

Create `backend/app/models/__init__.py`:
```python
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification, VerificationStatus
from app.models.survey import Survey
from app.models.match import Match, MatchRound, RoundStatus
from app.models.game import Ojakgyo, RedThread
from app.models.report import Report

__all__ = [
    "User", "UserStatus",
    "StudentVerification", "VerificationStatus",
    "Survey",
    "Match", "MatchRound", "RoundStatus",
    "Ojakgyo", "RedThread",
    "Report",
]
```

- [ ] **Step 8: Import models in `main.py`**

Replace `backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registers all models with Base.metadata

app = FastAPI(title="DateDrop Korea API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 9: Run test to verify nothing broke**

```powershell
uv run pytest tests/test_main.py -v
```
Expected: `1 passed`

- [ ] **Step 10: Commit**

```powershell
cd ..
git add backend/app/models/ backend/app/main.py
git commit -m "feat(backend): add SQLAlchemy models (User, Verification, Survey, Match, Game, Report)"
```

---

### Task 4: Alembic Setup

**Files:**
- Create: `backend/alembic/` (via `alembic init`)
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Initialize Alembic**

```powershell
cd backend
uv run alembic init alembic
```
Creates `alembic/` and `alembic.ini`.

- [ ] **Step 2: Update `alembic/env.py`**

Replace entire `backend/alembic/env.py`:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
import app.models  # noqa: F401 — registers all models
from app.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Generate initial migration (PostgreSQL 필요)**

PostgreSQL 로컬 실행 중일 때:
```powershell
uv run alembic revision --autogenerate -m "initial schema"
```
Expected: `backend/alembic/versions/XXXX_initial_schema.py` 생성됨.

PostgreSQL 없으면 Railway 배포 후 실행.

- [ ] **Step 4: Apply migration (PostgreSQL 필요)**

```powershell
uv run alembic upgrade head
```

- [ ] **Step 5: Commit**

```powershell
cd ..
git add backend/alembic/ backend/alembic.ini
git commit -m "chore(backend): add Alembic migrations setup"
```

---

### Task 5: Security Utilities

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_security.py`:
```python
from app.core.security import hash_password, verify_password, create_token, decode_token


def test_hash_and_verify_password():
    password = "secret123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_token({"sub": "42"})
    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"


def test_decode_invalid_token_returns_none():
    assert decode_token("invalid.token.here") is None


def test_different_passwords_produce_different_hashes():
    h1 = hash_password("password1")
    h2 = hash_password("password1")
    # bcrypt는 같은 입력도 매번 다른 해시 생성
    assert h1 != h2
    assert verify_password("password1", h1)
    assert verify_password("password1", h2)
```

- [ ] **Step 2: Run to verify fails**

```powershell
cd backend
uv run pytest tests/test_security.py -v
```
Expected: `ImportError: cannot import name 'hash_password'`

- [ ] **Step 3: Create `core/__init__.py`** (empty)

Create `backend/app/core/__init__.py`:
```python
```

- [ ] **Step 4: Create `core/security.py`**

Create `backend/app/core/security.py`:
```python
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None
```

- [ ] **Step 5: Run to verify passes**

```powershell
uv run pytest tests/test_security.py -v
```
Expected: `4 passed`

- [ ] **Step 6: Commit**

```powershell
cd ..
git add backend/app/core/security.py backend/app/core/__init__.py backend/tests/test_security.py
git commit -m "feat(backend): add security utilities (bcrypt + JWT)"
```

---

### Task 6: Pydantic Schemas + Dependency Injection

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/verification.py`
- Create: `backend/app/core/deps.py`

- [ ] **Step 1: Create `schemas/__init__.py`** (empty)

- [ ] **Step 2: Create `schemas/auth.py`**

Create `backend/app/schemas/auth.py`:
```python
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    university: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다")
        return v

    @field_validator("name", "university")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 값은 허용되지 않습니다")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 3: Create `schemas/user.py`**

Create `backend/app/schemas/user.py`:
```python
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.user import UserStatus


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    university: str
    status: UserStatus
    profile_photo: str | None
    bio: str | None
    instagram: str | None
    kakao_id: str | None
    phone: str | None
    matching_paused: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    bio: str | None = None
    instagram: str | None = None
    kakao_id: str | None = None
    phone: str | None = None

    @field_validator("instagram", "kakao_id", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v


class MatchingPauseUpdate(BaseModel):
    matching_paused: bool
```

- [ ] **Step 4: Create `schemas/verification.py`**

Create `backend/app/schemas/verification.py`:
```python
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.verification import VerificationStatus


class VerificationOut(BaseModel):
    id: int
    user_id: int
    image_url: str
    status: VerificationStatus
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VerificationAction(BaseModel):
    action: str  # "approve" or "reject"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v
```

- [ ] **Step 5: Create `core/deps.py`**

Create `backend/app/core/deps.py`:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다",
        )
    user = db.get(User, int(user_id_str))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="존재하지 않는 사용자입니다",
        )
    return user


def get_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인 대기 중입니다. 관리자 승인 후 이용 가능합니다",
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다",
        )
    return current_user
```

- [ ] **Step 6: Commit**

```powershell
cd ..
git add backend/app/schemas/ backend/app/core/deps.py
git commit -m "feat(backend): add Pydantic schemas and dependency injection"
```

---

### Task 7: Auth Endpoints

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing auth tests**

Create `backend/tests/test_auth.py`:
```python
from fastapi.testclient import TestClient


def test_register_new_user(client: TestClient):
    response = client.post("/auth/register", json={
        "email": "test@korea.ac.kr",
        "password": "password123",
        "name": "김테스트",
        "university": "고려대학교",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@korea.ac.kr"
    assert data["status"] == "pending"
    assert "password_hash" not in data


def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "dup@korea.ac.kr",
        "password": "password123",
        "name": "김중복",
        "university": "고려대학교",
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_register_weak_password(client: TestClient):
    response = client.post("/auth/register", json={
        "email": "weak@korea.ac.kr",
        "password": "123",
        "name": "김약함",
        "university": "고려대학교",
    })
    assert response.status_code == 422


def test_login_success(client: TestClient):
    client.post("/auth/register", json={
        "email": "login@korea.ac.kr",
        "password": "password123",
        "name": "김로그인",
        "university": "고려대학교",
    })
    response = client.post("/auth/login", json={
        "email": "login@korea.ac.kr",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    client.post("/auth/register", json={
        "email": "wrong@korea.ac.kr",
        "password": "password123",
        "name": "김틀림",
        "university": "고려대학교",
    })
    response = client.post("/auth/login", json={
        "email": "wrong@korea.ac.kr",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    response = client.post("/auth/login", json={
        "email": "noone@korea.ac.kr",
        "password": "password123",
    })
    assert response.status_code == 401
```

- [ ] **Step 2: Run to verify fails**

```powershell
cd backend
uv run pytest tests/test_auth.py -v
```
Expected: `404 Not Found` 또는 connection error — 라우터 미등록.

- [ ] **Step 3: Create `api/__init__.py`** (empty)

- [ ] **Step 4: Create `api/auth.py`**

Create `backend/app/api/auth.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        university=payload.university,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )
    token = create_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)
```

- [ ] **Step 5: Create `api/router.py`**

Create `backend/app/api/router.py`:
```python
from fastapi import APIRouter
from app.api import auth

router = APIRouter()
router.include_router(auth.router)
```

- [ ] **Step 6: Register router in `main.py`**

Replace `backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401
from app.api.router import router

app = FastAPI(title="DateDrop Korea API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests to verify passes**

```powershell
uv run pytest tests/test_auth.py tests/test_main.py -v
```
Expected: `7 passed`

- [ ] **Step 8: Commit**

```powershell
cd ..
git add backend/app/api/ backend/app/main.py backend/tests/test_auth.py
git commit -m "feat(backend): add auth endpoints (register, login)"
```

---

### Task 8: /me Endpoints

**Files:**
- Create: `backend/app/api/me.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_me.py`

- [ ] **Step 1: Write failing /me tests**

Create `backend/tests/test_me.py`:
```python
from fastapi.testclient import TestClient


def _register_and_get_headers(client: TestClient, email: str = "me@test.com") -> dict:
    client.post("/auth/register", json={
        "email": email,
        "password": "password123",
        "name": "김미",
        "university": "서울대학교",
    })
    res = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_get_me(client: TestClient):
    headers = _register_and_get_headers(client)
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["status"] == "pending"


def test_get_me_unauthorized(client: TestClient):
    response = client.get("/me")
    assert response.status_code == 401


def test_update_profile(client: TestClient):
    headers = _register_and_get_headers(client, "profile@test.com")
    response = client.put("/me/profile", json={
        "bio": "안녕하세요!",
        "instagram": "myinsta",
    }, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "안녕하세요!"
    assert data["instagram"] == "myinsta"
    assert data["kakao_id"] is None


def test_update_profile_clears_field_with_empty_string(client: TestClient):
    headers = _register_and_get_headers(client, "clear@test.com")
    client.put("/me/profile", json={"instagram": "myinsta"}, headers=headers)
    response = client.put("/me/profile", json={"instagram": ""}, headers=headers)
    assert response.status_code == 200
    assert response.json()["instagram"] is None


def test_toggle_matching_pause(client: TestClient):
    headers = _register_and_get_headers(client, "pause@test.com")
    res = client.put("/me/matching-pause", json={"matching_paused": True}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is True

    res = client.put("/me/matching-pause", json={"matching_paused": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["matching_paused"] is False
```

- [ ] **Step 2: Run to verify fails**

```powershell
uv run pytest tests/test_me.py -v
```
Expected: All fail with `404`.

- [ ] **Step 3: Create `api/me.py`**

Create `backend/app/api/me.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.user import MatchingPauseUpdate, ProfileUpdate, UserOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/matching-pause", response_model=UserOut)
def toggle_matching_pause(
    payload: MatchingPauseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.matching_paused = payload.matching_paused
    db.commit()
    db.refresh(current_user)
    return current_user
```

- [ ] **Step 4: Add me router to `api/router.py`**

Replace `backend/app/api/router.py`:
```python
from fastapi import APIRouter
from app.api import auth, me

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
```

- [ ] **Step 5: Run to verify passes**

```powershell
uv run pytest tests/test_me.py -v
```
Expected: `5 passed`

- [ ] **Step 6: Commit**

```powershell
cd ..
git add backend/app/api/me.py backend/app/api/router.py backend/tests/test_me.py
git commit -m "feat(backend): add /me endpoints (profile, matching-pause)"
```

---

### Task 9: Student ID Upload + Admin Verification

**Files:**
- Create: `backend/app/api/verification.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_verification.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_verification.py`:
```python
import io
from fastapi.testclient import TestClient


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
```

- [ ] **Step 2: Run to verify fails**

```powershell
uv run pytest tests/test_verification.py -v
```
Expected: All fail with `404`.

- [ ] **Step 3: Create `api/verification.py`**

Create `backend/app/api/verification.py`:
```python
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.models.user import User, UserStatus
from app.models.verification import StudentVerification, VerificationStatus
from app.schemas.verification import VerificationAction, VerificationOut

router = APIRouter(tags=["verification"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/verification/upload", response_model=VerificationOut, status_code=201)
async def upload_student_id(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JPG, PNG, WEBP 파일만 업로드 가능합니다",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 크기는 10MB 이하여야 합니다",
        )

    # 로컬 저장 (개발용) — 프로덕션은 S3로 교체
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = "jpg"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    # upsert: 이미 제출한 경우 덮어쓰기
    verification = (
        db.query(StudentVerification)
        .filter(StudentVerification.user_id == current_user.id)
        .first()
    )
    if verification:
        verification.image_url = filepath
        verification.status = VerificationStatus.pending
        verification.reviewed_at = None
        verification.reviewed_by = None
    else:
        verification = StudentVerification(
            user_id=current_user.id,
            image_url=filepath,
        )
        db.add(verification)

    db.commit()
    db.refresh(verification)
    return verification


@router.get("/admin/verifications", response_model=list[VerificationOut])
def list_pending_verifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return (
        db.query(StudentVerification)
        .filter(StudentVerification.status == VerificationStatus.pending)
        .all()
    )


@router.post("/admin/verifications/{verification_id}", response_model=VerificationOut)
def review_verification(
    verification_id: int,
    payload: VerificationAction,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    verification = db.get(StudentVerification, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    if payload.action == "approve":
        verification.status = VerificationStatus.approved
        user = db.get(User, verification.user_id)
        if user:
            user.status = UserStatus.active
    else:
        verification.status = VerificationStatus.rejected

    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = admin.id
    db.commit()
    db.refresh(verification)
    return verification
```

- [ ] **Step 4: Add verification router to `api/router.py`**

Replace `backend/app/api/router.py`:
```python
from fastapi import APIRouter
from app.api import auth, me, verification

router = APIRouter()
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(verification.router)
```

- [ ] **Step 5: Run all tests**

```powershell
uv run pytest -v
```
Expected:
```
tests/test_auth.py          6 passed
tests/test_main.py          1 passed
tests/test_me.py            5 passed
tests/test_security.py      4 passed
tests/test_verification.py  5 passed
21 passed
```

- [ ] **Step 6: Commit**

```powershell
cd ..
git add backend/app/api/verification.py backend/app/api/router.py backend/tests/test_verification.py
git commit -m "feat(backend): add student ID upload + admin verification endpoints"
```

---

## Self-Review

**Spec 커버리지:**
| 엔드포인트 | 태스크 | 상태 |
|---|---|---|
| POST /auth/register | Task 7 | ✅ |
| POST /auth/login | Task 7 | ✅ |
| POST /auth/logout | — | ⏭️ JWT 무상태 — 클라이언트가 토큰 파기, 서버 불필요 |
| GET /me | Task 8 | ✅ |
| PUT /me/profile | Task 8 | ✅ |
| PUT /me/matching-pause | Task 8 | ✅ |
| PUT /me/survey | — | ⏭️ Plan 3 (Survey & Profile) |
| POST /verification/upload | Task 9 | ✅ |
| GET /admin/verifications | Task 9 | ✅ |
| POST /admin/verifications/{id} | Task 9 | ✅ |
| /game/* | — | ⏭️ Plan 4 |
| /admin/match/* | — | ⏭️ Plan 5 |
| POST /reports | — | ⏭️ Plan 6 |

**플레이스홀더 스캔:** 없음. 모든 단계 실제 코드 포함.

**타입 일관성:**
- `UserOut` — auth.py register, me.py get_me/update_profile/toggle_pause 모두 동일 ✅
- `VerificationOut` — verification.py 전체 ✅
- `get_current_user` 반환 `User` — me.py, verification.py ✅
- `require_admin` 반환 `User` — verification.py ✅
- `create_token({"sub": str(user.id)})` → `decode_token` → `int(user_id_str)` — deps.py ✅
