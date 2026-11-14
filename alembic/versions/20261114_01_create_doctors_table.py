"""create doctors table

Revision ID: 20261114_01
Revises: 
Create Date: 2026-11-14 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision: str = '20261114_01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical schema if not exists
    op.execute(
        "IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'clinical') "
        "EXEC('CREATE SCHEMA [clinical]')"
    )

    # 2. Create Doctors table
    op.create_table(
        'Doctors',
        sa.Column('doctor_id', sa.String(length=64), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('mobile', sa.String(length=32), nullable=False),
        sa.Column('medical_degree', sa.String(length=128), nullable=False),
        sa.Column('registration_number', sa.String(length=64), nullable=False),
        sa.Column('registration_council', sa.String(length=128), nullable=False),
        sa.Column('email_verified', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('verification_status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', mssql.DATETIMEOFFSET(), server_default=sa.text('SYSDATETIMEOFFSET()'), nullable=False),
        sa.Column('document_filename', sa.String(length=256), nullable=True),
        sa.Column('document_path', sa.String(length=512), nullable=True),
        sa.Column('document_uploaded_at', mssql.DATETIMEOFFSET(), nullable=True),
        sa.CheckConstraint("verification_status IN ('PENDING', 'APPROVED', 'REJECTED')", name='CK_Doctors_VerificationStatus'),
        sa.PrimaryKeyConstraint('doctor_id', name='PK_Doctors'),
        sa.UniqueConstraint('email', name='UQ_Doctors_Email'),
        sa.UniqueConstraint('registration_number', name='UQ_Doctors_RegNumber'),
        schema='clinical'
    )

    # 3. Create Indexes
    op.create_index('IX_Doctors_Email', 'Doctors', ['email'], unique=False, schema='clinical')
    op.create_index('IX_Doctors_RegistrationNumber', 'Doctors', ['registration_number'], unique=False, schema='clinical')
    op.create_index('IX_Doctors_VerificationStatus', 'Doctors', ['verification_status'], unique=False, schema='clinical')


def downgrade() -> None:
    op.drop_index('IX_Doctors_VerificationStatus', table_name='Doctors', schema='clinical')
    op.drop_index('IX_Doctors_RegistrationNumber', table_name='Doctors', schema='clinical')
    op.drop_index('IX_Doctors_Email', table_name='Doctors', schema='clinical')
    op.drop_table('Doctors', schema='clinical')
