"""add onboarding_completed to users

Revision ID: f5b6c7d8e9f0
Revises: a3b4c5d6e7f8
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f5b6c7d8e9f0'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT TRUE NOT NULL;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """))


def downgrade() -> None:
    op.drop_column('users', 'onboarding_completed')
