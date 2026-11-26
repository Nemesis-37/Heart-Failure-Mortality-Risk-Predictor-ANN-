import React, { useState } from 'react'
import { buildFeatureExplanation } from '../utils/featureExplanations.js'

const ORDERED_INPUT_META = [
  { key: 'age', label: 'Age', unit: 'years', format: (v) => `${v} years` },
  { key: 'sex', label: 'Biological Sex', unit: '', format: (v) => (Number(v) === 1 ? 'Male (1)' : 'Female (0)') },
  { key: 'ejection_fraction', label: 'Ejection Fraction', unit: '%', format: (v) => `${v}%` },
  { key: 'serum_creatinine', label: 'Serum Creatinine', unit: 'mg/dL', format: (v) => `${v} mg/dL` },
  { key: 'serum_sodium', label: 'Serum Sodium', unit: 'mEq/L', format: (v) => `${v} mEq/L` },
  { key: 'platelets', label: 'Platelets', unit: 'cells/µL', format: (v) => `${Number(v).toLocaleString()} cells/µL` },
  { key: 'creatinine_phosphokinase', label: 'Creatinine Phosphokinase', unit: 'mcg/L', format: (v) => `${Number(v).toLocaleString()} mcg/L` },
  { key: 'anaemia', label: 'Anaemia', unit: '', format: (v) => (Number(v) === 1 ? 'Present (1)' : 'Absent (0)') },
  { key: 'diabetes', label: 'Diabetes', unit: '', format: (v) => (Number(v) === 1 ? 'Yes (1)' : 'No (0)') },
  { key: 'high_blood_pressure', label: 'High Blood Pressure', unit: '', format: (v) => (Number(v) === 1 ? 'Yes (1)' : 'No (0)') },
  { key: 'smoking', label: 'Smoking History', unit: '', format: (v) => (Number(v) === 1 ? 'Yes (1)' : 'No (0)') },
]

