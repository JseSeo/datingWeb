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
| 오작교 | 제3자가 두 사람(이름+학교) 지목 중매. 지목자 익명. 본인은 두 사람에 못 들어감. 같은 지목자·같은 쌍 중복 불가 |
| 붉은 실 | 최대 2명 입력(목록 통째 교체). 1~2명/본인불가/같은상대 중복불가. 이름·학교 strip 후 저장·비교. 상호 여부는 본인에게 비공개(매칭 시 드러남). 지목당한 유저엔 인원수 알림(지목자 익명). 양방향 시 100% 매칭 |
| 오작교 strip | 두 사람 이름·학교 strip 후 저장·비교 (쌍 중복판정도 strip 기준) |
