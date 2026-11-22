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
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "mssql":
        dt_type = sa.DateTime()
    elif dialect == "postgresql":
        dt_type = sa.TIMESTAMP(timezone=True)
    else:
        dt_type = sa.DateTime()

    # Add username, last_login, approved_at to Doctors
    op.add_column('Doctors', sa.Column('username', sa.String(length=64), nullable=True), schema='clinical')
    op.create_index(
        'UQ_Doctors_Username',
        'Doctors',
        ['username'],
        unique=True,
        postgresql_where=sa.text('username IS NOT NULL'),
        mssql_where=sa.text('username IS NOT NULL'),
        sqlite_where=sa.text('username IS NOT NULL'),
        schema='clinical'
    )
    op.add_column('Doctors', sa.Column('last_login', dt_type, nullable=True), schema='clinical')
    op.add_column('Doctors', sa.Column('approved_at', dt_type, nullable=True), schema='clinical')


def downgrade() -> None:
    op.drop_column('Doctors', 'approved_at', schema='clinical')
    op.drop_column('Doctors', 'last_login', schema='clinical')
    op.drop_index('UQ_Doctors_Username', table_name='Doctors', schema='clinical')
    op.drop_column('Doctors', 'username', schema='clinical')
