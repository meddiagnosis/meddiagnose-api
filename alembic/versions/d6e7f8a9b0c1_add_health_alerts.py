"""add health_alerts table for automated vitals monitoring

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-03-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'health_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('metric', sa.String(80), nullable=False),
        sa.Column('metric_label', sa.String(100), nullable=True),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('normal_min', sa.Float(), nullable=True),
        sa.Column('normal_max', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False, server_default='warning'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_health_alerts_user_id', 'health_alerts', ['user_id'], unique=False)
    op.create_index('ix_health_alerts_metric', 'health_alerts', ['metric'], unique=False)
    op.create_index('ix_health_alerts_status', 'health_alerts', ['status'], unique=False)
    op.create_index('ix_health_alerts_created_at', 'health_alerts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('health_alerts')
