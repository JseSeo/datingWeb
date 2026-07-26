"""add user gender

Revision ID: f791f9b09268
Revises: 8ed1fb6913e1
Create Date: 2026-07-27 01:01:36.959063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f791f9b09268'
down_revision: Union[str, Sequence[str], None] = '8ed1fb6913e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "gender",
            sa.Enum("male", "female", name="gender"),
            nullable=False,
            server_default="male",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "gender")
    sa.Enum(name="gender").drop(op.get_bind(), checkfirst=True)
