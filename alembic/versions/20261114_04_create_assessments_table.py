"""create assessments table

Revision ID: 20261114_04
Revises: 20261114_03
Create Date: 2026-11-15 02:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20261114_04'
down_revision: Union[str, None] = '20261114_03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'Assessments',
        sa.Column('assessment_id', sa.String(length=64), nullable=False),
        sa.Column('doctor_id', sa.String(length=64), nullable=False),
        sa.Column('patient_reference', sa.String(length=64), nullable=True),
        sa.Column('age', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('anaemia', sa.SmallInteger(), nullable=False),
        sa.Column('creatinine_phosphokinase', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('diabetes', sa.SmallInteger(), nullable=False),
        sa.Column('ejection_fraction', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('high_blood_pressure', sa.SmallInteger(), nullable=False),
        sa.Column('platelets', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('serum_creatinine', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('serum_sodium', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('sex', sa.SmallInteger(), nullable=False),
        sa.Column('smoking', sa.SmallInteger(), nullable=False),
        sa.Column('selected_model', sa.String(length=64), nullable=True),
        sa.Column('predicted_class', sa.SmallInteger(), nullable=True),
        sa.Column('predicted_probability', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('age > 0', name='CK_Assessments_Age_Positive'),
        sa.CheckConstraint('anaemia IN (0, 1)', name='CK_Assessments_Anaemia_Binary'),
        sa.CheckConstraint('diabetes IN (0, 1)', name='CK_Assessments_Diabetes_Binary'),
        sa.CheckConstraint('high_blood_pressure IN (0, 1)', name='CK_Assessments_HBP_Binary'),
        sa.CheckConstraint('sex IN (0, 1)', name='CK_Assessments_Sex_Binary'),
        sa.CheckConstraint('smoking IN (0, 1)', name='CK_Assessments_Smoking_Binary'),
        sa.ForeignKeyConstraint(['doctor_id'], ['Doctors.doctor_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assessment_id', name='PK_Assessments'),
    )
    op.create_index('IX_Assessments_DoctorId_CreatedAt', 'Assessments', ['doctor_id', 'created_at'])
    op.create_index('IX_Assessments_PatientReference', 'Assessments', ['patient_reference'])


def downgrade() -> None:
    op.drop_index('IX_Assessments_PatientReference', table_name='Assessments')
    op.drop_index('IX_Assessments_DoctorId_CreatedAt', table_name='Assessments')
    op.drop_table('Assessments')
