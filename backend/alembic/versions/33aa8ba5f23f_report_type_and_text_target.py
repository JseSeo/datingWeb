"""report type and text target

Revision ID: 33aa8ba5f23f
Revises: f791f9b09268
Create Date: 2026-08-02 13:55:46.152388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33aa8ba5f23f'
down_revision: Union[str, Sequence[str], None] = 'f791f9b09268'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    report_type = sa.Enum("report", "suggestion", name="report_type")
    report_type.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("type", report_type, nullable=False))
        batch_op.add_column(sa.Column("target_name", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column("target_university", sa.String(length=100), nullable=True)
        )
        batch_op.drop_column("target_id")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("target_id", sa.Integer(), nullable=False))
        batch_op.drop_column("target_university")
        batch_op.drop_column("target_name")
        batch_op.drop_column("type")
    sa.Enum(name="report_type").drop(op.get_bind(), checkfirst=True)
