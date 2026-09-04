"""universities and admission year

Revision ID: 663fa9cf7ce5
Revises: c3f5a1d20b47
Create Date: 2026-09-04 20:36:31.768700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '663fa9cf7ce5'
down_revision: Union[str, Sequence[str], None] = 'c3f5a1d20b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_universities_id"), "universities", ["id"])
    op.create_index(op.f("ix_universities_name"), "universities", ["name"], unique=True)

    op.add_column("users", sa.Column("admission_year", sa.Integer(), nullable=True))

    with op.batch_alter_table("ojakgyo", schema=None) as batch:
        batch.add_column(sa.Column(
            "person_a_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.add_column(sa.Column(
            "person_b_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.drop_constraint("uq_ojakgyo_recommender_pair", type_="unique")
        batch.create_unique_constraint(
            "uq_ojakgyo_recommender_pair",
            [
                "recommender_id",
                "person_a_name", "person_a_university", "person_a_admission_year",
                "person_b_name", "person_b_university", "person_b_admission_year",
            ],
        )

    with op.batch_alter_table("red_threads", schema=None) as batch:
        batch.add_column(sa.Column(
            "target_admission_year", sa.Integer(), nullable=False, server_default="0"
        ))
        batch.drop_constraint("uq_red_thread_user_target", type_="unique")
        batch.create_unique_constraint(
            "uq_red_thread_user_target",
            ["user_id", "target_name", "target_university", "target_admission_year"],
        )


def downgrade() -> None:
    with op.batch_alter_table("red_threads", schema=None) as batch:
        batch.drop_constraint("uq_red_thread_user_target", type_="unique")
        batch.create_unique_constraint(
            "uq_red_thread_user_target",
            ["user_id", "target_name", "target_university"],
        )
        batch.drop_column("target_admission_year")

    with op.batch_alter_table("ojakgyo", schema=None) as batch:
        batch.drop_constraint("uq_ojakgyo_recommender_pair", type_="unique")
        batch.create_unique_constraint(
            "uq_ojakgyo_recommender_pair",
            [
                "recommender_id",
                "person_a_name", "person_a_university",
                "person_b_name", "person_b_university",
            ],
        )
        batch.drop_column("person_b_admission_year")
        batch.drop_column("person_a_admission_year")

    op.drop_column("users", "admission_year")
    op.drop_index(op.f("ix_universities_name"), table_name="universities")
    op.drop_index(op.f("ix_universities_id"), table_name="universities")
    op.drop_table("universities")
