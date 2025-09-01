"""Add skills module

Revision ID: 95f4da89fc59
Revises: b6aed319328a
Create Date: 2025-09-01 11:05:55.035183

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "95f4da89fc59"
down_revision: Union[str, Sequence[str], None] = "b6aed319328a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create skills table
    op.create_table(
        "skill",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_skill_name"), "skill", ["name"], unique=False)

    # Create user_skill_link table
    op.create_table(
        "userskilllink",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skill.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "skill_id"),
    )

    # Create repository_skill_link table
    op.create_table(
        "repositoryskilllink",
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skill.id"],
        ),
        sa.PrimaryKeyConstraint("repository_id", "skill_id"),
    )

    # Create task_user_link table
    op.create_table(
        "taskuserlink",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("times_correct", sa.Integer(), nullable=False),
        sa.Column("times_incorrect", sa.Integer(), nullable=False),
        sa.Column("times_partial", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["task.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("task_id", "user_id"),
    )

    # Add skill_id column to task table
    op.add_column(
        "task", sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(None, "task", "skill", ["skill_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove skill_id column from task table
    op.drop_constraint(None, "task", type_="foreignkey")
    op.drop_column("task", "skill_id")

    # Drop task_user_link table
    op.drop_table("taskuserlink")

    # Drop repository_skill_link table
    op.drop_table("repositoryskilllink")

    # Drop user_skill_link table
    op.drop_table("userskilllink")

    # Drop skills table
    op.drop_index(op.f("ix_skill_name"), table_name="skill")
    op.drop_table("skill")
