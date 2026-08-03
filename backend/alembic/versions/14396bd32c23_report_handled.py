"""report handled

Revision ID: 14396bd32c23
Revises: 33aa8ba5f23f
Create Date: 2026-08-03 01:12:25.380870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14396bd32c23'
down_revision: Union[str, Sequence[str], None] = '33aa8ba5f23f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "reports",
        sa.Column("handled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("reports", "handled")
