"""match_rounds scheduled_at unique

Revision ID: 9c9c633d854d
Revises: 14396bd32c23
Create Date: 2026-08-17 22:25:35.252611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c9c633d854d'
down_revision: Union[str, Sequence[str], None] = '14396bd32c23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 앱 레이어 중복 검사(_reject_duplicate)와 INSERT 사이의 경쟁을 DB가 막는다.
    # UNIQUE 제약 대신 유니크 인덱스 — SQLite에서 테이블 재생성 없이 붙고,
    # matches의 FK 참조를 건드리지 않는다.
    op.create_index(
        "uq_match_rounds_scheduled_at", "match_rounds", ["scheduled_at"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_match_rounds_scheduled_at", table_name="match_rounds")
