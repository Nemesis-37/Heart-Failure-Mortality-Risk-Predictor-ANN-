"""add username, last_login, approved_at to doctors table

Revision ID: 20261115_05
Revises: 20261114_04
Create Date: 2026-11-15 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261115_05'
down_revision: Union[str, None] = '20261114_04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add username, last_login, approved_at to Doctors
    op.add_column('Doctors', sa.Column('username', sa.String(length=64), nullable=True))
    op.create_unique_constraint('UQ_Doctors_Username', 'Doctors', ['username'])
    op.add_column('Doctors', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('Doctors', sa.Column('approved_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('Doctors', 'approved_at')
    op.drop_column('Doctors', 'last_login')
    op.drop_constraint('UQ_Doctors_Username', 'Doctors', type_='unique')
    op.drop_column('Doctors', 'username')
