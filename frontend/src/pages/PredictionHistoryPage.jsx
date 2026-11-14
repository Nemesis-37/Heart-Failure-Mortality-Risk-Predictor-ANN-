import React, { useState, useEffect } from 'react'
import { getPredictions, deletePrediction, fetchBackendPredictions } from '../services/assessmentStore.js'

export default function PredictionHistoryPage({ doctorUser, onNavigate, onSelectAssessment }) {
  const [predictions, setPredictions] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [modelFilter, setModelFilter] = useState('ALL')
  const [classFilter, setClassFilter] = useState('ALL')
  const [sortOrder, setSortOrder] = useState('NEWEST')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 8

  // Modal states
  const [selectedPrediction, setSelectedPrediction] = useState(null)
  const [predictionToDelete, setPredictionToDelete] = useState(null)
  const [showInputParams, setShowInputParams] = useState(false)

  useEffect(() => {
    loadPredictions()
  }, [])

  const loadPredictions = async () => {
    const list = getPredictions()
    setPredictions(list)
    try {
      const remote = await fetchBackendPredictions()
      if (remote && remote.length > 0) {
        setPredictions(remote)
      }
    } catch {
      // Retain local predictions
    }
  }

  // Summary Metrics calculated strictly from real records
  const totalPredictions = predictions.length
  const annCount = predictions.filter((p) => p.modelName === 'Artificial Neural Network').length
  const lrCount = predictions.filter((p) => p.modelName === 'Logistic Regression').length
  const mostRecent = predictions.length > 0 ? predictions[0] : null

  // Filter and sort records
  const filteredPredictions = predictions
    .filter((p) => {
      const searchLower = searchTerm.toLowerCase().trim()
      const matchesSearch =
        !searchLower ||
        (p.predictionCode && p.predictionCode.toLowerCase().includes(searchLower)) ||
        (p.assessmentCode && p.assessmentCode.toLowerCase().includes(searchLower)) ||
        (p.patientReferenceId && p.patientReferenceId.toLowerCase().includes(searchLower))

      const matchesModel =
        modelFilter === 'ALL' ||
        (modelFilter === 'LR' && p.modelName === 'Logistic Regression') ||
        (modelFilter === 'ANN' && p.modelName === 'Artificial Neural Network')

      const matchesClass =
        classFilter === 'ALL' ||
        (classFilter === 'POSITIVE' && p.predictedClass === 1) ||
        (classFilter === 'NEGATIVE' && p.predictedClass === 0)

      return matchesSearch && matchesModel && matchesClass
    })
    .sort((a, b) => {
      const dateA = new Date(a.createdAt || 0).getTime()
      const dateB = new Date(b.createdAt || 0).getTime()
      return sortOrder === 'NEWEST' ? dateB - dateA : dateA - dateB
    })

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredPredictions.length / pageSize))
  const paginatedPredictions = filteredPredictions.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const handleOpenDetails = (pred) => {
    setSelectedPrediction(pred)
    setShowInputParams(false)
  }

  const handleConfirmDelete = () => {
    if (!predictionToDelete) return
    deletePrediction(predictionToDelete.id)
    loadPredictions()
    if (selectedPrediction && selectedPrediction.id === predictionToDelete.id) {
      setSelectedPrediction(null)
    }
    setPredictionToDelete(null)
  }

  return (
    <div className="history-page-container">
      {/* 1. Header Hero Card */}
      <section className="history-top-card" aria-label="Prediction History Header">
        <div className="history-header-text">
          <div className="sql-readiness-pill">
            <span className="sql-status-dot" />
            <span>SQL Server Integration: Predictions Table Schema Prepared</span>
          </div>
          <h2 className="history-page-title">Prediction History</h2>
          <p className="history-page-desc">
            Review previous assessments and model-generated prediction results. Audit mathematical death-event probabilities, compare Logistic Regression and ANN inferences, and inspect associated patient parameters.
          </p>
        </div>
        <div className="history-top-actions">
          <button
            type="button"
            className="btn-dash-primary"
            onClick={() => onNavigate('prediction')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span>Run New Prediction</span>
          </button>
        </div>
      </section>

      {/* 2. Four Real Statistics Summary Cards */}
      <section className="history-stats-grid" aria-label="Prediction Telemetry Metrics">
        {/* Total Predictions */}
        <div className="history-stat-card">
          <div className="stat-card-header">
            <span className="stat-card-tag">Inference Volume</span>
            <div className="stat-card-icon icon-blue" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
          </div>
          <div className="stat-card-main">
            <span className="stat-card-value">{totalPredictions}</span>
            <span className="stat-card-label">Total Predictions</span>
          </div>
          <div className="stat-card-footer">
            <span className="stat-card-sub">Recorded across clinical sessions</span>
          </div>
        </div>

        {/* ANN Predictions */}
        <div className="history-stat-card">
          <div className="stat-card-header">
            <span className="stat-card-tag">Deep Learning</span>
            <div className="stat-card-icon icon-purple" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
                <rect x="9" y="9" width="6" height="6" />
                <line x1="9" y1="1" x2="9" y2="4" />
                <line x1="15" y1="1" x2="15" y2="4" />
                <line x1="9" y1="20" x2="9" y2="23" />
                <line x1="15" y1="20" x2="15" y2="23" />
              </svg>
            </div>
          </div>
          <div className="stat-card-main">
            <span className="stat-card-value">{annCount}</span>
            <span className="stat-card-label">ANN Predictions</span>
          </div>
          <div className="stat-card-footer">
            <span className="stat-card-sub">PyTorch neural architecture</span>
          </div>
        </div>

        {/* Logistic Regression Predictions */}
        <div className="history-stat-card">
          <div className="stat-card-header">
            <span className="stat-card-tag">Statistical Baseline</span>
            <div className="stat-card-icon icon-teal" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            </div>
          </div>
          <div className="stat-card-main">
            <span className="stat-card-value">{lrCount}</span>
            <span className="stat-card-label">LR Predictions</span>
          </div>
          <div className="stat-card-footer">
            <span className="stat-card-sub">Linear statistical baseline</span>
          </div>
        </div>

        {/* Most Recent Prediction */}
        <div className="history-stat-card">
          <div className="stat-card-header">
            <span className="stat-card-tag">Latest Inference</span>
            <div className="stat-card-icon icon-emerald" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
          </div>
          <div className="stat-card-main">
            <span className="stat-card-value recent-val">
              {mostRecent ? (
                `${(mostRecent.predictedProbability * 100).toFixed(1)}%`
              ) : (
                'None yet'
              )}
            </span>
            <span className="stat-card-label">
              {mostRecent ? mostRecent.modelName : 'No Runs Yet'}
            </span>
          </div>
          <div className="stat-card-footer">
            <span className="stat-card-sub">
              {mostRecent?.displayCreatedAt || 'Awaiting first patient inference'}
            </span>
          </div>
        </div>
      </section>

      {/* 3. Search and Filters Card */}
      <div className="history-controls-card">
        {/* Search */}
        <div className="history-search-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="history-search-input"
            placeholder="Search by Prediction ID, Assessment ID, or Patient Reference…"
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

        {/* Filters Group */}
        <div className="history-filter-group">
          {/* Model Filter */}
          <div className="history-select-wrap">
            <label htmlFor="filter-hist-model" className="filter-label">Model:</label>
            <select
              id="filter-hist-model"
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
            </select>
          </div>

          {/* Outcome Filter */}
          <div className="history-select-wrap">
            <label htmlFor="filter-hist-class" className="filter-label">Outcome:</label>
            <select
              id="filter-hist-class"
              className="filter-select"
              value={classFilter}
              onChange={(e) => {
                setClassFilter(e.target.value)
                setCurrentPage(1)
              }}
            >
              <option value="ALL">All Outcomes</option>
              <option value="POSITIVE">Death Event (Class 1)</option>
              <option value="NEGATIVE">No Death Event (Class 0)</option>
            </select>
          </div>

          {/* Sort Order */}
          <div className="history-select-wrap">
            <label htmlFor="filter-hist-sort" className="filter-label">Sort:</label>
            <select
              id="filter-hist-sort"
              className="filter-select"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
            >
              <option value="NEWEST">Newest First</option>
              <option value="OLDEST">Oldest First</option>
            </select>
          </div>
        </div>
      </div>

      {/* 4. Prediction History Table */}
      <div className="history-table-card">
        {filteredPredictions.length === 0 ? (
          /* Honest Empty State */
          <div className="history-empty-box">
            <div className="empty-halo-icon" aria-hidden="true">
              <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h3 className="empty-title">
              {searchTerm || modelFilter !== 'ALL' || classFilter !== 'ALL'
                ? 'No matching prediction runs found'
                : 'No Prediction History Recorded Yet'}
            </h3>
            <p className="empty-desc">
              {searchTerm || modelFilter !== 'ALL' || classFilter !== 'ALL'
                ? 'Try clearing your filters or search terms to see all prediction logs.'
                : 'When you execute inference in the New Prediction workspace, immutable audit logs containing model outputs, threshold calculations, and input biomarkers will be recorded here.'}
            </p>
            <div className="empty-actions-row">
              {searchTerm || modelFilter !== 'ALL' || classFilter !== 'ALL' ? (
                <button
                  type="button"
                  className="btn-dash-secondary"
                  onClick={() => {
                    setSearchTerm('')
                    setModelFilter('ALL')
                    setClassFilter('ALL')
                  }}
                >
                  Reset Filters
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-dash-primary"
                  onClick={() => onNavigate('prediction')}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                  <span>Launch First Prediction</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Populated Table */
          <div className="table-responsive-wrapper">
            <table className="assessments-table">
              <thead>
                <tr>
                  <th>Prediction ID</th>
                  <th>Assessment ID</th>
                  <th>Patient Ref</th>
                  <th>Date &amp; Time</th>
                  <th>Model Architecture</th>
                  <th>Predicted Class</th>
                  <th>Probability</th>
                  <th className="th-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedPredictions.map((pred) => (
                  <tr key={pred.id} className="table-data-row">
                    <td className="cell-id">
                      <span className="pred-code-pill">{pred.predictionCode}</span>
                    </td>
                    <td className="cell-asm-link">
                      <button
                        type="button"
                        className="btn-asm-link"
                        onClick={() => {
                          if (onSelectAssessment) {
                            onSelectAssessment(pred.assessmentCode)
                          }
                          onNavigate('assessments')
                        }}
                        title={`Navigate to Assessment ${pred.assessmentCode}`}
                      >
                        {pred.assessmentCode}
                      </button>
                    </td>
                    <td className="cell-patient-ref">
                      {pred.patientReferenceId ? (
                        <span className="patient-id-tag">{pred.patientReferenceId}</span>
                      ) : (
                        <span className="anonymous-tag">Anonymous</span>
                      )}
                    </td>
                    <td className="cell-date">
                      <span className="date-main">{pred.displayCreatedAt}</span>
                    </td>
                    <td className="cell-model">
                      <span className={`model-chip ${pred.modelName.includes('Neural') ? 'model-ann' : 'model-lr'}`}>
                        {pred.modelName}
                      </span>
                    </td>
                    <td className="cell-class">
                      <span className={`risk-badge ${pred.predictedClass === 1 ? 'risk-high' : 'risk-low'}`}>
                        {pred.predictedClass === 1 ? 'Death Event (Class 1)' : 'No Death Event (Class 0)'}
                      </span>
                    </td>
                    <td className="cell-probability">
                      <div className="prob-display-row">
                        <span className={`prob-bold ${pred.predictedProbability >= 0.5 ? 'elevated' : 'baseline'}`}>
                          {(pred.predictedProbability * 100).toFixed(2)}%
                        </span>
                        <div className="mini-prob-track">
                          <div
                            className={`mini-prob-fill ${pred.predictedProbability >= 0.5 ? 'elevated' : 'baseline'}`}
                            style={{ width: `${Math.min(100, Math.max(0, pred.predictedProbability * 100))}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="cell-actions">
                      <button
                        type="button"
                        className="btn-table-action view"
                        onClick={() => handleOpenDetails(pred)}
                        title="View prediction telemetry"
                      >
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        <span>Details</span>
                      </button>
                      <button
                        type="button"
                        className="btn-table-action delete"
                        onClick={() => setPredictionToDelete(pred)}
                        title="Delete log record"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {filteredPredictions.length > pageSize && (
          <div className="table-pagination-row">
            <span className="pagination-info">
              Showing {(currentPage - 1) * pageSize + 1}–
              {Math.min(currentPage * pageSize, filteredPredictions.length)} of {filteredPredictions.length} prediction runs
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

      {/* 5. Prediction Details Drawer / Modal */}
      {selectedPrediction && (
        <div className="clinical-modal-backdrop" onClick={() => setSelectedPrediction(null)}>
          <div
            className="clinical-modal-content drawer-style"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="pred-details-title"
          >
            {/* Header */}
            <div className="clinical-modal-header">
              <div className="details-header-meta">
                <span className="details-kicker">Inference Audit Record</span>
                <h3 id="pred-details-title" className="details-code-title">
                  {selectedPrediction.predictionCode}
                </h3>
                <div className="details-badges-row">
                  <span className="details-patient-pill">
                    Assessment: <strong>{selectedPrediction.assessmentCode}</strong>
                  </span>
                  {selectedPrediction.patientReferenceId && (
                    <span className="details-patient-pill">
                      Patient: <strong>{selectedPrediction.patientReferenceId}</strong>
                    </span>
                  )}
                  <span className="details-version-pill">Model Version: {selectedPrediction.modelVersion || 'v1.0.0'}</span>
                </div>
              </div>
              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setSelectedPrediction(null)}
                aria-label="Close details"
              >
                &times;
              </button>
            </div>

            {/* Body */}
            <div className="clinical-modal-body">
              {/* Outcome Banner */}
              <div className={`clean-outcome-banner ${selectedPrediction.predictedClass === 1 ? 'positive-event' : 'negative-event'}`}>
                <div className="outcome-icon" aria-hidden="true">
                  {selectedPrediction.predictedClass === 1 ? (
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  ) : (
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                  )}
                </div>
                <div className="outcome-text">
                  <span className="outcome-kicker">Model Classification</span>
                  <h4 className="outcome-label">{selectedPrediction.predictedLabel}</h4>
                  <span className="outcome-class-code">
                    Output Class: <strong>{selectedPrediction.predictedClass}</strong> ({selectedPrediction.predictedClass === 1 ? 'Positive event: mortality risk predicted' : 'Negative event: no mortality predicted'})
                  </span>
                </div>
              </div>

              {/* Probability Card */}
              <div className="probability-metric-card">
                <div className="metric-header-row">
                  <div>
                    <span className="metric-heading">Calculated Mortality Probability</span>
                    <p className="metric-subheading">Inference score from input biomarkers</p>
                  </div>
                  <span className={`metric-percentage ${selectedPrediction.predictedProbability >= 0.5 ? 'elevated' : 'baseline'}`}>
                    {(selectedPrediction.predictedProbability * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="clean-progress-track">
                  <div
                    className={`clean-progress-fill ${selectedPrediction.predictedProbability >= 0.5 ? 'fill-elevated' : 'fill-baseline'}`}
                    style={{ width: `${Math.min(100, Math.max(0, selectedPrediction.predictedProbability * 100))}%` }}
                  />
                </div>
                <div className="metric-scale-labels" aria-hidden="true">
                  <span>0% (Baseline)</span>
                  <span className="threshold-indicator">50% Decision Threshold</span>
                  <span>100% (Maximum)</span>
                </div>
              </div>

              {/* Meta Specs Table */}
              <div className="result-meta-table">
                <div className="meta-row">
                  <span className="meta-label">Selected Model Architecture</span>
                  <span className="meta-value">{selectedPrediction.modelName}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Raw Probability Output</span>
                  <span className="meta-value font-mono">{selectedPrediction.predictedProbability}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Classification Cutoff Threshold</span>
                  <span className="meta-value font-mono">0.50 (50.0%)</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Inference Execution Timestamp</span>
                  <span className="meta-value font-mono">{selectedPrediction.displayCreatedAt}</span>
                </div>
                <div className="meta-row">
                  <span className="meta-label">Pipeline Version</span>
                  <span className="meta-value font-mono">{selectedPrediction.modelVersion || 'v1.0.0'}</span>
                </div>
              </div>

              {/* Clinical Distinctions Warning */}
              <div className="clean-disclaimer-box" role="note">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                <p>
                  <strong>Clinical Model Interpretation:</strong> Predicted class represents the binary model output relative to the 0.50 cutoff threshold. It is an algorithmic estimate derived from the UCI research dataset and does not constitute a certified clinical diagnosis or autonomous medical recommendation.
                </p>
              </div>

              {/* Toggleable Associated 11 Clinical Input Parameters */}
              <div className="associated-inputs-card">
                <div className="inputs-card-header">
                  <div>
                    <h4 className="inputs-card-title">Associated 11 Clinical Biomarkers</h4>
                    <p className="inputs-card-desc">Exact parameters submitted during this inference execution</p>
                  </div>
                  <button
                    type="button"
                    className="btn-dash-secondary btn-sm"
                    onClick={() => setShowInputParams(!showInputParams)}
                  >
                    {showInputParams ? 'Hide Biomarkers' : 'View Biomarkers'}
                  </button>
                </div>

                {showInputParams && selectedPrediction.inputs && (
                  <div className="inputs-grid-display">
                    <div className="input-param-chip">
                      <span className="param-kicker">Age</span>
                      <span className="param-num">{selectedPrediction.inputs.age} yrs</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Ejection Fraction</span>
                      <span className="param-num">{selectedPrediction.inputs.ejection_fraction}%</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Serum Creatinine</span>
                      <span className="param-num">{selectedPrediction.inputs.serum_creatinine} mg/dL</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Serum Sodium</span>
                      <span className="param-num">{selectedPrediction.inputs.serum_sodium} mEq/L</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Platelets</span>
                      <span className="param-num">{Number(selectedPrediction.inputs.platelets).toLocaleString()} cells/µL</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">CPK</span>
                      <span className="param-num">{selectedPrediction.inputs.creatinine_phosphokinase} mcg/L</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Sex</span>
                      <span className="param-num">{selectedPrediction.inputs.sex === 1 ? 'Male (1)' : 'Female (0)'}</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Anaemia</span>
                      <span className="param-num">{selectedPrediction.inputs.anaemia === 1 ? 'Yes (1)' : 'No (0)'}</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Diabetes</span>
                      <span className="param-num">{selectedPrediction.inputs.diabetes === 1 ? 'Yes (1)' : 'No (0)'}</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">High BP</span>
                      <span className="param-num">{selectedPrediction.inputs.high_blood_pressure === 1 ? 'Yes (1)' : 'No (0)'}</span>
                    </div>
                    <div className="input-param-chip">
                      <span className="param-kicker">Smoking</span>
                      <span className="param-num">{selectedPrediction.inputs.smoking === 1 ? 'Yes (1)' : 'No (0)'}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="clinical-modal-footer">
              <button
                type="button"
                className="btn-dash-secondary"
                onClick={() => setSelectedPrediction(null)}
              >
                Close Details
              </button>
              <button
                type="button"
                className="btn-dash-primary"
                onClick={() => {
                  if (onSelectAssessment) {
                    onSelectAssessment(selectedPrediction.assessmentCode)
                  }
                  onNavigate('assessments')
                }}
              >
                <span>View Full Assessment in Directory &rarr;</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Confirm Delete Modal */}
      {predictionToDelete && (
        <div className="clinical-modal-backdrop" onClick={() => setPredictionToDelete(null)}>
          <div
            className="clinical-modal-content confirm-modal-style"
            onClick={(e) => e.stopPropagation()}
            role="alertdialog"
            aria-labelledby="confirm-pred-del-title"
          >
            <div className="confirm-icon-danger" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h3 id="confirm-pred-del-title" className="confirm-title">
              Delete Prediction Log {predictionToDelete.predictionCode}?
            </h3>
            <p className="confirm-desc">
              Are you sure you want to permanently delete this prediction execution record? The parent assessment will remain intact.
            </p>
            <div className="confirm-actions-row">
              <button
                type="button"
                className="btn-dash-secondary"
                onClick={() => setPredictionToDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger-confirm"
                onClick={handleConfirmDelete}
              >
                Delete Log
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

