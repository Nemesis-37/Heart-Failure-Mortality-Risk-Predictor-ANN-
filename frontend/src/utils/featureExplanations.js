/**
 * featureExplanations.js
 * ----------------------
 * Builds plain-language, dynamically generated explanations and safe,
 * non-prescriptive clinical review prompts from Logistic Regression
 * patient-specific feature contribution records returned by FastAPI.
 *
 * Medical Safety Governance:
 * - Never instructs changing lab values directly to alter predictions.
 * - Never recommends starting, stopping, or modifying medication dosages.
 * - Clearly distinguishes non-modifiable demographic context (age, sex).
 * - Frames contributions strictly as mathematical shifts in this model's output,
 *   never as causal mechanisms or treatment priorities.
 */

const FEATURE_SAFETY_GUIDANCE = {
  serum_creatinine: {
    relevancePositive:
      'In the training cohort, higher serum creatinine values weigh upward on the model estimate.',
    relevanceNegative:
      'In the training cohort, lower or moderate serum creatinine values weigh downward relative to the cohort average.',
    nextStep:
      'Suggest reviewing this result in the context of overall renal function, fluid balance, other laboratory findings, and the patient\'s clinical history with the treating clinician.',
  },
  ejection_fraction: {
    relevancePositive:
      'In the cohort Logistic Regression model, lower left ventricular ejection fraction values correspond to a positive shift in the model estimate.',
    relevanceNegative:
      'In the cohort Logistic Regression model, higher ejection fraction values carry a negative weight, shifting the model estimate downward.',
    nextStep:
      'Review this finding alongside echocardiographic imaging reports, symptom status, and clinical examination with the treating clinician.',
  },
  age: {
    relevancePositive:
      'Higher patient age receives a positive coefficient weight in the cohort model, pushing the statistical estimate upward.',
    relevanceNegative:
      'Younger patient age relative to the cohort average carries a downward offset relative to the model baseline.',
    nextStep:
      'Age is a non-modifiable contextual factor and cannot be changed. Interpret this estimate alongside the patient\'s overall clinical presentation and comorbidities.',
  },
  serum_sodium: {
    relevancePositive:
      'Lower serum sodium levels relative to the cohort average shift the Logistic Regression output upward because serum sodium has a negative cohort weight.',
    relevanceNegative:
      'Serum sodium values at or above the cohort average shift the model estimate downward relative to the baseline.',
    nextStep:
      'Interpret this measurement in the context of comprehensive electrolyte panels, clinical hydration status, and overall patient evaluation by the treating clinician.',
  },
  creatinine_phosphokinase: {
    relevancePositive:
      'Higher creatinine phosphokinase (CPK) values relative to the cohort mean push this statistical model\'s output upward.',
    relevanceNegative:
      'Lower CPK concentrations relative to the cohort mean weigh slightly downward on the model estimate.',
    nextStep:
      'Review CPK findings together with clinical history, symptoms, and complementary diagnostic investigations with the treating clinician.',
  },
  anaemia: {
    relevancePositive:
      'Documented anaemia carries a positive coefficient weight in the cohort model and shifts this prediction upward.',
    relevanceNegative:
      'Absence of anaemia shifts the statistical estimate downward relative to the cohort baseline.',
    nextStep:
      'Review hemoglobin trends, symptom profile, and contributing clinical history with the treating clinician.',
  },
  high_blood_pressure: {
    relevancePositive:
      'A documented history of high blood pressure contributes positively toward the model estimate relative to baseline.',
    relevanceNegative:
      'Absence of documented hypertension lowers this term relative to the cohort average baseline.',
    nextStep:
      'Review blood-pressure management, recent longitudinal blood-pressure readings, and routine care plans with the treating clinician.',
  },
  sex: {
    relevancePositive:
      'In this 299-patient cohort model, recorded biological sex shifted this term modestly upward relative to the cohort baseline.',
    relevanceNegative:
      'In this 299-patient cohort model, recorded biological sex shifted this term modestly downward relative to the cohort baseline.',
    nextStep:
      'Biological sex is a non-modifiable contextual demographic factor and cannot be changed. Interpret the model score in context of individual patient evaluation.',
  },
  diabetes: {
    relevancePositive:
      'Documented diabetes contributes a modest upward statistical adjustment relative to the cohort baseline.',
    relevanceNegative:
      'Absence of documented diabetes results in a slight downward adjustment relative to the cohort baseline.',
    nextStep:
      'Review diabetes management, glycemic history, and comprehensive metabolic follow-up with the treating clinician.',
  },
  platelets: {
    relevancePositive:
      'Lower platelet counts relative to the cohort mean produce a modest upward offset in this linear model.',
    relevanceNegative:
      'Higher or typical platelet counts relative to the cohort mean produce a modest downward offset in this linear model.',
    nextStep:
      'Review platelet count findings in the context of complete blood count trends and the patient\'s overall clinical history with the treating clinician.',
  },
  smoking: {
    relevancePositive:
      'Documented smoking history adds a small upward statistical adjustment relative to the cohort baseline.',
    relevanceNegative:
      'Absence of documented smoking history contributes a small downward adjustment relative to the cohort baseline.',
    nextStep:
      'Review smoking history and consider appropriate cessation support with the patient during clinical consultation.',
  },
}

