"""
clinical/router.py
==================
Physician-protected API endpoints for:
1. Patient Assessment Management (CRUD, validation, pagination, search, IDOR protection)
2. Doctor Clinical Dashboard & Analytics (summary, recent assessments, recent predictions, distribution, model usage)
3. Prediction History & Clinical Stats

Security Architecture (IDOR & Impersonation Prevention):
- Every endpoint requires `current_doctor = Depends(get_current_doctor)`.
- Never trust doctor_id submitted by client; doctor_id is strictly derived from verified token.
- Queries enforce `Assessment.doctor_id == current_doctor.doctor_id`.
- Returns HTTP 404 when an assessment is not found or does not belong to the requesting doctor,
  preventing ID enumeration and cross-doctor information leakage.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.dependencies import get_current_doctor
try:
    from database.models import Doctor, Assessment
except ImportError:
    from db_models import Doctor, Assessment

try:
    from database.models import Prediction
except ImportError:
    Prediction = None

try:
    from database import get_db
except ImportError:
    from database.config import get_db

router = APIRouter(tags=["Patient Assessments & Clinical Dashboard"])


# ---------------------------------------------------------------------------
# Pydantic Schemas for Validation and Serialization
# ---------------------------------------------------------------------------

class AssessmentInput(BaseModel):
    """
    Validation schema for creating or updating patient assessments.
    Enforces all 11 model features, strict binary fields, and positive age.
    Does not collect patient personal identifiable information.
    """
    patient_reference: Optional[str] = Field(None, max_length=64, description="Optional patient reference ID")
    patient_reference_id: Optional[str] = Field(None, max_length=64, description="Alias for patient_reference")
    
    # 11 clinical features (UCI Heart Failure dataset without 'time')
    age: float = Field(..., gt=0, le=130, description="Patient age (positive numeric)")
    anaemia: int = Field(..., ge=0, le=1, description="0 = No, 1 = Yes")
    creatinine_phosphokinase: float = Field(..., gt=0, description="CPK enzyme level (mcg/L)")
    diabetes: int = Field(..., ge=0, le=1, description="0 = No, 1 = Yes")
    ejection_fraction: float = Field(..., gt=0, le=100, description="Ejection fraction percentage")
    high_blood_pressure: int = Field(..., ge=0, le=1, description="0 = No, 1 = Yes")
    platelets: float = Field(..., gt=0, description="Platelets count (kiloplatelets/mL)")
    serum_creatinine: float = Field(..., gt=0, description="Serum creatinine level (mg/dL)")
    serum_sodium: float = Field(..., gt=0, description="Serum sodium level (mEq/L)")
    sex: int = Field(..., ge=0, le=1, description="0 = Female, 1 = Male")
    smoking: int = Field(..., ge=0, le=1, description="0 = No, 1 = Yes")

    @model_validator(mode="before")
    @classmethod
    def sync_patient_reference(cls, data):
        if isinstance(data, dict):
            if "patient_reference" in data and "patient_reference_id" not in data:
                data["patient_reference_id"] = data["patient_reference"]
            elif "patient_reference_id" in data and "patient_reference" not in data:
                data["patient_reference"] = data["patient_reference_id"]
        return data


class AssessmentOut(BaseModel):
    """Full assessment response matching both step specifications and existing frontend."""
    assessment_id: str
    id: str
    doctor_id: str
    patient_reference: Optional[str] = None
    patient_reference_id: Optional[str] = None
    assessment_code: Optional[str] = None
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


class DashboardSummaryOut(BaseModel):
    total_assessments: int
    total_predictions: int
    logistic_regression_predictions: int
    ann_predictions: int
    class_0_predictions: int
    class_1_predictions: int


class RecentAssessmentOut(BaseModel):
    assessment_id: str
    patient_reference: Optional[str] = None
    created_at: datetime
    prediction_count: int


class RecentPredictionOut(BaseModel):
    prediction_id: str
    assessment_id: str
    model_name: str
    predicted_class: int
    predicted_label: str
    predicted_probability: float
    created_at: datetime


class PredictionDistributionOut(BaseModel):
    model: str
    class_0_count: int
    class_1_count: int
    class_0_label: str = "No death event predicted"
    class_1_label: str = "Death event predicted"
    notice: str = "These counts represent model inference outputs, not confirmed clinical diagnoses."


class ModelUsageOut(BaseModel):
    logistic_regression: int
    ann: int
    total: int


class DashboardStatsOut(BaseModel):
    total_assessments: int
    total_predictions: int
    ann_predictions: int
    lr_predictions: int
    most_recent_prediction: Optional[PredictionOut] = None


# ---------------------------------------------------------------------------
# Model Compatibility Helpers
# ---------------------------------------------------------------------------

def _assessment_pk_col():
    """Return the PK column of Assessment (id or assessment_id depending on model)."""
    cols = {c.name for c in Assessment.__table__.columns}
    return Assessment.id if "id" in cols else Assessment.assessment_id


def _assessment_ref_col():
    """Return the patient reference column of Assessment."""
    cols = {c.name for c in Assessment.__table__.columns}
    return Assessment.patient_reference_id if "patient_reference_id" in cols else Assessment.patient_reference


def _get_assessment_id(record) -> str:
    """Get the PK value from an Assessment record."""
    return str(getattr(record, "id", None) or getattr(record, "assessment_id", ""))


def _get_patient_ref(record):
    """Get patient reference value from an Assessment record."""
    return getattr(record, "patient_reference_id", None) or getattr(record, "patient_reference", None)


# ---------------------------------------------------------------------------
# Helper Serializer
# ---------------------------------------------------------------------------

def _serialize_assessment(r) -> AssessmentOut:
    asm_id = _get_assessment_id(r)
    pat_ref = _get_patient_ref(r)
    code = getattr(r, "assessment_code", None) or f"ASM-{asm_id[:8].upper()}"

    prob = getattr(r, "predicted_probability", None)
    if prob is not None:
        try:
            prob = float(prob)
        except (ValueError, TypeError):
            prob = None

    return AssessmentOut(
        assessment_id=asm_id,
        id=asm_id,
        doctor_id=str(r.doctor_id),
        patient_reference=pat_ref,
        patient_reference_id=pat_ref,
        assessment_code=code,
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
        selected_model=getattr(r, "selected_model", None),
        predicted_class=getattr(r, "predicted_class", None),
        predicted_probability=prob,
        created_at=r.created_at,
        updated_at=getattr(r, "updated_at", r.created_at),
    )


# ---------------------------------------------------------------------------
# Patient Assessments Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/assessments",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient assessment",
)
def create_patient_assessment(
    payload: AssessmentInput,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Create a new clinical assessment with all 11 model features.
    Automatically links to authenticated doctor.
    """
    now = datetime.now(timezone.utc)
    ref = payload.patient_reference or payload.patient_reference_id
    if ref:
        ref = ref.strip()

    asm_id = str(uuid.uuid4())

    # Build kwargs compatible with both db_models.Assessment and database.models.Assessment
    _asm_kwargs = {
        "doctor_id": current_doctor.doctor_id,
        "age": payload.age,
        "anaemia": payload.anaemia,
        "creatinine_phosphokinase": payload.creatinine_phosphokinase,
        "diabetes": payload.diabetes,
        "ejection_fraction": payload.ejection_fraction,
        "high_blood_pressure": payload.high_blood_pressure,
        "platelets": payload.platelets,
        "serum_creatinine": payload.serum_creatinine,
        "serum_sodium": payload.serum_sodium,
        "sex": payload.sex,
        "smoking": payload.smoking,
        "created_at": now,
        "updated_at": now,
    }
    # Set ID field — database.models uses "id", db_models uses "assessment_id"
    _cols = {c.name for c in Assessment.__table__.columns}
    if "id" in _cols:
        _asm_kwargs["id"] = asm_id
    else:
        _asm_kwargs["assessment_id"] = asm_id
    # Set patient reference field
    if "patient_reference_id" in _cols:
        _asm_kwargs["patient_reference_id"] = ref
    elif "patient_reference" in _cols:
        _asm_kwargs["patient_reference"] = ref
    # Set assessment_code if the model supports it
    if "assessment_code" in _cols:
        _asm_kwargs["assessment_code"] = f"ASM-{asm_id[:8].upper()}"

    assessment = Assessment(**_asm_kwargs)

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return _serialize_assessment(assessment)


