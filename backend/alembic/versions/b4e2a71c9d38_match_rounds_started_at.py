"""match_rounds started_at

Revision ID: b4e2a71c9d38
Revises: f0d8b2e2d9c2
Create Date: 2026-08-29 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e2a71c9d38'
down_revision: Union[str, Sequence[str], None] = 'f0d8b2e2d9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # nullable — 이미 있는 행은 NULL로 남는다. 되돌리기 가드는 NULL을
    # "추적 이전에 멈춘 라운드"로 보고 유예 없이 통과시킨다
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.drop_column("started_at")
