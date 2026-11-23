"""add profile_photo_path to doctors table

Revision ID: 20261123_06
Revises: 20261115_05
Create Date: 2026-11-23 02:22:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20261123_06'
down_revision: Union[str, None] = '20261115_05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    schema_name = 'clinical' if dialect == 'postgresql' else None

    # Add profile_photo_path column to Doctors table
    op.add_column(
        'Doctors',
        sa.Column('profile_photo_path', sa.String(length=512), nullable=True),
        schema=schema_name,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    schema_name = 'clinical' if dialect == 'postgresql' else None

    op.drop_column('Doctors', 'profile_photo_path', schema=schema_name)
