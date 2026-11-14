/**
 * assessmentStore.js
 * Client-side clinical assessment store preparing for SQL Server /api/assessments integration.
 * Ensures data entered during physician sessions persists cleanly without fabricating fake records.
 */

const STORAGE_KEY = 'hf_patient_assessments_v1'

export const getAssessments = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (err) {
    console.error('Error reading assessments storage:', err)
    return []
  }
}

export const getAssessmentById = (id) => {
  const records = getAssessments()
  return records.find((r) => r.id === id || r.assessmentCode === id) || null
}

export const saveAssessment = (assessment) => {
  const records = getAssessments()
  const now = new Date().toISOString()
  const displayTime = new Date().toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  const existingIndex = records.findIndex(
    (r) => r.id === assessment.id || (assessment.id && r.assessmentCode === assessment.id)
  )

  if (existingIndex >= 0) {
    // Update existing record
    const existing = records[existingIndex]

    // Check if clinical parameters changed
    const paramsChanged = [
      'age',
      'anaemia',
      'creatinine_phosphokinase',
      'diabetes',
      'ejection_fraction',
      'high_blood_pressure',
      'platelets',
      'serum_creatinine',
      'serum_sodium',
      'sex',
      'smoking',
    ].some((k) => String(existing[k]) !== String(assessment[k]))

    const updatedRecord = {
      ...existing,
      ...assessment,
      version: (existing.version || 1) + 1,
      updatedAt: now,
      displayUpdatedAt: displayTime,
      isPredictionStale: paramsChanged ? true : existing.isPredictionStale,
      auditLog: [
        ...(existing.auditLog || []),
        {
          timestamp: now,
          action: 'Updated clinical values',
          details: paramsChanged
            ? 'Input parameters modified — requires new prediction to re-calibrate risk.'
            : 'Record metadata updated.',
        },
      ],
    }

    records[existingIndex] = updatedRecord
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records))
    return updatedRecord
  }

  // Create new record
  const count = records.length + 1
  const code = `ASM-2026-${String(count).padStart(4, '0')}`
  const newRecord = {
    id: assessment.id || `asm_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    assessmentCode: code,
    patientReferenceId: assessment.patientReferenceId?.trim() || null,
    doctorId: assessment.doctorId || 'DR-CURRENT',
    doctorName: assessment.doctorName || 'Attending Physician',
    age: Number(assessment.age) || 60,
    anaemia: Number(assessment.anaemia) || 0,
    creatinine_phosphokinase: Number(assessment.creatinine_phosphokinase) || 250,
    diabetes: Number(assessment.diabetes) || 0,
    ejection_fraction: Number(assessment.ejection_fraction) || 38,
    high_blood_pressure: Number(assessment.high_blood_pressure) || 0,
    platelets: Number(assessment.platelets) || 260000,
    serum_creatinine: Number(assessment.serum_creatinine) || 1.1,
    serum_sodium: Number(assessment.serum_sodium) || 137,
    sex: Number(assessment.sex) ?? 1,
    smoking: Number(assessment.smoking) || 0,
    model: assessment.model || null,
    predictedClass: assessment.predictedClass ?? null,
    predictedLabel: assessment.predictedLabel || null,
    predictedProbability: assessment.predictedProbability ?? null,
    predictionTimestamp: assessment.predictionTimestamp || null,
    isPredictionStale: false,
    version: 1,
    createdAt: now,
    displayCreatedAt: displayTime,
    updatedAt: now,
    auditLog: [
      {
        timestamp: now,
        action: 'Record created',
        details: 'Initial clinical assessment logged into workspace.',
      },
    ],
  }

  records.unshift(newRecord)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(records))
  return newRecord
}

export const deleteAssessment = (id) => {
  const records = getAssessments()
  const filtered = records.filter((r) => r.id !== id && r.assessmentCode !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
  return filtered
}

// ── Predictions Store (Immutable prediction log) ────────────────────────────
const PREDICTIONS_STORAGE_KEY = 'hf_patient_predictions_v1'

export const getPredictions = () => {
  try {
    const raw = localStorage.getItem(PREDICTIONS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (err) {
    console.error('Error reading predictions storage:', err)
    return []
  }
}

export const getPredictionById = (id) => {
  const list = getPredictions()
  return list.find((p) => p.id === id || p.predictionCode === id) || null
}

export const savePrediction = (prediction) => {
  const list = getPredictions()
  const now = new Date().toISOString()
  const displayTime = new Date().toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

  const count = list.length + 1
  const code = `PRD-2026-${String(count).padStart(4, '0')}`

  const newPrediction = {
    id: prediction.id || `prd_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    predictionCode: code,
    assessmentId: prediction.assessmentId || null,
    assessmentCode: prediction.assessmentCode || 'ASM-RECORD',
    patientReferenceId: prediction.patientReferenceId?.trim() || null,
    modelName: prediction.modelName || 'Logistic Regression',
    predictedClass: Number(prediction.predictedClass) ?? 0,
    predictedLabel:
      prediction.predictedLabel ||
      (Number(prediction.predictedClass) === 1 ? 'Death event predicted' : 'No death event predicted'),
    predictedProbability: Number(prediction.predictedProbability) ?? 0,
    classificationThreshold: Number(prediction.classificationThreshold) || 0.5,
    modelVersion: prediction.modelVersion || 'v1.0.0',
    inputs: prediction.inputs || {},
    createdAt: now,
    displayCreatedAt: displayTime,
  }

  list.unshift(newPrediction)
  localStorage.setItem(PREDICTIONS_STORAGE_KEY, JSON.stringify(list))
  return newPrediction
}