@router.get(
    "/assessments",
    response_model=List[AssessmentOut],
    summary="List patient assessments for current authenticated doctor",
)
def list_doctor_assessments(
    page: int = 1,
    limit: int = 20,
    patient_reference: Optional[str] = None,
    search: Optional[str] = None,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns only assessments belonging to the authenticated physician.
    Supports pagination, searching by patient reference, and sorts newest first.
    """
    if not isinstance(page, int) or page < 1:
        page = 1
    if not isinstance(limit, int) or limit < 1:
        limit = 20

    query = db.query(Assessment).filter(Assessment.doctor_id == current_doctor.doctor_id)

    search_term = None
    if isinstance(patient_reference, str):
        search_term = patient_reference
    elif isinstance(search, str):
        search_term = search

    if search_term and search_term.strip():
        term = f"%{search_term.strip()}%"
        ref_col = _assessment_ref_col()
        query = query.filter(ref_col.ilike(term))

    records = (
        query.order_by(Assessment.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return [_serialize_assessment(r) for r in records]


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
    Retrieve one assessment by ID.
    Enforces doctor ownership. Returns HTTP 404 if record does not exist or
    belongs to another physician (preventing ID enumeration).
    """
    record = (
        db.query(Assessment)
        .filter(_assessment_pk_col() == assessment_id)
        .first()
    )

    if not record or record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found.",
        )

    return _serialize_assessment(record)


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
    """
    Update clinical parameters for an existing assessment.
    Returns HTTP 404 if not found or not owned by requesting doctor.
    """
    record = (
        db.query(Assessment)
        .filter(_assessment_pk_col() == assessment_id)
        .first()
    )

    if not record or record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found.",
        )

    # Update clinical input features
    record.age = payload.age
    record.anaemia = payload.anaemia
    record.creatinine_phosphokinase = payload.creatinine_phosphokinase
    record.diabetes = payload.diabetes
    record.ejection_fraction = payload.ejection_fraction
    record.high_blood_pressure = payload.high_blood_pressure
    record.platelets = payload.platelets
    record.serum_creatinine = payload.serum_creatinine
    record.serum_sodium = payload.serum_sodium
    record.sex = payload.sex
    record.smoking = payload.smoking

    ref = payload.patient_reference or payload.patient_reference_id
    _cols = {c.name for c in Assessment.__table__.columns}
    if "patient_reference_id" in _cols:
        record.patient_reference_id = ref.strip() if ref else None
    elif "patient_reference" in _cols:
        record.patient_reference = ref.strip() if ref else None

    if hasattr(record, "updated_at"):
        record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)

    return _serialize_assessment(record)


