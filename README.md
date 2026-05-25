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
cp .env.example .env
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