function formatCohortMean(item) {
  if (item.cohort_mean === undefined || item.cohort_mean === null) return null
  if (item.feature_type === 'binary') {
    return `${(item.cohort_mean * 100).toFixed(0)}% cohort prevalence`
  }
  if (item.feature === 'platelets') {
    return `${Math.round(item.cohort_mean).toLocaleString()} ${item.unit}`
  }
  if (item.unit === '%') {
    return `${Number(item.cohort_mean).toFixed(1)}%`
  }
  return `${Number(item.cohort_mean).toFixed(2)} ${item.unit}`.trim()
}

export function buildFeatureExplanation(item) {
  const guidance = FEATURE_SAFETY_GUIDANCE[item.feature] || {
    relevancePositive: 'This parameter contributed positively toward the linear model score.',
    relevanceNegative: 'This parameter contributed negatively toward the linear model score.',
    nextStep:
      'Interpret this factor alongside the patient\'s complete medical history and diagnostic findings with the treating clinician.',
  }

  const contrib = Number(item.contribution || 0)
  const absMag = Math.abs(contrib)
  const isPositive = item.direction === 'positive' || contrib > 1e-9
  const isNegative = item.direction === 'negative' || contrib < -1e-9
  const isMinimal = absMag < 0.03

  const directionSummary = isPositive
    ? 'Increased the model-estimated probability.'
    : isNegative
      ? 'Decreased the model-estimated probability.'
      : 'Minimal contribution near the model baseline.'

  const shortDirectionLabel = isPositive
    ? 'Pushed estimate ↑'
    : isNegative
      ? 'Pushed estimate ↓'
      : 'Near baseline'

  const cohortRef = formatCohortMean(item)
  const signedContrib = `${contrib >= 0 ? '+' : ''}${contrib.toFixed(3)}`

  let whyItMatters = ''
  const valueSentence =
    item.feature_type === 'binary'
      ? `For this patient, ${item.label.toLowerCase()} is recorded as ${item.display_value}.`
      : `For this patient, the entered ${item.label.toLowerCase()} is ${item.display_value}${cohortRef ? ` (cohort average: ${cohortRef})` : ''}.`

  if (isMinimal) {
    whyItMatters = `${valueSentence} Because this value lies close to the cohort baseline, it had only a minor net effect (${signedContrib} log-odds) on this specific Logistic Regression output.`
  } else if (isPositive) {
    whyItMatters = `${valueSentence} ${guidance.relevancePositive} Together, this contributed ${signedContrib} toward the linear risk score, moving the model's estimate upward for this patient.`
  } else {
    whyItMatters = `${valueSentence} ${guidance.relevanceNegative} Together, this contributed ${signedContrib} to the linear risk score, shifting the model's estimate downward for this patient.`
  }

  return {
    directionSummary,
    shortDirectionLabel,
    signedContrib,
    absFormatted: absMag.toFixed(3),
    whyItMatters,
    clinicalNextStep: guidance.nextStep,
    strengthTag:
      absMag >= 0.45
        ? 'Major contributor'
        : absMag >= 0.15
          ? 'Moderate contributor'
          : 'Minor contributor',
  }
}
