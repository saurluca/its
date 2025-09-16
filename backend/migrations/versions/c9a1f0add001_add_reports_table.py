"""add reports table

Revision ID: c9a1f0add001
Revises: b6aed319328a_add_repository_based_access
Create Date: 2025-09-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "c9a1f0add001"
down_revision: Union[str, Sequence[str], None] = ("6c7ebb16cf35", "b49dba212232")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report",
        sa.Column("report_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("category_tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("user_agent", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["unit.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("report")
