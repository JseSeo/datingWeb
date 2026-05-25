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
