"""matching university weights

Revision ID: c3f5a1d20b47
Revises: b4e2a71c9d38
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f5a1d20b47'
down_revision: Union[str, Sequence[str], None] = 'b4e2a71c9d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # university_b는 nullable이 아니다 — NULL을 허용하면 유니크가 중복 규칙을 못 막는다
    op.create_table(
        "matching_university_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("university_a", sa.String(length=100), nullable=False),
        sa.Column("university_b", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("bonus", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "university_a", "university_b", name="uq_university_weights_pair"
        ),
    )
    op.create_index(
        op.f("ix_matching_university_weights_id"),
        "matching_university_weights",
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_matching_university_weights_id"),
        table_name="matching_university_weights",
    )
    op.drop_table("matching_university_weights")
