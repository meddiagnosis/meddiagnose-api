"""use varchar for batch status (match model)

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-03-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE batches ALTER COLUMN status TYPE VARCHAR(30) USING status::text")


def downgrade() -> None:
    op.execute("ALTER TABLE batches ALTER COLUMN status TYPE batchstatus USING status::batchstatus")
