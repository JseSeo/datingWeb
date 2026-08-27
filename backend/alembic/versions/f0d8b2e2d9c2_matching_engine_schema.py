"""matching engine schema

Revision ID: f0d8b2e2d9c2
Revises: 9c9c633d854d
Create Date: 2026-08-25 01:34:00.189319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0d8b2e2d9c2'
down_revision: Union[str, Sequence[str], None] = '9c9c633d854d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("missed_rounds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "matches",
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )
    # SQLite는 ALTER로 제약을 못 붙인다. batch_alter_table이 테이블 재생성으로 처리한다
    with op.batch_alter_table("matches") as batch:
        batch.create_unique_constraint(
            "uq_matches_round_user_a", ["match_round_id", "user_a_id"]
        )
        batch.create_unique_constraint(
            "uq_matches_round_user_b", ["match_round_id", "user_b_id"]
        )
    # PostgreSQL은 enum 타입에 값을 명시적으로 추가해야 한다. SQLite는 VARCHAR라 불필요
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE round_status ADD VALUE IF NOT EXISTS 'running'")


def downgrade() -> None:
    with op.batch_alter_table("matches") as batch:
        batch.drop_constraint("uq_matches_round_user_b", type_="unique")
        batch.drop_constraint("uq_matches_round_user_a", type_="unique")
    op.drop_column("matches", "score")
    op.drop_column("users", "missed_rounds")
    # PostgreSQL은 enum 값 제거를 지원하지 않는다. 'running'은 남겨둔다
