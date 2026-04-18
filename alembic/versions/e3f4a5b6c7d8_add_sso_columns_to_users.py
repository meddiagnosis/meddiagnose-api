"""add SSO columns to users (oauth_provider, oauth_id, nullable hashed_password)

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-03-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add oauth columns (idempotent for PostgreSQL)
    for col, typ in [
        ('oauth_provider', 'VARCHAR(50)'),
        ('oauth_id', 'VARCHAR(255)'),
    ]:
        conn.execute(sa.text(f"""
            DO $$ BEGIN
                ALTER TABLE users ADD COLUMN {col} {typ};
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))
    # Make hashed_password nullable for SSO users
    op.alter_column(
        'users',
        'hashed_password',
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    # Note: downgrade may fail if SSO users exist (hashed_password is NULL)
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
    op.alter_column(
        'users',
        'hashed_password',
        existing_type=sa.String(255),
        nullable=False,
    )
