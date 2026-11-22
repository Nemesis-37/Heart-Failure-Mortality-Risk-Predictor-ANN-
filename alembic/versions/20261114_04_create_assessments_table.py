"""create assessments and predictions tables

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
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        dt_type = sa.TIMESTAMP(timezone=True)
        now_def = sa.text('CURRENT_TIMESTAMP')
        b_false = sa.text('false')
    else:
        dt_type = sa.DateTime()
        now_def = sa.text('CURRENT_TIMESTAMP')
        b_false = sa.text('0')

    # 1. Create Assessments table
    op.create_table(
        'Assessments',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('assessment_code', sa.String(length=32), nullable=False),
        sa.Column('patient_reference_id', sa.String(length=64), nullable=True),
        sa.Column('doctor_id', sa.String(length=64), nullable=True),
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
        sa.Column('prediction_timestamp', dt_type, nullable=True),
        sa.Column('is_prediction_stale', sa.Boolean(), server_default=b_false, nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', dt_type, server_default=now_def, nullable=False),
        sa.Column('updated_at', dt_type, server_default=now_def, nullable=False),
        sa.CheckConstraint('age >= 1.0 AND age <= 120.0', name='CK_Assessments_Age'),
        sa.CheckConstraint('anaemia IN (0, 1)', name='CK_Assessments_Anaemia'),
        sa.CheckConstraint('creatinine_phosphokinase > 0.0 AND creatinine_phosphokinase <= 20000.0', name='CK_Assessments_CPK'),
        sa.CheckConstraint('diabetes IN (0, 1)', name='CK_Assessments_Diabetes'),
        sa.CheckConstraint('ejection_fraction >= 1.0 AND ejection_fraction <= 100.0', name='CK_Assessments_EF'),
        sa.CheckConstraint('high_blood_pressure IN (0, 1)', name='CK_Assessments_HBP'),
        sa.CheckConstraint('platelets > 0.0 AND platelets <= 2000000.0', name='CK_Assessments_Platelets'),
        sa.CheckConstraint('serum_creatinine >= 0.1 AND serum_creatinine <= 30.0', name='CK_Assessments_Creatinine'),
        sa.CheckConstraint('serum_sodium >= 50.0 AND serum_sodium <= 200.0', name='CK_Assessments_Sodium'),
        sa.CheckConstraint('sex IN (0, 1)', name='CK_Assessments_Sex'),
        sa.CheckConstraint('smoking IN (0, 1)', name='CK_Assessments_Smoking'),
        sa.CheckConstraint('predicted_class IS NULL OR predicted_class IN (0, 1)', name='CK_Assessments_PredictedClass'),
        sa.CheckConstraint('predicted_probability IS NULL OR (predicted_probability >= 0.0 AND predicted_probability <= 1.0)', name='CK_Assessments_PredictedProb'),
        sa.ForeignKeyConstraint(['doctor_id'], ['clinical.Doctors.doctor_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='PK_Assessments'),
        sa.UniqueConstraint('assessment_code', name='UQ_Assessments_Code'),
        schema='clinical'
    )
    op.create_index('IX_Assessments_DoctorId', 'Assessments', ['doctor_id', 'created_at'], schema='clinical')
    op.create_index('IX_Assessments_PatientRef', 'Assessments', ['patient_reference_id'], schema='clinical')
    op.create_index('IX_Assessments_CreatedAt', 'Assessments', ['created_at'], schema='clinical')

    # 2. Create Predictions table
    op.create_table(
        'Predictions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('prediction_code', sa.String(length=32), nullable=False),
        sa.Column('assessment_id', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('predicted_class', sa.SmallInteger(), nullable=False),
        sa.Column('predicted_probability', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('classification_threshold', sa.Numeric(precision=4, scale=2), server_default='0.50', nullable=False),
        sa.Column('model_version', sa.String(length=32), server_default='v1.0.0', nullable=False),
        sa.Column('created_at', dt_type, server_default=now_def, nullable=False),
        sa.CheckConstraint('predicted_class IN (0, 1)', name='CK_Predictions_Class'),
        sa.CheckConstraint('predicted_probability >= 0.0 AND predicted_probability <= 1.0', name='CK_Predictions_Prob'),
        sa.ForeignKeyConstraint(['assessment_id'], ['clinical.Assessments.id'], ondelete='CASCADE', name='FK_Predictions_Assessments'),
        sa.PrimaryKeyConstraint('id', name='PK_Predictions'),
        sa.UniqueConstraint('prediction_code', name='UQ_Predictions_Code'),
        schema='clinical'
    )
    op.create_index('IX_Predictions_AssessmentId', 'Predictions', ['assessment_id', 'created_at'], schema='clinical')
    op.create_index('IX_Predictions_CreatedAt', 'Predictions', ['created_at'], schema='clinical')


def downgrade() -> None:
    op.drop_index('IX_Predictions_CreatedAt', table_name='Predictions', schema='clinical')
    op.drop_index('IX_Predictions_AssessmentId', table_name='Predictions', schema='clinical')
    op.drop_table('Predictions', schema='clinical')
    op.drop_index('IX_Assessments_CreatedAt', table_name='Assessments', schema='clinical')
    op.drop_index('IX_Assessments_PatientRef', table_name='Assessments', schema='clinical')
    op.drop_index('IX_Assessments_DoctorId', table_name='Assessments', schema='clinical')
    op.drop_table('Assessments', schema='clinical')
