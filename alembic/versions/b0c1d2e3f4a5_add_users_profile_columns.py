"""add users profile columns (date_of_birth, gender, etc.)

Revision ID: b0c1d2e3f4a5
Revises: a9a17bb661f9
Create Date: 2026-03-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, None] = 'a9a17bb661f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    for col, typ in [
        ('date_of_birth', 'VARCHAR(20)'),
        ('gender', 'VARCHAR(20)'),
        ('blood_group', 'VARCHAR(10)'),
        ('allergies', 'VARCHAR(500)'),
        ('phone', 'VARCHAR(20)'),
        ('weight_kg', 'DOUBLE PRECISION'),
    ]:
        conn.execute(sa.text(f"""
            DO $$ BEGIN
                ALTER TABLE users ADD COLUMN {col} {typ};
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))


def downgrade() -> None:
    op.drop_column('users', 'weight_kg')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'allergies')
    op.drop_column('users', 'blood_group')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'date_of_birth')