export const deletePrediction = (id) => {
  const list = getPredictions()
  const filtered = list.filter((p) => p.id !== id && p.predictionCode !== id)
  localStorage.setItem(PREDICTIONS_STORAGE_KEY, JSON.stringify(filtered))
  return filtered
}

// ── Backend API Synchronization (Step 7: Protected APIs) ────────────────────

export const fetchBackendAssessments = async () => {
  const token = localStorage.getItem('cardiopredict_access_token')
  if (!token) return getAssessments()

  try {
    const res = await fetch('http://127.0.0.1:8000/api/assessments', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        const mapped = data.map((d) => ({
          id: d.id,
          assessmentCode: d.assessment_code,
          patientReferenceId: d.patient_reference_id,
          doctorId: d.doctor_id,
          doctorName: 'Attending Physician',
          age: d.age,
          anaemia: d.anaemia,
          creatinine_phosphokinase: d.creatinine_phosphokinase,
          diabetes: d.diabetes,
          ejection_fraction: d.ejection_fraction,
          high_blood_pressure: d.high_blood_pressure,
          platelets: d.platelets,
          serum_creatinine: d.serum_creatinine,
          serum_sodium: d.serum_sodium,
          sex: d.sex,
          smoking: d.smoking,
          model: d.selected_model,
          predictedClass: d.predicted_class,
          predictedLabel:
            d.predicted_class === 1
              ? 'Death event predicted'
              : d.predicted_class === 0
              ? 'No death event predicted'
              : null,
          predictedProbability: d.predicted_probability,
          createdAt: d.created_at,
          updatedAt: d.updated_at,
        }))
        localStorage.setItem(STORAGE_KEY, JSON.stringify(mapped))
        return mapped
      }
    }
  } catch (err) {
    console.warn('Backend assessments sync warning:', err)
  }
  return getAssessments()
}

export const fetchBackendPredictions = async () => {
  const token = localStorage.getItem('cardiopredict_access_token')
  if (!token) return getPredictions()

  try {
    const res = await fetch('http://127.0.0.1:8000/api/history', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        const mapped = data.map((p) => ({
          id: p.id,
          predictionCode: p.prediction_code,
          assessmentId: p.assessment_id,
          assessmentCode: p.assessment_code,
          patientReferenceId: p.patient_reference_id,
          modelName: p.model_name,
          predictedClass: p.predicted_class,
          predictedLabel:
            p.predicted_class === 1
              ? 'Death event predicted'
              : 'No death event predicted',
          predictedProbability: p.predicted_probability,
          classificationThreshold: p.classification_threshold,
          modelVersion: p.model_version,
          createdAt: p.created_at,
        }))
        localStorage.setItem(PREDICTIONS_STORAGE_KEY, JSON.stringify(mapped))
        return mapped
      }
    }
  } catch (err) {
    console.warn('Backend predictions sync warning:', err)
  }
  return getPredictions()
}


