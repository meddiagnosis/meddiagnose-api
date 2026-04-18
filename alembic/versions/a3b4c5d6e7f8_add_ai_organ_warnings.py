"""add ai_organ_warnings to diagnoses

Revision ID: a3b4c5d6e7f8
Revises: 92c3d4e5f6a7
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = '92c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('ai_organ_warnings', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'ai_organ_warnings')
