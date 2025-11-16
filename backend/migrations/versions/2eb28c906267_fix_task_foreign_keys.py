"""fix task foreign keys

Revision ID: 7115a6db0acf
Revises: cdcff104e1d3
Create Date: 2025-11-04 21:16:25.966336

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7115a6db0acf"
down_revision: Union[str, Sequence[str], None] = "cdcff104e1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Fix TaskMetrics foreign key - use correct constraint name
    op.drop_constraint("fk_taskmetrics_task_id_task", "taskmetrics", type_="foreignkey")
    op.create_foreign_key(
        "fk_taskmetrics_task_id_task",
        "taskmetrics",
        "task",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Fix EventLog foreign key - use correct constraint name
    op.drop_constraint("fk_eventlog_task_id_task", "eventlog", type_="foreignkey")
    op.create_foreign_key(
        "fk_eventlog_task_id_task",
        "eventlog",
        "task",
        ["task_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Fix TaskVersion foreign key - use correct constraint name
    op.drop_constraint("fk_taskversion_task_id_task", "taskversion", type_="foreignkey")
    op.create_foreign_key(
        "fk_taskversion_task_id_task",
        "taskversion",
        "task",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Fix UserAnswerLog foreign key
    op.drop_constraint(
        "fk_useranswerlog_task_id_task", "useranswerlog", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_useranswerlog_task_id_task",
        "useranswerlog",
        "task",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    # Revert changes - use correct constraint names
    op.drop_constraint("fk_taskmetrics_task_id_task", "taskmetrics", type_="foreignkey")
    op.create_foreign_key(
        "fk_taskmetrics_task_id_task", "taskmetrics", "task", ["task_id"], ["id"]
    )

    op.drop_constraint("fk_eventlog_task_id_task", "eventlog", type_="foreignkey")
    op.create_foreign_key(
        "fk_eventlog_task_id_task", "eventlog", "task", ["task_id"], ["id"]
    )

    op.drop_constraint("fk_taskversion_task_id_task", "taskversion", type_="foreignkey")
    op.create_foreign_key(
        "fk_taskversion_task_id_task", "taskversion", "task", ["task_id"], ["id"]
    )

    op.drop_constraint(
        "fk_useranswerlog_task_id_task", "useranswerlog", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_useranswerlog_task_id_task", "useranswerlog", "task", ["task_id"], ["id"]
    )
