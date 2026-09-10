"""관리자 계정 시드.

빈 DB에는 관리자가 없어 아무도 가입 승인을 못 한다. 첫 관리자는 앱 밖에서
심어야 해서 이 스크립트가 있다. 값은 환경변수로 받는다 — 비밀번호가 코드에
남으면 운영 DB에 그대로 실릴 수 있다.
"""

import argparse
import sys

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import Gender, User, UserStatus

# 관리자는 학생이 아니지만 name/university/gender가 NOT NULL이다. 환경변수를
# 늘리는 대신 고정값을 쓴다. university는 universities 테이블에 없는 이름이라
# 대학 삭제 시 참조 검사에도 걸리지 않는다.
PLACEHOLDER_NAME = "관리자"
PLACEHOLDER_UNIVERSITY = "관리자"


def seed_admin(db: Session, email: str, password: str, force: bool = False) -> str:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        if not force:
            return "unchanged"
        existing.password_hash = hash_password(password)
        existing.is_admin = True
        existing.status = UserStatus.active
        db.commit()
        return "updated"

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=PLACEHOLDER_NAME,
        university=PLACEHOLDER_UNIVERSITY,
        gender=Gender.male,
        status=UserStatus.active,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    return "created"


# 윈도우 콘솔(cp949)에서 깨지지 않는 문자만 쓴다. em dash 같은 문자를 넣으면
# DB 작업을 마친 뒤 print에서 죽어 성공이 실패로 보인다
MESSAGES = {
    "created": "관리자 생성됨",
    "unchanged": "이미 존재하는 계정. 변경 없음 (덮어쓰려면 --force)",
    "updated": "관리자 갱신됨. 비밀번호 재설정, 권한/상태 복구",
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="관리자 계정 시드")
    parser.add_argument(
        "--force",
        action="store_true",
        help="계정이 이미 있으면 비밀번호·권한·상태를 덮어쓴다",
    )
    args = parser.parse_args(argv)

    if not settings.admin_email or not settings.admin_password:
        print(
            "ADMIN_EMAIL, ADMIN_PASSWORD 환경변수가 필요합니다 (.env 참고)",
            file=sys.stderr,
        )
        raise SystemExit(1)

    db = SessionLocal()
    try:
        result = seed_admin(
            db, settings.admin_email, settings.admin_password, force=args.force
        )
    finally:
        db.close()
    print(f"{MESSAGES[result]}: {settings.admin_email}")


if __name__ == "__main__":
    main()