function ProbabilityRadialGauge({ probability }) {
  const clamped = Math.min(1, Math.max(0, Number(probability) || 0))
  const pct = clamped * 100
  const isElevated = clamped >= 0.5

  const size = 216
  const strokeWidth = 16
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference * (1 - clamped)

  // Indicator dot position along the circular arc (starting top center = -90deg)
  const angleRad = (-90 + clamped * 360) * (Math.PI / 180)
  const cx = size / 2
  const cy = size / 2
  const dotX = cx + radius * Math.cos(angleRad)
  const dotY = cy + radius * Math.sin(angleRad)

  // Threshold marker at 50% (bottom of circle = +90deg)
  const threshX1 = cx
  const threshY1 = cy + radius - strokeWidth * 0.55
  const threshX2 = cx
  const threshY2 = cy + radius + strokeWidth * 0.55

  const accentStroke = isElevated ? '#DC2626' : '#16A34A'

  return (
    <div className="pr-gauge-wrapper">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="pr-gauge-svg"
        role="img"
        aria-label={`Model-estimated probability gauge showing ${pct.toFixed(1)}%`}
      >
        {/* Background Track Ring */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          className="pr-gauge-track"
          strokeWidth={strokeWidth}
        />

        {/* Progress Arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={accentStroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: 'stroke-dashoffset 600ms cubic-bezier(0.22, 1, 0.36, 1)' }}
        />

        {/* 50% Classification Threshold Marker Tick */}
        <line
          x1={threshX1}
          y1={threshY1}
          x2={threshX2}
          y2={threshY2}
          className="pr-gauge-threshold-tick"
          strokeWidth="2.5"
          strokeLinecap="round"
        />

        {/* Active Arc Endpoint Indicator */}
        {clamped > 0 && (
          <circle
            cx={dotX}
            cy={dotY}
            r={5}
            fill="#FFFFFF"
            stroke={accentStroke}
            strokeWidth={3}
          />
        )}
      </svg>

      <div className="pr-gauge-center">
        <span className="pr-gauge-kicker">Model-Estimated Probability</span>
        <span className={`pr-gauge-pct ${isElevated ? 'is-elevated' : 'is-lower'}`}>
          {pct.toFixed(1)}%
        </span>
        <span className="pr-gauge-raw font-mono">
          p = {clamped.toFixed(4)}
        </span>
      </div>
    </div>
  )
}

export default function PredictionResultsPage({
  resultState,
  onBackToForm,
  onNewAssessment,
}) {
  const [showAllExplanations, setShowAllExplanations] = useState(false)
  const [inputsExpanded, setInputsExpanded] = useState(false)

  if (!resultState || !resultState.predictionResponse) {
    return (
      <div className="pr-page-container">
        <div className="pr-empty-card">
          <h2>No Prediction Result Loaded</h2>
          <p>
            Please complete the Patient Risk Assessment form and click <strong>Generate Prediction</strong> to review model estimates and factor contributions.
          </p>
          <button type="button" className="btn-primary" onClick={onNewAssessment}>
            Go to Patient Risk Assessment
          </button>
        </div>
      </div>
    )
  }

  const {
    predictionResponse: resp,
    patientInputs,
    patientRef,
    assessmentCode,
    predictionCode,
    displayTimestamp,
  } = resultState

  const probability = Number(resp.predicted_probability ?? 0)
  const threshold = Number(resp.threshold ?? 0.5)
  const predictedClass = Number(resp.predicted_class ?? (probability >= threshold ? 1 : 0))
  const isElevated = predictedClass === 1 || probability >= threshold

  const contributions = Array.isArray(resp.feature_contributions)
    ? resp.feature_contributions
    : []

  const maxAbsContribution = contributions.reduce(
    (acc, item) => Math.max(acc, Math.abs(Number(item.contribution || 0))),
    0
  )

  const sumContributions = contributions.reduce(
    (acc, item) => acc + Number(item.contribution || 0),
    0
  )

  const visibleExplanations = showAllExplanations
    ? contributions
    : contributions.slice(0, 6)

  const positiveCount = contributions.filter((c) => Number(c.contribution) > 1e-9).length
  const negativeCount = contributions.filter((c) => Number(c.contribution) < -1e-9).length

  const formattedTime =
    displayTimestamp ||
    (resp.prediction_timestamp
      ? new Date(resp.prediction_timestamp).toLocaleString([], {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      : new Date().toLocaleString())

  return (
    <div className="pr-page-container">
      {/* Top Action & Identifier Header */}
      <div className="pr-top-nav-bar">
        <div className="pr-identifiers-group">
          <div className="pr-id-pill">
            <span className="pr-id-label">Patient ID</span>
            <span className="pr-id-value font-mono">{patientRef || resp.patient_reference_id || 'Unassigned'}</span>
          </div>
          {assessmentCode && (
            <div className="pr-id-pill">
              <span className="pr-id-label">Assessment</span>
              <span className="pr-id-value font-mono">{assessmentCode}</span>
            </div>
          )}
          {predictionCode && (
            <div className="pr-id-pill">
              <span className="pr-id-label">Record</span>
              <span className="pr-id-value font-mono">{predictionCode}</span>
            </div>
          )}
          <div className="pr-id-pill pr-time-pill">
            <span className="pr-id-label">Timestamp</span>
            <span className="pr-id-value font-mono">{formattedTime}</span>
          </div>
        </div>

        <div className="pr-nav-buttons">
          <button
            type="button"
            className="btn-dash-secondary pr-nav-btn"
            onClick={onBackToForm}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back to Patient Form</span>
          </button>
          <button
            type="button"
            className="btn-dash-primary pr-nav-btn"
            onClick={onNewAssessment}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>New Assessment</span>
          </button>
        </div>
      </div>

      {/* SECTION A — Main Prediction Result */}
      <section className="pr-hero-card" aria-label="Main Prediction Result">
        <div className="pr-hero-grid">
          <div className="pr-hero-gauge-col">
            <ProbabilityRadialGauge probability={probability} />
            <span className="pr-threshold-caption">
              Classification Threshold: {(threshold * 100).toFixed(0)}% ({threshold.toFixed(2)})
            </span>
          </div>

          <div className="pr-hero-details-col">
            <div className="pr-hero-eyebrow">Logistic Regression Cohort Output</div>
            <h2 className="pr-hero-heading">
              Model-Estimated Probability:{' '}
              <span className={isElevated ? 'pr-text-elevated' : 'pr-text-lower'}>
                {(probability * 100).toFixed(1)}%
              </span>
            </h2>

            <div className={`pr-classification-badge ${isElevated ? 'badge-elevated' : 'badge-lower'}`}>
              <span className="pr-status-dot" aria-hidden="true" />
              <div>
                <div className="pr-badge-title">
                  {isElevated
                    ? 'Elevated Model-Estimated Probability'
                    : 'Lower Model-Estimated Probability'}
                </div>
                <div className="pr-badge-sub">
                  Classification at {threshold.toFixed(2)} threshold: <strong>{resp.predicted_label}</strong> (Class {predictedClass})
                </div>
              </div>
            </div>

            <div className="pr-hero-metrics-strip">
              <div className="pr-mini-stat">
                <span className="pr-mini-label">Predicted Class</span>
                <span className="pr-mini-val font-mono">
                  {predictedClass} ({predictedClass === 1 ? '≥ 0.50' : '< 0.50'})
                </span>
              </div>
              <div className="pr-mini-stat">
                <span className="pr-mini-label">Factors Pushing ↑</span>
                <span className="pr-mini-val pr-text-elevated font-mono">{positiveCount} of {contributions.length}</span>
              </div>
              <div className="pr-mini-stat">
                <span className="pr-mini-label">Factors Pushing ↓</span>
                <span className="pr-mini-val pr-text-lower font-mono">{negativeCount} of {contributions.length}</span>
              </div>
            </div>

            {/* Required Concise Disclaimer */}
            <div className="pr-disclaimer-banner" role="note">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <p>
                This result is generated by an educational machine-learning prototype. It is not a diagnosis, clinically validated mortality estimate, or replacement for professional medical judgment.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION B — Most Influential Patient Features */}
      <section className="pr-section-card" aria-label="Factors Influencing This Prediction">
        <div className="pr-section-header">
          <div>
            <h2 className="pr-section-title">Factors Influencing This Prediction</h2>
            <p className="pr-section-subtitle">
              Features are ranked by individual contribution magnitude for this patient using the fitted model coefficients and standardized inputs.
            </p>
          </div>
          <div className="pr-chart-legend" aria-label="Contribution Direction Legend">
            <span className="pr-legend-item">
              <span className="pr-legend-swatch swatch-neg" aria-hidden="true" />
              <span>Decreased estimate (↓)</span>
            </span>
            <span className="pr-legend-item">
              <span className="pr-legend-swatch swatch-pos" aria-hidden="true" />
              <span>Increased estimate (↑)</span>
            </span>
          </div>
        </div>

        <p className="pr-interpretation-note">
          Positive bars (red) indicate values that pushed this model estimate upward relative to the cohort baseline. Negative bars (green) pushed it downward. Contributions describe mathematical model behavior only and do not establish biological causation.
        </p>

        {contributions.length === 0 ? (
          <div className="pr-missing-contrib-notice">
            Feature contribution data was not included in this prediction payload.
          </div>
        ) : (
          <>
            <div className="pr-diverging-chart" role="list" aria-label="Feature contributions bar chart">
              <div className="pr-chart-axis-header" aria-hidden="true">
                <span>Feature &amp; Patient Value</span>
                <div className="pr-axis-labels">
                  <span>← Pushed Downward</span>
                  <span>Baseline (0)</span>
                  <span>Pushed Upward →</span>
                </div>
                <span className="pr-axis-right-hdr">Contribution (Log-Odds)</span>
              </div>

              {contributions.map((item, idx) => {
                const contrib = Number(item.contribution || 0)
                const isPos = contrib > 1e-9
                const isNeg = contrib < -1e-9
                const ratio = maxAbsContribution > 0 ? Math.min(1, Math.abs(contrib) / maxAbsContribution) : 0
                const halfBarPct = Math.max(ratio * 48, Math.abs(contrib) > 0.005 ? 2.5 : 0)

                return (
                  <div className="pr-chart-row" key={item.feature} role="listitem">
                    <div className="pr-chart-feature-col">
                      <span className="pr-chart-rank">#{idx + 1}</span>
                      <div className="pr-chart-feature-info">
                        <span className="pr-chart-feature-name">{item.label}</span>
                        <span className="pr-chart-patient-val">{item.display_value}</span>
                      </div>
                    </div>

                    <div className="pr-chart-track-col" aria-hidden="true">
                      <div className="pr-chart-diverging-track">
                        <div className="pr-chart-zero-line" />
                        {isNeg && (
                          <div
                            className="pr-chart-bar bar-negative"
                            style={{
                              width: `${halfBarPct}%`,
                              right: '50%',
                            }}
                          />
                        )}
                        {isPos && (
                          <div
                            className="pr-chart-bar bar-positive"
                            style={{
                              width: `${halfBarPct}%`,
                              left: '50%',
                            }}
                          />
                        )}
                      </div>
                    </div>

                    <div className="pr-chart-impact-col">
                      <span className={`pr-impact-val font-mono ${isPos ? 'is-pos' : isNeg ? 'is-neg' : 'is-neutral'}`}>
                        {contrib >= 0 ? '+' : ''}
                        {contrib.toFixed(3)}
                      </span>
                      <span className="pr-impact-dir">
                        {isPos ? 'Pushed ↑' : isNeg ? 'Pushed ↓' : 'Neutral'}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>

            {resp.baseline_intercept !== undefined && resp.logit !== undefined && (
              <div className="pr-math-reconstruct-bar">
                <span>
                  Model Linear Reconstruction: Baseline Intercept{' '}
                  <strong className="font-mono">{Number(resp.baseline_intercept).toFixed(4)}</strong>
                  {' + '}Sum of 11 Contributions{' '}
                  <strong className="font-mono">
                    {sumContributions >= 0 ? '+' : ''}
                    {sumContributions.toFixed(4)}
                  </strong>
                  {' = '}Linear Score (Logit){' '}
                  <strong className="font-mono">{Number(resp.logit).toFixed(4)}</strong>
                  {' → '}Probability{' '}
                  <strong className="font-mono">{(probability * 100).toFixed(1)}%</strong>
                </span>
              </div>
            )}
          </>
        )}
      </section>

      {/* SECTION C — Feature-wise Explanations and Clinical Context */}
      {contributions.length > 0 && (
        <section className="pr-section-card" aria-label="Feature-wise Explanations and Next Steps">
          <div className="pr-section-header">
            <div>
              <h2 className="pr-section-title">Feature-Wise Explanations &amp; Clinical Review</h2>
              <p className="pr-section-subtitle">
                Ordered from highest to lowest contribution magnitude for this assessment. Prompts below are general, non-prescriptive review guides for the clinical team.
              </p>
            </div>
            {contributions.length > 6 && (
              <button
                type="button"
                className="btn-dash-secondary pr-toggle-cards-btn"
                onClick={() => setShowAllExplanations((prev) => !prev)}
              >
                {showAllExplanations
                  ? 'Show Top 6 Influential Factors'
                  : `Show All ${contributions.length} Factors`}
              </button>
            )}
          </div>

          <div className="pr-explanations-grid">
            {visibleExplanations.map((item, idx) => {
              const exp = buildFeatureExplanation(item)
              const contrib = Number(item.contribution || 0)
              const isPos = contrib > 1e-9
              const isNeg = contrib < -1e-9

              return (
                <article
                  key={item.feature}
                  className={`pr-exp-card ${isPos ? 'card-pos' : isNeg ? 'card-neg' : 'card-neutral'}`}
                >
                  <div className="pr-exp-card-top">
                    <div>
                      <div className="pr-exp-rank-row">
                        <span className="pr-exp-rank-badge">#{idx + 1}</span>
                        <span className="pr-exp-strength">{exp.strengthTag}</span>
                      </div>
                      <h3 className="pr-exp-title">{item.label}</h3>
                    </div>
                    <div className="pr-exp-val-chip">
                      <span className="pr-exp-val-label">Patient value</span>
                      <strong className="pr-exp-val-text">{item.display_value}</strong>
                    </div>
                  </div>

                  <div className={`pr-exp-direction-row ${isPos ? 'dir-pos' : isNeg ? 'dir-neg' : 'dir-neutral'}`}>
                    <span className="pr-dir-indicator" aria-hidden="true" />
                    <span className="pr-dir-text">{exp.directionSummary}</span>
                    <span className="pr-dir-mag font-mono">
                      Impact: {exp.signedContrib} (|{exp.absFormatted}|)
                    </span>
                  </div>

                  <div className="pr-exp-block">
                    <h4>Why it matters in this prediction</h4>
                    <p>{exp.whyItMatters}</p>
                  </div>

                  <div className="pr-exp-block pr-next-step-block">
                    <h4>Clinical Review / Next Step</h4>
                    <p>{exp.clinicalNextStep}</p>
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      )}

      {/* Additional Component 1: Collapsible Patient Input Summary */}
      <section className="pr-section-card pr-compact-section" aria-label="Patient Input Summary">
        <button
          type="button"
          className="pr-collapse-header"
          onClick={() => setInputsExpanded((prev) => !prev)}
          aria-expanded={inputsExpanded}
        >
          <div>
            <h2 className="pr-section-title">Patient Input Summary (11 Features Used)</h2>
            <p className="pr-section-subtitle">
              {inputsExpanded
                ? 'Click to collapse the complete entered biomarker profile'
                : 'Click to inspect all 11 entered patient values transmitted for this calculation'}
            </p>
          </div>
          <span className="pr-collapse-pill">
            {inputsExpanded ? 'Hide Inputs ▲' : 'View All 11 Inputs ▼'}
          </span>
        </button>

        {inputsExpanded && patientInputs && (
          <div className="pr-inputs-summary-grid">
            {ORDERED_INPUT_META.map((meta) => (
              <div key={meta.key} className="pr-summary-cell">
                <span className="pr-summary-label">{meta.label}</span>
                <span className="pr-summary-val font-mono">
                  {patientInputs[meta.key] !== undefined && patientInputs[meta.key] !== null
                    ? meta.format(patientInputs[meta.key])
                    : '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Additional Component 2 & 3: Model Explanation & Bottom Navigation */}
      <section className="pr-footer-card" aria-label="Model Methodology and Navigation">
        <div className="pr-model-note">
          <div className="pr-model-note-badge">Logistic Regression Pipeline</div>
          <p>
            This assessment uses a Logistic Regression model. The feature contribution chart explains how the entered patient values influenced this particular model output.
          </p>
        </div>

        <div className="pr-nav-buttons">
          <button
            type="button"
            className="btn-dash-secondary pr-nav-btn"
            onClick={onBackToForm}
          >
            Back to Patient Form
          </button>
          <button
            type="button"
            className="btn-dash-primary pr-nav-btn"
            onClick={onNewAssessment}
          >
            New Assessment
          </button>
        </div>
      </section>
    </div>
  )
}
