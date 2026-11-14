"""create doctor sessions table

Revision ID: 20261114_03
Revises: 20261114_02
Create Date: 2026-11-14 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision: str = '20261114_03'
down_revision: Union[str, None] = '20261114_02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'DoctorSessions',
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('doctor_id', sa.String(length=64), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=256), nullable=False),
        sa.Column('expires_at', mssql.DATETIMEOFFSET(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', mssql.DATETIMEOFFSET(), server_default=sa.text('SYSDATETIMEOFFSET()'), nullable=False),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['clinical.Doctors.doctor_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id', name='PK_DoctorSessions'),
        schema='clinical'
    )
    op.create_index('IX_DoctorSessions_DoctorId', 'DoctorSessions', ['doctor_id', 'created_at'], schema='clinical')
    op.create_index('IX_DoctorSessions_ExpiresAt', 'DoctorSessions', ['expires_at'], schema='clinical')


def downgrade() -> None:
    op.drop_index('IX_DoctorSessions_ExpiresAt', table_name='DoctorSessions', schema='clinical')
    op.drop_index('IX_DoctorSessions_DoctorId', table_name='DoctorSessions', schema='clinical')
    op.drop_table('DoctorSessions', schema='clinical')
