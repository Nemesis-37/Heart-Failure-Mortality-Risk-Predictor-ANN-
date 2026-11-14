"""create email otp and administrators tables

Revision ID: 20261114_02
Revises: 20261114_01
Create Date: 2026-11-14 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision: str = '20261114_02'
down_revision: Union[str, None] = '20261114_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add verification audit columns to Doctors if not present
    op.add_column('Doctors', sa.Column('verified_at', mssql.DATETIMEOFFSET(), nullable=True), schema='clinical')
    op.add_column('Doctors', sa.Column('verified_by', sa.String(length=64), nullable=True), schema='clinical')
    op.add_column('Doctors', sa.Column('rejection_reason', sa.String(length=512), nullable=True), schema='clinical')

    # 2. Create EmailOTP table
    op.create_table(
        'EmailOTP',
        sa.Column('otp_id', sa.String(length=64), nullable=False),
        sa.Column('doctor_id', sa.String(length=64), nullable=False),
        sa.Column('otp_hash', sa.String(length=256), nullable=False),
        sa.Column('expires_at', mssql.DATETIMEOFFSET(), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', mssql.DATETIMEOFFSET(), server_default=sa.text('SYSDATETIMEOFFSET()'), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['clinical.Doctors.doctor_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('otp_id', name='PK_EmailOTP'),
        schema='clinical'
    )
    op.create_index('IX_EmailOTP_DoctorId', 'EmailOTP', ['doctor_id', 'created_at'], schema='clinical')
    op.create_index('IX_EmailOTP_ExpiresAt', 'EmailOTP', ['expires_at'], schema='clinical')

    # 3. Create Administrators table
    op.create_table(
        'Administrators',
        sa.Column('admin_id', sa.String(length=64), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=64), server_default='Medical Credentialing Officer', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', mssql.DATETIMEOFFSET(), server_default=sa.text('SYSDATETIMEOFFSET()'), nullable=False),
        sa.PrimaryKeyConstraint('admin_id', name='PK_Administrators'),
        sa.UniqueConstraint('username', name='UQ_Admin_Username'),
        sa.UniqueConstraint('email', name='UQ_Admin_Email'),
        schema='clinical'
    )
    op.create_index('IX_Admin_Email', 'Administrators', ['email'], schema='clinical')


def downgrade() -> None:
    op.drop_index('IX_Admin_Email', table_name='Administrators', schema='clinical')
    op.drop_table('Administrators', schema='clinical')
    op.drop_index('IX_EmailOTP_ExpiresAt', table_name='EmailOTP', schema='clinical')
    op.drop_index('IX_EmailOTP_DoctorId', table_name='EmailOTP', schema='clinical')
    op.drop_table('EmailOTP', schema='clinical')
    op.drop_column('Doctors', 'rejection_reason', schema='clinical')
    op.drop_column('Doctors', 'verified_by', schema='clinical')
    op.drop_column('Doctors', 'verified_at', schema='clinical')