@router.delete(
    "/assessments/{assessment_id}",
    summary="Delete patient assessment (IDOR Protected)",
)
def delete_patient_assessment(
    assessment_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Delete patient assessment record.
    Returns HTTP 404 if not found or not owned by requesting doctor.
    """
    record = (
        db.query(Assessment)
        .filter(_assessment_pk_col() == assessment_id)
        .first()
    )

    if not record or record.doctor_id != current_doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found.",
        )

    db.delete(record)
    db.commit()

    return {
        "status": "success",
        "message": f"Assessment {assessment_id} deleted successfully.",
        "assessment_id": assessment_id,
    }


# ---------------------------------------------------------------------------
# Backend Dashboard & Analytics APIs
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryOut,
    summary="Get aggregated statistics for logged-in physician",
)
def get_dashboard_summary(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns real statistics retrieved from SQL database for authenticated doctor.
    No hardcoded or fabricated statistics.
    """
    total_assessments = (
        db.query(Assessment)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
        .count()
    )

    total_preds = 0
    lr_preds = 0
    ann_preds = 0
    class_0 = 0
    class_1 = 0

    if Prediction is not None:
        try:
            preds_q = (
                db.query(Prediction)
                .join(Assessment, Prediction.assessment_id == _assessment_pk_col())
                .filter(Assessment.doctor_id == current_doctor.doctor_id)
            )
            total_preds = preds_q.count()
            lr_preds = preds_q.filter(Prediction.model_name.ilike("%logistic%")).count()
            ann_preds = preds_q.filter(or_(Prediction.model_name.ilike("%neural%"), Prediction.model_name.ilike("%ann%"))).count()
            class_0 = preds_q.filter(Prediction.predicted_class == 0).count()
            class_1 = preds_q.filter(Prediction.predicted_class == 1).count()
        except Exception:
            pass

    # If predictions are tracked on Assessment table itself
    if total_preds == 0:
        asm_preds = db.query(Assessment).filter(
            Assessment.doctor_id == current_doctor.doctor_id,
            Assessment.predicted_class != None,
        )
        total_preds = asm_preds.count()
        class_0 = asm_preds.filter(Assessment.predicted_class == 0).count()
        class_1 = asm_preds.filter(Assessment.predicted_class == 1).count()
        lr_preds = asm_preds.filter(Assessment.selected_model.ilike("%logistic%")).count()
        ann_preds = asm_preds.filter(or_(Assessment.selected_model.ilike("%neural%"), Assessment.selected_model.ilike("%ann%"))).count()

    return DashboardSummaryOut(
        total_assessments=total_assessments,
        total_predictions=total_preds,
        logistic_regression_predictions=lr_preds,
        ann_predictions=ann_preds,
        class_0_predictions=class_0,
        class_1_predictions=class_1,
    )


@router.get(
    "/dashboard/recent-assessments",
    response_model=List[RecentAssessmentOut],
    summary="Get latest five assessments belonging to logged-in doctor",
)
def get_dashboard_recent_assessments(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns latest five assessments with prediction count.
    """
    latest_asms = (
        db.query(Assessment)
        .filter(Assessment.doctor_id == current_doctor.doctor_id)
        .order_by(Assessment.created_at.desc())
        .limit(5)
        .all()
    )

    results = []
    for a in latest_asms:
        asm_id = str(getattr(a, "assessment_id", getattr(a, "id", "")))
        pat_ref = getattr(a, "patient_reference", getattr(a, "patient_reference_id", None))

        pred_count = 0
        if Prediction is not None:
            try:
                pred_count = db.query(Prediction).filter(
                    or_(
                        Prediction.assessment_id == asm_id,
                        getattr(Prediction, "assessment_code", None) == getattr(a, "assessment_code", None),
                    )
                ).count()
            except Exception:
                pass
        if pred_count == 0 and getattr(a, "predicted_class", None) is not None:
            pred_count = 1

        results.append(
            RecentAssessmentOut(
                assessment_id=asm_id,
                patient_reference=pat_ref,
                created_at=a.created_at,
                prediction_count=pred_count,
            )
        )

    return results


@router.get(
    "/dashboard/recent-predictions",
    response_model=List[RecentPredictionOut],
    summary="Get latest five predictions belonging to logged-in doctor",
)
def get_dashboard_recent_predictions(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns latest five model predictions with probability and labels.
    """
    recent_preds = []

    if Prediction is not None:
        try:
            preds = (
                db.query(Prediction, Assessment)
                .join(Assessment, Prediction.assessment_id == getattr(Assessment, "assessment_id", getattr(Assessment, "id", None)))
                .filter(Assessment.doctor_id == current_doctor.doctor_id)
                .order_by(Prediction.created_at.desc())
                .limit(5)
                .all()
            )
            for p, a in preds:
                p_id = str(getattr(p, "prediction_id", getattr(p, "id", "")))
                asm_id = str(getattr(a, "assessment_id", getattr(a, "id", "")))
                cls_val = int(p.predicted_class)
                recent_preds.append(
                    RecentPredictionOut(
                        prediction_id=p_id,
                        assessment_id=asm_id,
                        model_name=p.model_name,
                        predicted_class=cls_val,
                        predicted_label="Death event predicted" if cls_val == 1 else "No death event predicted",
                        predicted_probability=float(p.predicted_probability),
                        created_at=p.created_at,
                    )
                )
        except Exception:
            pass

    if not recent_preds:
        # Fallback to recent assessments with predictions
        asms = (
            db.query(Assessment)
            .filter(
                Assessment.doctor_id == current_doctor.doctor_id,
                Assessment.predicted_class != None,
            )
            .order_by(Assessment.updated_at.desc())
            .limit(5)
            .all()
        )
        for a in asms:
            asm_id = str(getattr(a, "assessment_id", getattr(a, "id", "")))
            cls_val = int(a.predicted_class)
            prob_val = getattr(a, "predicted_probability", 0.5)
            prob_float = float(prob_val) if prob_val is not None else 0.5
            recent_preds.append(
                RecentPredictionOut(
                    prediction_id=f"pred-{asm_id[:8]}",
                    assessment_id=asm_id,
                    model_name=getattr(a, "selected_model", "Artificial Neural Network") or "Artificial Neural Network",
                    predicted_class=cls_val,
                    predicted_label="Death event predicted" if cls_val == 1 else "No death event predicted",
                    predicted_probability=prob_float,
                    created_at=a.updated_at,
                )
            )

    return recent_preds


@router.get(
    "/dashboard/prediction-distribution",
    response_model=PredictionDistributionOut,
    summary="Get prediction distribution counts grouped by class",
)
def get_dashboard_prediction_distribution(
    model: str = "ALL",
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Returns prediction counts grouped by class (0 vs 1).
    Explicit notice: Model outputs, not actual patient outcomes.
    """
    if not isinstance(model, str):
        model = "ALL"
    model_norm = model.strip().upper()
    c0 = 0
    c1 = 0

    if Prediction is not None:
        try:
            preds_q = (
                db.query(Prediction)
                .join(Assessment, Prediction.assessment_id == getattr(Assessment, "assessment_id", getattr(Assessment, "id", None)))
                .filter(Assessment.doctor_id == current_doctor.doctor_id)
            )
            if model_norm in ("LOGISTIC_REGRESSION", "LR"):
                preds_q = preds_q.filter(Prediction.model_name.ilike("%logistic%"))
            elif model_norm in ("ANN", "NEURAL"):
                preds_q = preds_q.filter(or_(Prediction.model_name.ilike("%neural%"), Prediction.model_name.ilike("%ann%")))

            c0 = preds_q.filter(Prediction.predicted_class == 0).count()
            c1 = preds_q.filter(Prediction.predicted_class == 1).count()
        except Exception:
            pass

    if c0 == 0 and c1 == 0:
        asm_q = db.query(Assessment).filter(
            Assessment.doctor_id == current_doctor.doctor_id,
            Assessment.predicted_class != None,
        )
        if model_norm in ("LOGISTIC_REGRESSION", "LR"):
            asm_q = asm_q.filter(Assessment.selected_model.ilike("%logistic%"))
        elif model_norm in ("ANN", "NEURAL"):
            asm_q = asm_q.filter(or_(Assessment.selected_model.ilike("%neural%"), Assessment.selected_model.ilike("%ann%")))

        c0 = asm_q.filter(Assessment.predicted_class == 0).count()
        c1 = asm_q.filter(Assessment.predicted_class == 1).count()

    return PredictionDistributionOut(
        model=model_norm,
        class_0_count=c0,
        class_1_count=c1,
    )


@router.get(
    "/dashboard/model-usage",
    response_model=ModelUsageOut,
    summary="Get prediction usage comparison between models",
)
def get_dashboard_model_usage(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    """
    Compares total predictions generated by Logistic Regression vs ANN.
    """
    lr_count = 0
    ann_count = 0

    if Prediction is not None:
        try:
            preds_q = (
                db.query(Prediction)
                .join(Assessment, Prediction.assessment_id == getattr(Assessment, "assessment_id", getattr(Assessment, "id", None)))
                .filter(Assessment.doctor_id == current_doctor.doctor_id)
            )
            lr_count = preds_q.filter(Prediction.model_name.ilike("%logistic%")).count()
            ann_count = preds_q.filter(or_(Prediction.model_name.ilike("%neural%"), Prediction.model_name.ilike("%ann%"))).count()
        except Exception:
            pass

    if lr_count == 0 and ann_count == 0:
        asm_q = db.query(Assessment).filter(
            Assessment.doctor_id == current_doctor.doctor_id,
            Assessment.predicted_class != None,
        )
        lr_count = asm_q.filter(Assessment.selected_model.ilike("%logistic%")).count()
        ann_count = asm_q.filter(or_(Assessment.selected_model.ilike("%neural%"), Assessment.selected_model.ilike("%ann%"))).count()

    return ModelUsageOut(
        logistic_regression=lr_count,
        ann=ann_count,
        total=lr_count + ann_count,
    )


# ---------------------------------------------------------------------------
# Compatibility Endpoints (History & Dashboard Stats)
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
    if Prediction is None:
        return []

    try:
        results = (
            db.query(Prediction, Assessment)
            .join(Assessment, Prediction.assessment_id == getattr(Assessment, "assessment_id", getattr(Assessment, "id", None)))
            .filter(Assessment.doctor_id == current_doctor.doctor_id)
            .order_by(Prediction.created_at.desc())
            .all()
        )

        return [
            PredictionOut(
                id=str(pred.id),
                prediction_code=pred.prediction_code,
                assessment_id=str(pred.assessment_id),
                assessment_code=getattr(asm, "assessment_code", None),
                patient_reference_id=getattr(asm, "patient_reference", getattr(asm, "patient_reference_id", None)),
                model_name=pred.model_name,
                predicted_class=pred.predicted_class,
                predicted_probability=float(pred.predicted_probability),
                classification_threshold=float(pred.classification_threshold),
                model_version=pred.model_version,
                created_at=pred.created_at,
            )
            for pred, asm in results
        ]
    except Exception:
        return []


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsOut,
    summary="Doctor personal dashboard metrics",
)
def get_doctor_dashboard_stats(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
):
    summary = get_dashboard_summary(current_doctor=current_doctor, db=db)
    return DashboardStatsOut(
        total_assessments=summary.total_assessments,
        total_predictions=summary.total_predictions,
        ann_predictions=summary.ann_predictions,
        lr_predictions=summary.logistic_regression_predictions,
        most_recent_prediction=None,
    )
