"""
clinical/router.py
==================
Physician-protected API endpoints for Patient Assessments, Prediction History,
and Clinical Analytics Dashboard.

Security Architecture (IDOR Prevention):
- Every endpoint requires `current_doctor = Depends(get_current_doctor)`.
- Data queries strictly enforce `Assessment.doctor_id == current_doctor.doctor_id`.
- Doctors cannot access, view, or modify other physicians' patient records.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.dependencies import get_current_doctor
from database.config import get_db
from database.models import Assessment, Doctor, Prediction

router = APIRouter(prefix="/api", tags=["Protected Clinical Data"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AssessmentInput(BaseModel):
    patient_reference_id: Optional[str] = Field(None, max_length=64)
    age: float = Field(..., ge=1, le=120)
    anaemia: int = Field(..., ge=0, le=1)
    creatinine_phosphokinase: float = Field(..., gt=0, le=20000)
    diabetes: int = Field(..., ge=0, le=1)
    ejection_fraction: float = Field(..., ge=1, le=100)
    high_blood_pressure: int = Field(..., ge=0, le=1)
    platelets: float = Field(..., gt=0, le=2000000)
    serum_creatinine: float = Field(..., ge=0.1, le=30.0)
    serum_sodium: float = Field(..., ge=50.0, le=200.0)
    sex: int = Field(..., ge=0, le=1)
    smoking: int = Field(..., ge=0, le=1)


class AssessmentOut(BaseModel):
    id: str
    assessment_code: str
    patient_reference_id: Optional[str] = None
    doctor_id: str
    age: float
    anaemia: int
    creatinine_phosphokinase: float
    diabetes: int
    ejection_fraction: float
    high_blood_pressure: int
    platelets: float
    serum_creatinine: float
    serum_sodium: float
    sex: int
    smoking: int
    selected_model: Optional[str] = None
    predicted_class: Optional[int] = None
    predicted_probability: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PredictionOut(BaseModel):
    id: str
    prediction_code: str
    assessment_id: str
    assessment_code: Optional[str] = None
    patient_reference_id: Optional[str] = None
    model_name: str
    predicted_class: int
    predicted_probability: float
    classification_threshold: float
    model_version: str
    created_at: datetime


class DashboardStatsOut(BaseModel):
    total_assessments: int
    total_predictions: int
    ann_predictions: int
    lr_predictions: int
    most_recent_prediction: Optional[PredictionOut] = None


# ---------------------------------------------------------------------------
# Patient Assessments Endpoints (IDOR Protected)
# ---------------------------------------------------------------------------

@router.get(
    "/assessments",
    response_model=List[AssessmentOut],
    summary="List patient assessments for current authenticated doctor",
)
def list_doctor_assessments(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns only patient assessments entered by the currently signed-in doctor.
    Enforces strict ownership check.
    """
    records = (
        db.query(Assessment)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
        .order_by(Assessment.created_at.desc())
        .all()
    )

    return [
        AssessmentOut(
            id=str(r.id),
            assessment_code=r.assessment_code,
            patient_reference_id=r.patient_reference_id,
            doctor_id=str(r.doctor_id),
            age=float(r.age),
            anaemia=int(r.anaemia),
            creatinine_phosphokinase=float(r.creatinine_phosphokinase),
            diabetes=int(r.diabetes),
            ejection_fraction=float(r.ejection_fraction),
            high_blood_pressure=int(r.high_blood_pressure),
            platelets=float(r.platelets),
            serum_creatinine=float(r.serum_creatinine),
            serum_sodium=float(r.serum_sodium),
            sex=int(r.sex),
            smoking=int(r.smoking),
            selected_model=r.selected_model,
            predicted_class=r.predicted_class,
            predicted_probability=float(r.predicted_probability) if r.predicted_probability is not None else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentOut,
    summary="Get single assessment details (IDOR Protected)",
)
def get_assessment_by_id(
    assessment_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Retrieve single assessment.
    Prevents IDOR: If assessment belongs to another doctor, access is denied (HTTP 403).
    """
    record = (
        db.query(Assessment)
        .filter(
            (Assessment.id == assessment_id) | (Assessment.assessment_code == assessment_id)
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found.",
        )

    # Strict IDOR ownership check
    if record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to view another physician's patient record.",
        )

    return AssessmentOut(
        id=str(record.id),
        assessment_code=record.assessment_code,
        patient_reference_id=record.patient_reference_id,
        doctor_id=str(record.doctor_id),
        age=float(record.age),
        anaemia=int(record.anaemia),
        creatinine_phosphokinase=float(record.creatinine_phosphokinase),
        diabetes=int(record.diabetes),
        ejection_fraction=float(record.ejection_fraction),
        high_blood_pressure=int(record.high_blood_pressure),
        platelets=float(record.platelets),
        serum_creatinine=float(record.serum_creatinine),
        serum_sodium=float(record.serum_sodium),
        sex=int(record.sex),
        smoking=int(record.smoking),
        selected_model=record.selected_model,
        predicted_class=record.predicted_class,
        predicted_probability=float(record.predicted_probability) if record.predicted_probability is not None else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/assessments",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new patient clinical assessment",
)
def create_patient_assessment(
    payload: AssessmentInput,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Save an assessment record bound to the current physician's ID."""
    now = datetime.now(timezone.utc)
    # Count doctor's assessments to generate code
    count = db.query(Assessment).filter(Assessment.doctor_id == current_doctor.doctor_id).count() + 1
    code = f"ASM-2026-{str(count).padStart(4, '0')}" if hasattr(str, 'padStart') else f"ASM-2026-{count:04d}"

    assessment = Assessment(
        id=str(uuid.uuid4()),
        assessment_code=code,
        patient_reference_id=payload.patient_reference_id.strip() if payload.patient_reference_id else None,
        doctor_id=current_doctor.doctor_id,
        age=payload.age,
        anaemia=payload.anaemia,
        creatinine_phosphokinase=payload.creatinine_phosphokinase,
        diabetes=payload.diabetes,
        ejection_fraction=payload.ejection_fraction,
        high_blood_pressure=payload.high_blood_pressure,
        platelets=payload.platelets,
        serum_creatinine=payload.serum_creatinine,
        serum_sodium=payload.serum_sodium,
        sex=payload.sex,
        smoking=payload.smoking,
        version=1,
        created_at=now,
        updated_at=now,
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return AssessmentOut(
        id=str(assessment.id),
        assessment_code=assessment.assessment_code,
        patient_reference_id=assessment.patient_reference_id,
        doctor_id=str(assessment.doctor_id),
        age=float(assessment.age),
        anaemia=int(assessment.anaemia),
        creatinine_phosphokinase=float(assessment.creatinine_phosphokinase),
        diabetes=int(assessment.diabetes),
        ejection_fraction=float(assessment.ejection_fraction),
        high_blood_pressure=int(assessment.high_blood_pressure),
        platelets=float(assessment.platelets),
        serum_creatinine=float(assessment.serum_creatinine),
        serum_sodium=float(assessment.serum_sodium),
        sex=int(assessment.sex),
        smoking=int(assessment.smoking),
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
    )


@router.put(
    "/assessments/{assessment_id}",
    response_model=AssessmentOut,
    summary="Update patient assessment (IDOR Protected)",
)
def update_patient_assessment(
    assessment_id: str,
    payload: AssessmentInput,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Update assessment if owned by current doctor. Blocks IDOR (HTTP 403)."""
    record = (
        db.query(Assessment)
        .filter((Assessment.id == assessment_id) | (Assessment.assessment_code == assessment_id))
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    if record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to modify another physician's record.",
        )

    for field, val in payload.model_dump().items():
        setattr(record, field, val)

    record.updated_at = datetime.now(timezone.utc)
    record.version = (record.version or 1) + 1
    db.commit()
    db.refresh(record)
    return AssessmentOut(
        id=str(record.id),
        assessment_code=record.assessment_code,
        patient_reference_id=record.patient_reference_id,
        doctor_id=str(record.doctor_id),
        age=float(record.age),
        anaemia=int(record.anaemia),
        creatinine_phosphokinase=float(record.creatinine_phosphokinase),
        diabetes=int(record.diabetes),
        ejection_fraction=float(record.ejection_fraction),
        high_blood_pressure=int(record.high_blood_pressure),
        platelets=float(record.platelets),
        serum_creatinine=float(record.serum_creatinine),
        serum_sodium=float(record.serum_sodium),
        sex=int(record.sex),
        smoking=int(record.smoking),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete(
    "/assessments/{assessment_id}",
    summary="Delete patient assessment (IDOR Protected)",
)
def delete_patient_assessment(
    assessment_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Delete assessment if owned by current doctor. Blocks IDOR (HTTP 403)."""
    record = (
        db.query(Assessment)
        .filter((Assessment.id == assessment_id) | (Assessment.assessment_code == assessment_id))
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    if record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to delete another physician's record.",
        )

    db.delete(record)
    db.commit()
    return {"status": "success", "message": f"Assessment {record.assessment_code} deleted."}


# ---------------------------------------------------------------------------
# Prediction History Endpoints (IDOR Protected)
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=List[PredictionOut],
    summary="List prediction history for current doctor",
)
def list_prediction_history(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns predictions generated by the current doctor.
    Joins on Assessment to verify doctor_id ownership.
    """
    results = (
        db.query(Prediction, Assessment)
        .join(Assessment, Prediction.assessment_id == Assessment.id)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )

    return [
        PredictionOut(
            id=str(pred.id),
            prediction_code=pred.prediction_code,
            assessment_id=str(pred.assessment_id),
            assessment_code=asm.assessment_code,
            patient_reference_id=asm.patient_reference_id,
            model_name=pred.model_name,
            predicted_class=pred.predicted_class,
            predicted_probability=float(pred.predicted_probability),
            classification_threshold=float(pred.classification_threshold),
            model_version=pred.model_version,
            created_at=pred.created_at,
        )
        for pred, asm in results
    ]


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsOut,
    summary="Doctor personal dashboard metrics",
)
def get_doctor_dashboard_stats(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """Calculate real personal clinical statistics for current physician."""
    total_assessments = (
        db.query(Assessment)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
        .count()
    )

    preds_query = (
        db.query(Prediction)
        .join(Assessment, Prediction.assessment_id == Assessment.id)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
    )

    total_predictions = preds_query.count()
    ann_predictions = preds_query.filter(Prediction.model_name.like("%Neural%")).count()
    lr_predictions = preds_query.filter(Prediction.model_name.like("%Logistic%")).count()

    latest_tuple = preds_query.order_by(Prediction.created_at.desc()).first()
    recent_pred_out = None
    if latest_tuple:
        parent_asm = db.query(Assessment).filter(Assessment.id == latest_tuple.assessment_id).first()
        recent_pred_out = PredictionOut(
            id=str(latest_tuple.id),
            prediction_code=latest_tuple.prediction_code,
            assessment_id=str(latest_tuple.assessment_id),
            assessment_code=parent_asm.assessment_code if parent_asm else None,
            patient_reference_id=parent_asm.patient_reference_id if parent_asm else None,
            model_name=latest_tuple.model_name,
            predicted_class=latest_tuple.predicted_class,
            predicted_probability=float(latest_tuple.predicted_probability),
            classification_threshold=float(latest_tuple.classification_threshold),
            model_version=latest_tuple.model_version,
            created_at=latest_tuple.created_at,
        )

    return DashboardStatsOut(
        total_assessments=total_assessments,
        total_predictions=total_predictions,
        ann_predictions=ann_predictions,
        lr_predictions=lr_predictions,
        most_recent_prediction=recent_pred_out,
    )
