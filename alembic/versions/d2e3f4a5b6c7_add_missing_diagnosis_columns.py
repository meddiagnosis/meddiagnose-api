"""add missing diagnosis columns

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-03-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE diagnoses ALTER COLUMN status TYPE VARCHAR(30) USING status::text")
    op.add_column('diagnoses', sa.Column('ai_medications', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_lifestyle', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_precautions', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_severity', sa.String(20), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_urgency', sa.String(20), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_when_to_see_doctor', sa.Text(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_recommended_tests', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('ai_drug_interactions', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('report_files', sa.JSON(), nullable=True))
    op.add_column('diagnoses', sa.Column('symptoms_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('diagnoses', 'symptoms_text')
    op.drop_column('diagnoses', 'report_files')
    op.drop_column('diagnoses', 'ai_drug_interactions')
    op.drop_column('diagnoses', 'ai_recommended_tests')
    op.drop_column('diagnoses', 'ai_when_to_see_doctor')
    op.drop_column('diagnoses', 'ai_urgency')
    op.drop_column('diagnoses', 'ai_severity')
    op.drop_column('diagnoses', 'ai_precautions')
    op.drop_column('diagnoses', 'ai_lifestyle')
    op.drop_column('diagnoses', 'ai_medications')
    op.execute("ALTER TABLE diagnoses ALTER COLUMN status TYPE diagnosisstatus USING status::diagnosisstatus")
