"""match_rounds last_error

Revision ID: 6cb8bd3e1586
Revises: 663fa9cf7ce5
Create Date: 2026-09-05 17:51:27.811629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cb8bd3e1586'
down_revision: Union[str, Sequence[str], None] = '663fa9cf7ce5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # nullable — 기존 행은 NULL(= 실패 이력 없음)로 남는다
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.add_column(sa.Column("last_error", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("match_rounds") as batch_op:
        batch_op.drop_column("last_error")
