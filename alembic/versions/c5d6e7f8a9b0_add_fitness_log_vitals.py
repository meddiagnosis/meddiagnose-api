"""add heart_rate and spo2 to fitness_logs for live vitals from wearables

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('fitness_logs', sa.Column('heart_rate', sa.Float(), nullable=True))
    op.add_column('fitness_logs', sa.Column('spo2', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('fitness_logs', 'spo2')
    op.drop_column('fitness_logs', 'heart_rate')
