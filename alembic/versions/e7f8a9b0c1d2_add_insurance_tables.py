"""add insurance_policies, insurance_bills, insurance_claims tables

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-03-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'insurance_policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider_type', sa.String(30), nullable=False),
        sa.Column('provider_name', sa.String(100), nullable=False),
        sa.Column('policy_number', sa.String(100), nullable=False),
        sa.Column('member_id', sa.String(100), nullable=True),
        sa.Column('group_id', sa.String(100), nullable=True),
        sa.Column('sum_insured', sa.Float(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scheme_name', sa.String(100), nullable=True),
        sa.Column('abha_number', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_insurance_policies_user_id', 'insurance_policies', ['user_id'], unique=False)
    op.create_index('ix_insurance_policies_policy_number', 'insurance_policies', ['policy_number'], unique=False)

    op.create_table(
        'insurance_bills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=True),
        sa.Column('bill_date', sa.Date(), nullable=False),
        sa.Column('hospital_name', sa.String(200), nullable=False),
        sa.Column('hospital_address', sa.String(500), nullable=True),
        sa.Column('treatment_description', sa.Text(), nullable=True),
        sa.Column('diagnosis_id', sa.Integer(), nullable=True),
        sa.Column('amount_total', sa.Float(), nullable=False),
        sa.Column('amount_breakdown', sa.Text(), nullable=True),
        sa.Column('document_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['policy_id'], ['insurance_policies.id']),
        sa.ForeignKeyConstraint(['diagnosis_id'], ['diagnoses.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_insurance_bills_user_id', 'insurance_bills', ['user_id'], unique=False)
    op.create_index('ix_insurance_bills_policy_id', 'insurance_bills', ['policy_id'], unique=False)

    op.create_table(
        'insurance_claims',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('bill_id', sa.Integer(), nullable=False),
        sa.Column('claim_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('amount_claimed', sa.Float(), nullable=False),
        sa.Column('amount_approved', sa.Float(), nullable=True),
        sa.Column('amount_paid', sa.Float(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['policy_id'], ['insurance_policies.id']),
        sa.ForeignKeyConstraint(['bill_id'], ['insurance_bills.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_insurance_claims_user_id', 'insurance_claims', ['user_id'], unique=False)
    op.create_index('ix_insurance_claims_policy_id', 'insurance_claims', ['policy_id'], unique=False)
    op.create_index('ix_insurance_claims_bill_id', 'insurance_claims', ['bill_id'], unique=False)
    op.create_index('ix_insurance_claims_status', 'insurance_claims', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('insurance_claims')
    op.drop_table('insurance_bills')
    op.drop_table('insurance_policies')
