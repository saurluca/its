"""Adding missing model

Revision ID: 22e567a189b4
Revises: 92edd72fe1ad
Create Date: 2025-11-16 19:05:00.456720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '22e567a189b4'
down_revision: Union[str, Sequence[str], None] = '92edd72fe1ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('unittaskevent',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('unit_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column(
            'action',
            postgresql.ENUM('ADDED', 'REMOVED', name='unittaskaction', create_type=False),
            nullable=False
        ),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ),
        sa.ForeignKeyConstraint(['unit_id'], ['unit.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unittaskevent_created_at'), 'unittaskevent', ['created_at'], unique=False)
    op.create_index(op.f('ix_unittaskevent_task_id'), 'unittaskevent', ['task_id'], unique=False)
    op.create_index(op.f('ix_unittaskevent_unit_id'), 'unittaskevent', ['unit_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_unittaskevent_unit_id'), table_name='unittaskevent')
    op.drop_index(op.f('ix_unittaskevent_task_id'), table_name='unittaskevent')
    op.drop_index(op.f('ix_unittaskevent_created_at'), table_name='unittaskevent')
    op.drop_table('unittaskevent')