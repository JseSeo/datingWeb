# Backend — FastAPI

FastAPI + SQLAlchemy 2.0 + PostgreSQL.

## 개발 명령

```bash
uv run uvicorn app.main:app --reload        # 개발 서버 (포트 8000)
uv run pytest -v                            # 테스트
uv run alembic revision --autogenerate -m "설명"  # 마이그레이션 생성
uv run alembic upgrade head                 # 마이그레이션 적용
```

## 코드 구조

```
app/
  main.py        # FastAPI 앱, CORS, 라우터 등록
  config.py      # Settings (pydantic-settings, .env)
  database.py    # SQLAlchemy 세션 (get_db)
  api/           # 엔드포인트 (auth, me, verification, ...)
  models/        # SQLAlchemy ORM 모델
  schemas/       # Pydantic 입출력 스키마
  core/
    security.py  # bcrypt 해시, JWT 생성/검증
    deps.py      # get_current_user, get_active_user, require_admin
```

## 코딩 규칙

| 규칙 | 내용 |
|------|------|
| 스키마 | 엔드포인트마다 Pydantic 스키마 사용. dict 반환 금지 |
| 스키마 분리 | 입력(Create) ≠ 응답(Response) 스키마 분리 |
| DB 세션 | `get_db` 의존성 주입 사용 |
| 인증 | `get_current_user` / `get_active_user` / `require_admin` (core.deps) |
| 비밀번호 | 평문 저장 절대 금지. `hash_password` (core.security)만 사용 |
| 모델 추가 | `app/models/__init__.py` re-export 목록 업데이트 필수 |
| 환경변수 | 하드코딩 금지. `config.py` Settings 통해서만 |
| 에러 응답 | `HTTPException(status_code=..., detail="...")` |

## 도메인 규칙

| 규칙 | 내용 |
|------|------|
| User.status | `pending` → `active` → `suspended`. 관리자만 변경 가능 |
| 학생증 이미지 | 승인 후 즉시 삭제 또는 암호화 보관 (개인정보보호법) |
| 연락처 | instagram / kakao_id / phone 중 1개 이상 필수 |
| 매칭 참여 | 설문 완료 + active 상태만 가능 |
| 회원 탈퇴 | 연락처·학생증·설문 즉시 삭제 |
| 오작교 추천인 | 피추천인에게 익명 (비공개) |
| 붉은 실 | 단방향 입력 시 대기·알림 없음. 양방향 시 100% 매칭 |
