"""add ai_extracted_lab_values to diagnoses

Revision ID: 81b2c3d4e5f6
Revises: 70ab5f14ed06
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '81b2c3d4e5f6'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('ai_extracted_lab_values', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'ai_extracted_lab_values')
