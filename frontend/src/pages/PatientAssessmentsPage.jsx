import React, { useState, useEffect } from 'react'
import { getAssessments, saveAssessment, deleteAssessment } from '../services/assessmentStore.js'

export default function PatientAssessmentsPage({ doctorUser, onNavigate, onSelectForPrediction }) {
  const [assessments, setAssessments] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [modelFilter, setModelFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 8

  // Modal / Drawer states
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [recordToDelete, setRecordToDelete] = useState(null)
  const [editFormData, setEditFormData] = useState({})
  const [editErrors, setEditErrors] = useState({})

  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = () => {
    const list = getAssessments()
    setAssessments(list)
  }

  // Filtered records
  const filteredRecords = assessments.filter((rec) => {
    const matchesSearch =
      !searchTerm ||
      (rec.assessmentCode && rec.assessmentCode.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (rec.patientReferenceId && rec.patientReferenceId.toLowerCase().includes(searchTerm.toLowerCase()))

    const matchesModel =
      modelFilter === 'ALL' ||
      (modelFilter === 'LR' && rec.model === 'Logistic Regression') ||
      (modelFilter === 'ANN' && rec.model === 'Artificial Neural Network') ||
      (modelFilter === 'NONE' && !rec.model)

    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'POSITIVE' && rec.predictedClass === 1) ||
      (statusFilter === 'NEGATIVE' && rec.predictedClass === 0) ||
      (statusFilter === 'PENDING' && rec.predictedClass === null)

    return matchesSearch && matchesModel && matchesStatus
  })

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredRecords.length / pageSize))
  const paginatedRecords = filteredRecords.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  // Handlers
  const handleViewDetails = (record) => {
    setSelectedRecord(record)
    setIsEditing(false)
  }

  const handleStartEdit = (record) => {
    setSelectedRecord(record)
    setEditFormData({
      patientReferenceId: record.patientReferenceId || '',
      age: record.age,
      anaemia: record.anaemia,
      creatinine_phosphokinase: record.creatinine_phosphokinase,
      diabetes: record.diabetes,
      ejection_fraction: record.ejection_fraction,
      high_blood_pressure: record.high_blood_pressure,
      platelets: record.platelets,
      serum_creatinine: record.serum_creatinine,
      serum_sodium: record.serum_sodium,
      sex: record.sex,
      smoking: record.smoking,
    })
    setEditErrors({})
    setIsEditing(true)
  }

  const handleStartCreate = () => {
    setEditFormData({
      patientReferenceId: '',
      age: '60',
      anaemia: 0,
      creatinine_phosphokinase: '250',
      diabetes: 0,
      ejection_fraction: '38',
      high_blood_pressure: 0,
      platelets: '260000',
      serum_creatinine: '1.1',
      serum_sodium: '137',
      sex: 1,
      smoking: 0,
    })
    setEditErrors({})
    setIsCreating(true)
  }

  const validateEditForm = () => {
    const errors = {}
    const rules = [
      ['age', 1, 120, 'Age must be between 1 and 120'],
      ['creatinine_phosphokinase', 1, 10000, 'CPK must be between 1 and 10,000'],
      ['ejection_fraction', 1, 100, 'EF must be between 1% and 100%'],
      ['platelets', 1, 1500000, 'Platelets must be between 1 and 1,500,000'],
      ['serum_creatinine', 0.1, 25, 'Creatinine must be between 0.1 and 25 mg/dL'],
      ['serum_sodium', 50, 200, 'Sodium must be between 50 and 200 mEq/L'],
    ]

    rules.forEach(([field, min, max, msg]) => {
      const val = Number(editFormData[field])
      if (editFormData[field] === '' || isNaN(val) || val < min || val > max) {
        errors[field] = msg
      }
    })

    setEditErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSaveEdit = (e) => {
    e.preventDefault()
    if (!validateEditForm()) return

    const updated = saveAssessment({
      ...selectedRecord,
      ...editFormData,
    })

    loadRecords()
    setSelectedRecord(updated)
    setIsEditing(false)
  }

  const handleSaveCreate = (e) => {
    e.preventDefault()
    if (!validateEditForm()) return

    const cleanDoctorName = doctorUser?.name || 'Attending Physician'
    const newRecord = saveAssessment({
      ...editFormData,
      doctorName: cleanDoctorName,
      doctorId: doctorUser?.email || 'DR-CURRENT',
    })

    loadRecords()
    setIsCreating(false)
    setSelectedRecord(newRecord)
  }

  const handleConfirmDelete = () => {
    if (!recordToDelete) return
    deleteAssessment(recordToDelete.id)
    loadRecords()
    if (selectedRecord && selectedRecord.id === recordToDelete.id) {
      setSelectedRecord(null)
    }
    setRecordToDelete(null)
  }

  return (
    <div className="assessments-page-container">
      {/* 1. Page Header & Database Readiness Banner */}
      <div className="assessments-top-card">
        <div className="assessments-header-text">
          <div className="sql-readiness-pill">
            <span className="sql-status-dot" />
            <span>SQL Server Integration: Assessments Table Schema Prepared</span>
          </div>
          <h2 className="assessments-page-title">Patient Assessments Directory</h2>
          <p className="assessments-page-desc">
            Browse, search, and audit patient clinical parameter records. Each assessment stores all 11 required biomarkers, patient reference codes, and associated model prediction history.
          </p>
        </div>
        <div className="assessments-top-actions">
          <button
            type="button"
            className="btn-dash-primary"
            onClick={handleStartCreate}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>Record Assessment</span>
          </button>
        </div>
      </div>

      {/* 2. Filters & Search Bar */}
      <div className="assessments-controls-card">
        <div className="search-bar-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="assessments-search-input"
            placeholder="Search by Assessment ID or Patient Reference…"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1)
            }}
          />
          {searchTerm && (
            <button
              type="button"
              className="clear-search-btn"
              onClick={() => setSearchTerm('')}
              aria-label="Clear search"
            >
              &times;
            </button>
          )}
        </div>

        <div className="filter-dropdowns-group">
          {/* Model Filter */}
          <div className="filter-select-wrap">
            <label htmlFor="filter-model" className="filter-label">Model:</label>
            <select
              id="filter-model"
              className="filter-select"
              value={modelFilter}
              onChange={(e) => {
                setModelFilter(e.target.value)
                setCurrentPage(1)
              }}
            >
              <option value="ALL">All Models</option>
              <option value="LR">Logistic Regression</option>
              <option value="ANN">Artificial Neural Net</option>
              <option value="NONE">Unpredicted Only</option>
            </select>
          </div>

          {/* Outcome Filter */}
          <div className="filter-select-wrap">
            <label htmlFor="filter-outcome" className="filter-label">Prediction:</label>
            <select
              id="filter-outcome"
              className="filter-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setCurrentPage(1)
              }}
            >
              <option value="ALL">All Outcomes</option>
              <option value="POSITIVE">Mortality Risk (Class 1)</option>
              <option value="NEGATIVE">Low Risk (Class 0)</option>
              <option value="PENDING">Pending Inference</option>
            </select>
          </div>
        </div>
      </div>

      {/* 3. Assessments Table */}
      <div className="assessments-table-card">
        {filteredRecords.length === 0 ? (
          /* Honest Empty State */
          <div className="assessments-empty-box">
            <div className="empty-halo-icon" aria-hidden="true">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
                <line x1="9" y1="12" x2="15" y2="12" />
                <line x1="9" y1="16" x2="13" y2="16" />
              </svg>
            </div>
            <h3 className="empty-title">
              {searchTerm || modelFilter !== 'ALL' || statusFilter !== 'ALL'
                ? 'No matching assessments found'
                : 'No Patient Assessments Recorded Yet'}
            </h3>
            <p className="empty-desc">
              {searchTerm || modelFilter !== 'ALL' || statusFilter !== 'ALL'
                ? 'Try adjusting your search criteria or resetting filters to view all records.'
                : 'Assessments entered during patient risk predictions or logged manually will be archived here with full clinical parameters and audit trails.'}
            </p>
            <div className="empty-actions-row">
              {searchTerm || modelFilter !== 'ALL' || statusFilter !== 'ALL' ? (
                <button
                  type="button"
                  className="btn-dash-secondary"
                  onClick={() => {
                    setSearchTerm('')
                    setModelFilter('ALL')
                    setStatusFilter('ALL')
                  }}
                >
                  Reset Filters
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="btn-dash-primary"
                    onClick={handleStartCreate}
                  >
                    <span>Record New Assessment</span>
                  </button>
                  <button
                    type="button"
                    className="btn-dash-secondary"
                    onClick={() => onNavigate('prediction')}
                  >
                    <span>Go to New Prediction</span>
                  </button>
                </>
              )}
            </div>
          </div>
        ) : (
          /* Populated Table */
          <div className="table-responsive-wrapper">
            <table className="assessments-table">
              <thead>
                <tr>
                  <th>Assessment ID</th>
                  <th>Patient Reference</th>
                  <th>Age</th>
                  <th>Sex</th>
                  <th>Assessment Date</th>
                  <th>Model Used</th>
                  <th>Risk Outcome</th>
                  <th className="th-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedRecords.map((rec) => {
                  return (
                    <tr key={rec.id} className="table-data-row">
                      <td className="cell-id">
                        <span className="assessment-code-badge">{rec.assessmentCode}</span>
                        {rec.version > 1 && (
                          <span className="version-pill" title={`Revision v${rec.version}`}>
                            v{rec.version}
                          </span>
                        )}
                      </td>
                      <td className="cell-patient-ref">
                        {rec.patientReferenceId ? (
                          <span className="patient-id-tag">{rec.patientReferenceId}</span>
                        ) : (
                          <span className="anonymous-tag">Anonymous</span>
                        )}
                      </td>
                      <td className="cell-age">{rec.age} yrs</td>
                      <td className="cell-sex">
                        <span className={`sex-badge ${rec.sex === 1 ? 'male' : 'female'}`}>
                          {rec.sex === 1 ? 'Male' : 'Female'}
                        </span>
                      </td>
                      <td className="cell-date">
                        <span className="date-main">{rec.displayCreatedAt || rec.createdAt?.slice(0, 10)}</span>
                      </td>
                      <td className="cell-model">
                        {rec.model ? (
                          <span className="model-chip">{rec.model}</span>
                        ) : (
                          <span className="unpredicted-chip">Not Evaluated</span>
                        )}
                      </td>
                      <td className="cell-prediction">
                        {rec.predictedClass !== null && rec.predictedClass !== undefined ? (
                          <div className="prediction-cell-wrap">
                            <span
                              className={`risk-badge ${
                                rec.predictedClass === 1 ? 'risk-high' : 'risk-low'
                              }`}
                            >
                              {rec.predictedClass === 1 ? 'Death Event' : 'No Death Event'}
                            </span>
                            {rec.predictedProbability !== null && (
                              <span className="prob-value">
                                {(rec.predictedProbability * 100).toFixed(1)}%
                              </span>
                            )}
                            {rec.isPredictionStale && (
                              <span
                                className="stale-warning-tag"
                                title="Parameters were modified after inference. Prediction requires re-evaluation."
                              >
                                Stale
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="pending-text">Pending Inference</span>
                        )}
                      </td>
                      <td className="cell-actions">
                        <button
                          type="button"
                          className="btn-table-action view"
                          onClick={() => handleViewDetails(rec)}
                          title="View clinical parameter details"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                          <span>Details</span>
                        </button>
                        <button
                          type="button"
                          className="btn-table-action edit"
                          onClick={() => handleStartEdit(rec)}
                          title="Edit clinical parameters"
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="btn-table-action delete"
                          onClick={() => setRecordToDelete(rec)}
                          title="Delete record"
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {filteredRecords.length > pageSize && (
          <div className="table-pagination-row">
            <span className="pagination-info">
              Showing {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, filteredRecords.length)} of {filteredRecords.length} records
            </span>
            <div className="pagination-buttons">
              <button
                type="button"
                className="btn-page"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
                <button
                  key={pg}
                  type="button"
                  className={`btn-page-num ${currentPage === pg ? 'active' : ''}`}
                  onClick={() => setCurrentPage(pg)}
                >
                  {pg}
                </button>
              ))}
              <button
                type="button"
                className="btn-page"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 4. Clinical Details Drawer / Modal */}
      {selectedRecord && !isEditing && (
        <div className="clinical-modal-backdrop" onClick={() => setSelectedRecord(null)}>
          <div
            className="clinical-modal-content drawer-style"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="details-title"
          >
            {/* Modal Header */}
            <div className="clinical-modal-header">
              <div className="details-header-meta">
                <span className="details-kicker">Assessment Record Details</span>
                <h3 id="details-title" className="details-code-title">
                  {selectedRecord.assessmentCode}
                </h3>
                <div className="details-badges-row">
                  {selectedRecord.patientReferenceId ? (
                    <span className="details-patient-pill">
                      Patient: <strong>{selectedRecord.patientReferenceId}</strong>
                    </span>
                  ) : (
                    <span className="details-anon-pill">Anonymous Evaluation</span>
                  )}
                  <span className="details-version-pill">Version {selectedRecord.version || 1}</span>
                  <span className="details-doctor-pill">Attending: {selectedRecord.doctorName || 'Doctor'}</span>
                </div>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setSelectedRecord(null)}
                aria-label="Close details"
              >
                &times;
              </button>
            </div>

            {/* Modal Body: Organized 11 Clinical Biomarkers */}
            <div className="clinical-modal-body">
              {/* Stale Warning If Parameters Were Modified */}
              {selectedRecord.isPredictionStale && (
                <div className="stale-alert-banner" role="alert">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <div>
                    <strong>Prediction Discrepancy Notice:</strong> Clinical parameters in this record were modified after the initial prediction was generated. Re-run inference to calculate an accurate risk score.
                  </div>
                </div>
              )}

              {/* Group 1: Quantitative Measurements */}
              <div className="details-group-card">
                <h4 className="details-group-heading">
                  <span className="details-group-num">1</span>
                  <span>Quantitative Measurements &amp; Laboratory Assays</span>
                </h4>
                <div className="details-params-grid">
                  <div className="param-item-box">
                    <span className="param-item-name">Age</span>
                    <span className="param-item-value">{selectedRecord.age} <small>years</small></span>
                    <span className="param-item-norm">Cohort range: 40–95</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Ejection Fraction</span>
                    <span className={`param-item-value ${selectedRecord.ejection_fraction < 35 ? 'critical' : ''}`}>
                      {selectedRecord.ejection_fraction}%
                    </span>
                    <span className="param-item-norm">Normal: 50%–70%</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Serum Creatinine</span>
                    <span className={`param-item-value ${selectedRecord.serum_creatinine > 1.4 ? 'critical' : ''}`}>
                      {selectedRecord.serum_creatinine} <small>mg/dL</small>
                    </span>
                    <span className="param-item-norm">Normal: 0.7–1.3 mg/dL</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Serum Sodium</span>
                    <span className={`param-item-value ${selectedRecord.serum_sodium < 135 ? 'critical' : ''}`}>
                      {selectedRecord.serum_sodium} <small>mEq/L</small>
                    </span>
                    <span className="param-item-norm">Normal: 135–145 mEq/L</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Platelet Count</span>
                    <span className="param-item-value">
                      {Number(selectedRecord.platelets).toLocaleString()} <small>cells/µL</small>
                    </span>
                    <span className="param-item-norm">Normal: 150k–450k</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Creatinine Phosphokinase</span>
                    <span className="param-item-value">
                      {selectedRecord.creatinine_phosphokinase} <small>mcg/L</small>
                    </span>
                    <span className="param-item-norm">Normal: 10–120 mcg/L</span>
                  </div>
                </div>
              </div>

              {/* Group 2: Binary & Demographic Indicators */}
              <div className="details-group-card">
                <h4 className="details-group-heading">
                  <span className="details-group-num">2</span>
                  <span>Binary &amp; Demographic Indicators</span>
                </h4>
                <div className="details-params-grid">
                  <div className="param-item-box">
                    <span className="param-item-name">Biological Sex</span>
                    <span className="param-item-value">
                      {selectedRecord.sex === 1 ? 'Male (1)' : 'Female (0)'}
                    </span>
                    <span className="param-item-norm">Dataset encoding: 0=F, 1=M</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Anaemia Status</span>
                    <span className={`param-item-value ${selectedRecord.anaemia === 1 ? 'critical' : ''}`}>
                      {selectedRecord.anaemia === 1 ? 'Positive (1)' : 'Negative (0)'}
                    </span>
                    <span className="param-item-norm">Hb &lt; 12 g/dL</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Diabetes Diagnosis</span>
                    <span className={`param-item-value ${selectedRecord.diabetes === 1 ? 'critical' : ''}`}>
                      {selectedRecord.diabetes === 1 ? 'Positive (1)' : 'Negative (0)'}
                    </span>
                    <span className="param-item-norm">Confirmed diagnosis</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">High Blood Pressure</span>
                    <span className={`param-item-value ${selectedRecord.high_blood_pressure === 1 ? 'critical' : ''}`}>
                      {selectedRecord.high_blood_pressure === 1 ? 'Positive (1)' : 'Negative (0)'}
                    </span>
                    <span className="param-item-norm">Hypertension history</span>
                  </div>

                  <div className="param-item-box">
                    <span className="param-item-name">Smoking History</span>
                    <span className={`param-item-value ${selectedRecord.smoking === 1 ? 'critical' : ''}`}>
                      {selectedRecord.smoking === 1 ? 'Positive (1)' : 'Negative (0)'}
                    </span>
                    <span className="param-item-norm">Active tobacco consumption</span>
                  </div>
                </div>
              </div>

              {/* Prediction Section */}
              <div className="details-prediction-card">
                <h4 className="details-prediction-title">Model Inference &amp; Risk Estimation</h4>
                {selectedRecord.model ? (
                  <div className="prediction-detail-content">
                    <div className="pred-metric-row">
                      <div className="pred-cell">
                        <span className="pred-label">Selected Model</span>
                        <span className="pred-val">{selectedRecord.model}</span>
                      </div>
                      <div className="pred-cell">
                        <span className="pred-label">Predicted Classification</span>
                        <span className={`pred-val ${selectedRecord.predictedClass === 1 ? 'text-danger' : 'text-success'}`}>
                          {selectedRecord.predictedLabel || (selectedRecord.predictedClass === 1 ? 'Death event predicted' : 'No death event predicted')}
                        </span>
                      </div>
                      <div className="pred-cell">
                        <span className="pred-label">Death-Event Probability</span>
                        <span className="pred-val font-mono">
                          {selectedRecord.predictedProbability !== null
                            ? `${(selectedRecord.predictedProbability * 100).toFixed(2)}%`
                            : 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="no-pred-text">
                    This assessment record has not yet been processed by an inference model. Click &quot;Test in Prediction Workspace&quot; below to run inference.
                  </p>
                )}
              </div>

              {/* Audit Log Trail */}
              {selectedRecord.auditLog && selectedRecord.auditLog.length > 0 && (
                <div className="details-audit-card">
                  <h4 className="audit-card-title">Audit Trail</h4>
                  <ul className="audit-timeline">
                    {selectedRecord.auditLog.map((item, idx) => (
                      <li key={idx} className="audit-item">
                        <span className="audit-dot" />
                        <div className="audit-content">
                          <span className="audit-action">{item.action}</span>
                          <span className="audit-details">{item.details}</span>
                          <span className="audit-time">{new Date(item.timestamp).toLocaleString()}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="clinical-modal-footer">
              <button
                type="button"
                className="btn-dash-secondary"
                onClick={() => setSelectedRecord(null)}
              >
                Close Details
              </button>
              <button
                type="button"
                className="btn-dash-secondary"
                onClick={() => handleStartEdit(selectedRecord)}
              >
                Edit Parameters
              </button>
              <button
                type="button"
                className="btn-dash-primary"
                onClick={() => {
                  if (onSelectForPrediction) {
                    onSelectForPrediction(selectedRecord)
                  }
                  onNavigate('prediction')
                }}
              >
                <span>Test in Prediction Workspace &rarr;</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Create / Edit Assessment Modal Form */}
      {(isEditing || isCreating) && (
        <div className="clinical-modal-backdrop" onClick={() => { setIsEditing(false); setIsCreating(false); }}>
          <div
            className="clinical-modal-content form-modal-style"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="clinical-modal-header">
              <div>
                <span className="details-kicker">
                  {isCreating ? 'New Clinical Assessment' : 'Edit Assessment Record'}
                </span>
                <h3 className="details-code-title">
                  {isCreating ? 'Record Patient Parameters' : `Editing ${selectedRecord?.assessmentCode}`}
                </h3>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => { setIsEditing(false); setIsCreating(false); }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={isCreating ? handleSaveCreate : handleSaveEdit} noValidate>
              <div className="clinical-modal-body form-body-scroll">
                {/* Patient Ref ID */}
                <div className="form-field full-width">
                  <label className="form-label" htmlFor="edit-patient-ref">
                    <span className="label-with-tip">Patient Reference ID <small>(Optional)</small></span>
                    <span className="field-unit">Leave blank for anonymous</span>
                  </label>
                  <input
                    id="edit-patient-ref"
                    type="text"
                    className="form-input"
                    placeholder="e.g. PT-2026-084"
                    value={editFormData.patientReferenceId}
                    onChange={(e) => setEditFormData({ ...editFormData, patientReferenceId: e.target.value })}
                  />
                </div>

                <h4 className="edit-section-heading">Quantitative Measurements</h4>
                <div className="form-grid">
                  {/* Age */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-age">
                      <span>Age *</span>
                      <span className="field-unit">years</span>
                    </label>
                    <input
                      id="edit-age"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.age ? 'has-error' : ''}`}
                      value={editFormData.age}
                      onChange={(e) => setEditFormData({ ...editFormData, age: e.target.value })}
                    />
                    {editErrors.age && <span className="field-error-msg">{editErrors.age}</span>}
                  </div>

                  {/* Ejection Fraction */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-ef">
                      <span>Ejection Fraction *</span>
                      <span className="field-unit">%</span>
                    </label>
                    <input
                      id="edit-ef"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.ejection_fraction ? 'has-error' : ''}`}
                      value={editFormData.ejection_fraction}
                      onChange={(e) => setEditFormData({ ...editFormData, ejection_fraction: e.target.value })}
                    />
                    {editErrors.ejection_fraction && <span className="field-error-msg">{editErrors.ejection_fraction}</span>}
                  </div>

                  {/* Serum Creatinine */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-creatinine">
                      <span>Serum Creatinine *</span>
                      <span className="field-unit">mg/dL</span>
                    </label>
                    <input
                      id="edit-creatinine"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.serum_creatinine ? 'has-error' : ''}`}
                      value={editFormData.serum_creatinine}
                      onChange={(e) => setEditFormData({ ...editFormData, serum_creatinine: e.target.value })}
                    />
                    {editErrors.serum_creatinine && <span className="field-error-msg">{editErrors.serum_creatinine}</span>}
                  </div>

                  {/* Serum Sodium */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-sodium">
                      <span>Serum Sodium *</span>
                      <span className="field-unit">mEq/L</span>
                    </label>
                    <input
                      id="edit-sodium"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.serum_sodium ? 'has-error' : ''}`}
                      value={editFormData.serum_sodium}
                      onChange={(e) => setEditFormData({ ...editFormData, serum_sodium: e.target.value })}
                    />
                    {editErrors.serum_sodium && <span className="field-error-msg">{editErrors.serum_sodium}</span>}
                  </div>

                  {/* Platelets */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-platelets">
                      <span>Platelets *</span>
                      <span className="field-unit">cells/µL</span>
                    </label>
                    <input
                      id="edit-platelets"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.platelets ? 'has-error' : ''}`}
                      value={editFormData.platelets}
                      onChange={(e) => setEditFormData({ ...editFormData, platelets: e.target.value })}
                    />
                    {editErrors.platelets && <span className="field-error-msg">{editErrors.platelets}</span>}
                  </div>

                  {/* CPK */}
                  <div className="form-field">
                    <label className="form-label" htmlFor="edit-cpk">
                      <span>Creatinine Phosphokinase *</span>
                      <span className="field-unit">mcg/L</span>
                    </label>
                    <input
                      id="edit-cpk"
                      type="number"
                      step="any"
                      className={`form-input ${editErrors.creatinine_phosphokinase ? 'has-error' : ''}`}
                      value={editFormData.creatinine_phosphokinase}
                      onChange={(e) => setEditFormData({ ...editFormData, creatinine_phosphokinase: e.target.value })}
                    />
                    {editErrors.creatinine_phosphokinase && <span className="field-error-msg">{editErrors.creatinine_phosphokinase}</span>}
                  </div>
                </div>

                <h4 className="edit-section-heading">Binary &amp; Demographic Indicators</h4>
                <div className="form-grid">
                  {/* Sex */}
                  <div className="form-field">
                    <label className="form-label">Biological Sex *</label>
                    <div className={`segmented-toggle sliding-segmented-toggle ${editFormData.sex === 1 ? 'pos-right' : 'pos-left'}`}>
                      <div className="segmented-sliding-glider" aria-hidden="true" />
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.sex === 0 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, sex: 0 })}
                      >
                        Female (0)
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.sex === 1 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, sex: 1 })}
                      >
                        Male (1)
                      </button>
                    </div>
                  </div>

                  {/* Anaemia */}
                  <div className="form-field">
                    <label className="form-label">Anaemia *</label>
                    <div className={`segmented-toggle sliding-segmented-toggle ${editFormData.anaemia === 1 ? 'pos-right' : 'pos-left'}`}>
                      <div className="segmented-sliding-glider" aria-hidden="true" />
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.anaemia === 0 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, anaemia: 0 })}
                      >
                        No (0)
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.anaemia === 1 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, anaemia: 1 })}
                      >
                        Yes (1)
                      </button>
                    </div>
                  </div>

                  {/* Diabetes */}
                  <div className="form-field">
                    <label className="form-label">Diabetes *</label>
                    <div className={`segmented-toggle sliding-segmented-toggle ${editFormData.diabetes === 1 ? 'pos-right' : 'pos-left'}`}>
                      <div className="segmented-sliding-glider" aria-hidden="true" />
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.diabetes === 0 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, diabetes: 0 })}
                      >
                        No (0)
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.diabetes === 1 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, diabetes: 1 })}
                      >
                        Yes (1)
                      </button>
                    </div>
                  </div>

                  {/* High Blood Pressure */}
                  <div className="form-field">
                    <label className="form-label">High Blood Pressure *</label>
                    <div className={`segmented-toggle sliding-segmented-toggle ${editFormData.high_blood_pressure === 1 ? 'pos-right' : 'pos-left'}`}>
                      <div className="segmented-sliding-glider" aria-hidden="true" />
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.high_blood_pressure === 0 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, high_blood_pressure: 0 })}
                      >
                        No (0)
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.high_blood_pressure === 1 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, high_blood_pressure: 1 })}
                      >
                        Yes (1)
                      </button>
                    </div>
                  </div>

                  {/* Smoking */}
                  <div className="form-field">
                    <label className="form-label">Smoking History *</label>
                    <div className={`segmented-toggle sliding-segmented-toggle ${editFormData.smoking === 1 ? 'pos-right' : 'pos-left'}`}>
                      <div className="segmented-sliding-glider" aria-hidden="true" />
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.smoking === 0 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, smoking: 0 })}
                      >
                        No (0)
                      </button>
                      <button
                        type="button"
                        className={`toggle-btn segmented-opt-btn ${editFormData.smoking === 1 ? 'active' : ''}`}
                        onClick={() => setEditFormData({ ...editFormData, smoking: 1 })}
                      >
                        Yes (1)
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="clinical-modal-footer">
                <button
                  type="button"
                  className="btn-dash-secondary"
                  onClick={() => { setIsEditing(false); setIsCreating(false); }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-dash-primary"
                >
                  {isCreating ? 'Save New Record' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. Delete Confirmation Modal */}
      {recordToDelete && (
        <div className="clinical-modal-backdrop" onClick={() => setRecordToDelete(null)}>
          <div
            className="clinical-modal-content confirm-modal-style"
            onClick={(e) => e.stopPropagation()}
            role="alertdialog"
            aria-labelledby="confirm-delete-title"
          >
            <div className="confirm-icon-danger" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h3 id="confirm-delete-title" className="confirm-title">
              Delete Assessment {recordToDelete.assessmentCode}?
            </h3>
            <p className="confirm-desc">
              Are you sure you want to permanently delete this clinical assessment record? This action cannot be undone.
            </p>
            <div className="confirm-actions-row">
              <button
                type="button"
                className="btn-dash-secondary"
                onClick={() => setRecordToDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger-confirm"
                onClick={handleConfirmDelete}
              >
                Delete Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

