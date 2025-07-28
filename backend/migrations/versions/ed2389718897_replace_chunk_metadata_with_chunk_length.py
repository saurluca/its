"""replace chunk metadata with chunk length

Revision ID: ed2389718897
Revises: 7ea0b31d4194
Create Date: 2025-07-28 11:37:12.692718

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ed2389718897"
down_revision: Union[str, Sequence[str], None] = "7ea0b31d4194"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add chunk_length column
    op.add_column("chunk", sa.Column("chunk_length", sa.INTEGER(), nullable=True))

    # Drop chunk_metadata column
    op.drop_column("chunk", "chunk_metadata")


def downgrade() -> None:
    """Downgrade schema."""
    # Add chunk_metadata column back
    op.add_column("chunk", sa.Column("chunk_metadata", sa.VARCHAR(), nullable=True))

    # Drop chunk_length column
    op.drop_column("chunk", "chunk_length")
