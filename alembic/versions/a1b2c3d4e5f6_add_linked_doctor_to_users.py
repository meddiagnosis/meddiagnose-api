"""add linked_doctor_id to users for patient-doctor linking

Revision ID: a1b2c3d4e5f6
Revises: 92c3d4e5f6a7
Create Date: 2026-03-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('linked_doctor_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_users_linked_doctor_id',
        'users',
        'users',
        ['linked_doctor_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_users_linked_doctor_id', 'users', ['linked_doctor_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_users_linked_doctor_id', table_name='users')
    op.drop_constraint('fk_users_linked_doctor_id', 'users', type_='foreignkey')
    op.drop_column('users', 'linked_doctor_id')
