"""add prescription safety columns to diagnoses

Revision ID: 92c3d4e5f6a7
Revises: 81b2c3d4e5f6
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '92c3d4e5f6a7'
down_revision: Union[str, None] = '81b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('diagnoses', sa.Column('ai_allergy_warnings', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_high_risk_drug_warnings', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'ai_high_risk_drug_warnings')
    op.drop_column('diagnoses', 'ai_allergy_warnings')
