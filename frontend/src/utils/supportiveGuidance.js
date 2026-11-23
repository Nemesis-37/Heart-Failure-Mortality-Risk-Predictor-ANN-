/**
 * supportiveGuidance.js
 * =====================
 * Generates tailored, compassionate supportive guidance messages based on the
 * predicted 30-day death-event probability from either Logistic Regression or ANN.
 * 
 * Probability bands (20 separate 5-percentage-point increments):
 * - 0–4.99%   - 5–9.99%   - 10–14.99%  - 15–19.99%  - 20–24.99%
 * - 25–29.99% - 30–34.99% - 35–39.99%  - 40–44.99%  - 45–49.99%
 * - 50–54.99% - 55–59.99% - 60–64.99%  - 65–69.99%  - 70–74.99%
 * - 75–79.99% - 80–84.99% - 85–89.99%  - 90–94.99%  - 95–100%
 * 
 * Medical Safety Governance:
 * - Supportive educational text only; never represents a guaranteed prognosis or diagnosis.
 * - Does not promise survival/recovery or predict death.
 * - Never suggests altering, delaying, or discontinuing medications without physician guidance.
 * - Directs patients to review findings with their treating physician and seek urgent care for severe symptoms.
 */

export const SUPPORTIVE_BANDS = [
  {
    range: [0, 4.999],
    label: '0.00% – 4.99%',
    category: 'Lower Probability Band',
    icon: '🌱',
    accentColor: '#10B981', // Emerald
    accentBg: 'rgba(16, 185, 129, 0.12)',
    headline: 'Encouraging Baseline Profile & Preventive Health Engagement',
    message:
      'This estimated probability reflects a reassuring baseline profile within this educational cohort model. Encourage the patient to celebrate this foundation by maintaining nutritious dietary habits, regular daily movement, and taking all prescribed medications exactly as directed. Emphasize that ongoing preventive care, routine laboratory monitoring, and regular physician consultations remain essential to preserve long-term cardiovascular resilience.',
    practicalFocus: [
      'Reinforce daily medication compliance and consistent sleep routines.',
      'Encourage a nutrient-rich, low-sodium dietary pattern.',
      'Maintain scheduled outpatient wellness reviews with the clinical team.',
    ],
  },
  {
    range: [5, 9.999],
    label: '5.00% – 9.99%',
    category: 'Lower Probability Band',
    icon: '🌿',
    accentColor: '#14B8A6', // Teal
    accentBg: 'rgba(20, 184, 166, 0.12)',
    headline: 'Favorable Health Foundations with Active Daily Vigilance',
    message:
      'Initial clinical indicators present a favorable outlook. Reassure the patient of the value of their daily health habits while gently highlighting that cardiovascular stability requires steady, lifelong attention. Support them in sticking strictly to their personalized care schedule, managing daily stress levels, and attending all upcoming follow-up appointments to track biomarker progress.',
    practicalFocus: [
      'Prioritize structured, gentle daily activities such as brisk walking.',
      'Continue consistent self-monitoring and keep an updated medication list.',
      'Discuss routine blood pressure and metabolic trends during checkups.',
    ],
  },
  {
    range: [10, 14.999],
    label: '10.00% – 14.99%',
    category: 'Lower Probability Band',
    icon: '💧',
    accentColor: '#0EA5E9', // Sky Blue
    accentBg: 'rgba(14, 165, 233, 0.12)',
    headline: 'Positive Preventive Momentum with Regular Clinical Check-ins',
    message:
      'A constructive preventive baseline is evident. Support the patient in continuing their proactive self-care routines, balancing physical exercise with restorative sleep, and taking medications conscientiously. Remind them that scheduled clinical assessments enable timely adjustments to therapy, ensuring their heart receives optimal ongoing support.',
    practicalFocus: [
      'Maintain steady hydration and avoid heavy late-night dinners.',
      'Record daily blood pressure readings to share with the care team.',
      'Adhere strictly to all physician guidance and prescription intervals.',
    ],
  },
  {
    range: [15, 19.999],
    label: '15.00% – 19.99%',
    category: 'Lower-Moderate Probability Band',
    icon: '🛡️',
    accentColor: '#0284C7', // Blue
    accentBg: 'rgba(2, 132, 199, 0.12)',
    headline: 'Stable Foundation with Focus on Lifestyle Consistency',
    message:
      'The calculated risk score indicates a stable baseline, providing a great opportunity to reinforce healthy cardiovascular choices. Encourage the patient to actively discuss heart-healthy dietary adjustments, sodium moderation, and daily activity goals with their physician. Consistent partnership with healthcare providers ensures steady, sustained well-being.',
    practicalFocus: [
      'Focus on whole foods, fresh vegetables, and limiting processed items.',
      'Incorporate structured rest periods to buffer emotional distress.',
      'Promptly mention any new or unusual feelings of fatigue during checkups.',
    ],
  },
  {
    range: [20, 24.999],
    label: '20.00% – 24.99%',
    category: 'Lower-Moderate Probability Band',
    icon: '✨',
    accentColor: '#38BDF8', // Light Sky
    accentBg: 'rgba(56, 189, 248, 0.12)',
    headline: 'Constructive Clinical Partnership & Proactive Self-Monitoring',
    message:
      'Acknowledge the patient\'s commitment to their cardiac health. This probability band underscores the practical benefits of daily routine consistency—including scheduled medication intake, mindful stress reduction, and monitoring daily weight. Encourage the patient to view routine follow-ups as a collaborative setting to celebrate progress and address questions.',
    practicalFocus: [
      'Log daily home blood pressure measurements in a personal journal or app.',
      'Discuss achievable physical activity milestones with the healthcare team.',
      'Maintain strong communication with family members and caregivers.',
    ],
  },
  {
    range: [25, 29.999],
    label: '25.00% – 29.99%',
    category: 'Moderate Probability Band',
    icon: '🧭',
    accentColor: '#6366F1', // Indigo
    accentBg: 'rgba(99, 102, 241, 0.12)',
    headline: 'Opportunity for Health Optimization & Personalized Guidance',
    message:
      'This estimate presents a constructive opportunity for targeted health optimization. Encourage the patient to review daily routines openly with their treating physician. Concentrating on practical, achievable improvements—such as daily walking intervals, dietary refinement, and reliable medication schedules—delivers meaningful cardiovascular protection.',
    practicalFocus: [
      'Collaborate with the doctor to review guideline-directed treatment targets.',
      'Adopt the "Half-Plate Rule" for meals (half produce, one-quarter lean protein, one-quarter whole grain).',
      'Ensure uninterrupted nocturnal sleep of 7 to 8 hours.',
    ],
  },
  {
    range: [30, 34.999],
    label: '30.00% – 34.99%',
    category: 'Moderate Probability Band',
    icon: '🔍',
    accentColor: '#8B5CF6', // Violet
    accentBg: 'rgba(139, 92, 246, 0.12)',
    headline: 'Active Monitoring & Mindful Health Partnership',
    message:
      'Careful ongoing monitoring is beneficial. Advise the patient to review these model estimates in the context of their comprehensive medical history with their physician. Consistent medication adherence, balanced hydration, and routine clinical checkups form the cornerstone of ongoing stability and vitality.',
    practicalFocus: [
      'Never skip or adjust prescription doses without clinical consultation.',
      'Engage in gentle, physician-cleared aerobic conditioning (e.g. daily walking).',
      'Keep a written list of symptoms and questions ready for clinical appointments.',
    ],
  },
  {
    range: [35, 39.999],
    label: '35.00% – 39.99%',
    category: 'Moderate Probability Band',
    icon: '📊',
    accentColor: '#A855F7', // Purple
    accentBg: 'rgba(168, 85, 247, 0.12)',
    headline: 'Attentive Care Engagement & Goal-Directed Progress',
    message:
      'Encourage the patient to take active ownership of their cardiovascular journey by discussing clinical biomarker trends with their care team. Sustained adherence to prescribed regimens and sensible daily activity modifications make a tangible difference over time in supporting heart function.',
    practicalFocus: [
      'Monitor fluid intake and dietary sodium closely (< 2,000 mg/day).',
      'Track morning weight after waking to catch early fluid accumulation.',
      'Practice deep breathing or mindfulness techniques to modulate autonomic tone.',
    ],
  },
  {
    range: [40, 44.999],
    label: '40.00% – 44.99%',
    category: 'Moderate-Elevated Probability Band',
    icon: '🩺',
    accentColor: '#EC4899', // Pink
    accentBg: 'rgba(236, 72, 153, 0.12)',
    headline: 'Focused Clinical Collaboration & Supportive Interventions',
    message:
      'Thoughtful clinical collaboration is recommended. Encourage scheduling a dedicated consultation with the treating clinician to examine individualized therapy targets. Structured medical care, symptom vigilance, and positive caregiver encouragement strongly reinforce cardiovascular stability.',
    practicalFocus: [
      'Schedule a thorough outpatient medication review with the physician.',
      'Establish a clear daily medication tracking routine or pill organizer.',
      'Involve trusted family members in care planning and lifestyle modifications.',
    ],
  },
  {
    range: [45, 49.999],
    label: '45.00% – 49.99%',
    category: 'Moderate-Elevated Probability Band',
    icon: '⚖️',
    accentColor: '#F59E0B', // Amber
    accentBg: 'rgba(245, 158, 11, 0.12)',
    headline: 'Approaching Clinical Threshold — Prioritize Multidisciplinary Review',
    message:
      'Approaching the standard 0.50 decision threshold highlights the value of focused clinical discussion. Encourage an open conversation with the physician regarding therapy optimization and lifestyle enhancements. Reinforce that dedicated self-care, family support, and steady medical follow-up are powerful allies in maintaining wellness.',
    practicalFocus: [
      'Discuss potential medication titration or diagnostic updates with the doctor.',
      'Log home blood pressure twice daily under resting conditions.',
      'Seek prompt medical advice if experiencing unusual fatigue or ankle swelling.',
    ],
  },
  {
    range: [50, 54.999],
    label: '50.00% – 54.99%',
    category: 'Elevated Probability Band (Threshold Crossing)',
    icon: '🤝',
    accentColor: '#F97316', // Orange
    accentBg: 'rgba(249, 115, 22, 0.12)',
    headline: 'Elevated Risk Score — Collaborative Medical Partnership Is Key',
    message:
      'An elevated risk estimation indicates an important reason for timely clinical review. Recommend that the patient discuss these findings with their healthcare provider to review tailored care plans. Reassure them that modern cardiology offers robust therapies, structured surveillance, and supportive interventions dedicated to protecting quality of life.',
    practicalFocus: [
      'Arrange an in-person clinical consultation with the cardiology team.',
      'Follow guideline-directed medical therapies without interruption.',
      'Report any sudden overnight weight gain (>= 2 lbs) or shortness of breath.',
    ],
  },
  {
    range: [55, 59.999],
    label: '55.00% – 59.99%',
    category: 'Elevated Probability Band',
    icon: '💙',
    accentColor: '#FB923C', // Warm Orange
    accentBg: 'rgba(251, 146, 60, 0.12)',
    headline: 'Timely Clinical Attention & Compassionate Healthcare Partnership',
    message:
      'This risk estimate provides an important signal for collaborative medical attention. Encourage scheduling timely follow-up with the primary cardiology team. Emphasize the importance of consistent symptom logging and surrounding oneself with a supportive network of family and healthcare professionals.',
    practicalFocus: [
      'Prioritize routine outpatient cardiology check-ins and laboratory assessments.',
      'Maintain an open dialogue regarding energy levels, breathing, and comfort.',
      'Lean on family members, friends, or peer support groups for emotional strength.',
    ],
  },
  {
    range: [60, 64.999],
    label: '60.00% – 64.99%',
    category: 'Elevated Probability Band',
    icon: '🛡️',
    accentColor: '#38BDF8', // Cyan/Blue
    accentBg: 'rgba(56, 189, 248, 0.12)',
    headline: 'Proactive Medical Alignment & Dedicated Symptom Surveillance',
    message:
      'Proactive medical partnership is essential. Encourage a calm, thorough review with the treating physician to optimize guideline-directed medical therapy. Reassure the patient that active symptom surveillance, family involvement, and attentive clinical care can significantly enhance daily comfort and well-being.',
    practicalFocus: [
      'Keep a detailed daily log of vital signs, fluid intake, and sleep quality.',
      'Ensure clear knowledge of the clinic\'s daytime and after-hours contact numbers.',
      'Focus daily energy on restorative rest, gentle mobility, and stress reduction.',
    ],
  },
  {
    range: [65, 69.999],
    label: '65.00% – 69.99%',
    category: 'Elevated Probability Band',
    icon: '🕊️',
    accentColor: '#818CF8', // Indigo/Blue
    accentBg: 'rgba(129, 140, 248, 0.12)',
    headline: 'Compassionate Clinical Engagement & Quality of Life Focus',
    message:
      'A higher risk estimate highlights the need for focused healthcare support. Encourage reaching out to the cardiology clinic for a comprehensive, personalized evaluation. Focus discussions on symptom management, functional quality of life, and coordinated clinical guidance that respects personal preferences.',
    practicalFocus: [
      'Review all prescription dosages and potential interactions with the doctor.',
      'Establish a calm home environment that supports easy breathing and rest.',
      'Seek prompt medical evaluation if experiencing persistent chest fullness or dizziness.',
    ],
  },
  {
    range: [70, 74.999],
    label: '70.00% – 74.99%',
    category: 'Elevated Probability Band',
    icon: '🌟',
    accentColor: '#A78BFA', // Violet
    accentBg: 'rgba(167, 139, 250, 0.12)',
    headline: 'Comprehensive Healthcare Coordination & Active Support Networks',
    message:
      'Substantial clinical complexity is indicated. Reassure the patient that medical teams possess extensive clinical strategies to support cardiac function and ease symptoms. Encourage prompt follow-up, open communication with loved ones, and strict adherence to individualized physician instructions.',
    practicalFocus: [
      'Coordinate closely with the primary physician and heart failure specialists.',
      'Engage family members to assist with daily schedules and appointments.',
      'Prioritize daily comfort, emotional peace, and regular clinical monitoring.',
    ],
  },
  {
    range: [75, 79.999],
    label: '75.00% – 79.99%',
    category: 'High Priority Clinical Band',
    icon: '🩺',
    accentColor: '#38BDF8', // Sky Blue
    accentBg: 'rgba(56, 189, 248, 0.14)',
    headline: 'Dedicated Specialist Review & Multidisciplinary Care Alliance',
    message:
      'Prioritize a dedicated clinical consultation. Encourage the patient to arrange a detailed review with their cardiologist. Modern supportive cardiology provides comprehensive multidisciplinary care focused on symptom relief, functional stability, and attentive, personalized medical management.',
    practicalFocus: [
      'Schedule prompt in-person consultation with the treating cardiologist.',
      'Review electrolyte levels, renal biomarkers, and fluid status with the clinic.',
      'Communicate openly with family and care partners about supportive daily needs.',
    ],
  },
  {
    range: [80, 84.999],
    label: '80.00% – 84.99%',
    category: 'High Priority Clinical Band',
    icon: '🤍',
    accentColor: '#C084FC', // Light Purple
    accentBg: 'rgba(192, 132, 252, 0.14)',
    headline: 'Close, Compassionate Partnership & Attentive Daily Comfort',
    message:
      'This assessment warrants close, compassionate clinical engagement. Encourage the patient to share questions and feelings openly with their healthcare team and trusted family members. Emphasize that supportive medical care, diligent symptom monitoring, and individualized therapies are centered entirely on maximizing daily comfort and quality of life.',
    practicalFocus: [
      'Work collaboratively with physicians to optimize therapeutic comfort.',
      'Monitor and report any breathing difficulties while lying flat.',
      'Lean fully on healthcare professionals, social workers, and loving family.',
    ],
  },
  {
    range: [85, 89.999],
    label: '85.00% – 89.99%',
    category: 'High Priority Clinical Band',
    icon: '🤲',
    accentColor: '#60A5FA', // Soft Blue
    accentBg: 'rgba(96, 165, 250, 0.14)',
    headline: 'Attentive Comprehensive Support & Proactive Symptom Relief',
    message:
      'A significantly elevated risk estimate calls for attentive, comprehensive support. Advise connecting promptly with the treating physician to review all facets of cardiovascular care. Reassure the patient that compassionate multidisciplinary support, close family partnership, and proactive symptom relief remain steadfast clinical priorities.',
    practicalFocus: [
      'Contact the cardiology provider promptly to discuss tailored treatment options.',
      'Keep emergency medical phone numbers accessible to all household members.',
      'Emphasize emotional closeness, peaceful rest, and ongoing medical oversight.',
    ],
  },
  {
    range: [90, 94.999],
    label: '90.00% – 94.99%',
    category: 'High Priority Clinical Band',
    icon: '🕊️',
    accentColor: '#818CF8', // Periwinkle
    accentBg: 'rgba(129, 140, 248, 0.14)',
    headline: 'Continuous Specialized Partnership & Holistic Well-being',
    message:
      'This high-priority clinical context highlights the essential role of specialized healthcare providers. Remind the patient and family that statistical estimates reflect cohort trends, not personal destinies, and that compassionate clinical teams are deeply dedicated to optimizing comfort, vitality, and comprehensive symptom management.',
    practicalFocus: [
      'Maintain active daily communication with the specialized heart failure team.',
      'Ensure close observation for changes in breathing, edema, or mental alertness.',
      'Embrace family support and clinical guidance in navigating every decision.',
    ],
  },
  {
    range: [95, 100],
    label: '95.00% – 100.00%',
    category: 'High Priority Clinical Band',
    icon: '🕊️',
    accentColor: '#38BDF8', // Sky Blue
    accentBg: 'rgba(56, 189, 248, 0.16)',
    headline: 'Compassionate Clinical Prioritization & Dedicated Multidisciplinary Care',
    message:
      'This high statistical estimate underscores the vital importance of prompt, comprehensive review with the treating cardiologist. Statistical model calculations reflect retrospective group patterns and do not determine an individual\'s personal journey or replace tailored medical wisdom. Emphasize accessing all dimensions of specialized supportive care, surrounding oneself with loving family and trusted healthcare professionals, and focusing on quality of life and compassionate clinical partnership.',
    practicalFocus: [
      'Arrange immediate, comprehensive evaluation with the cardiac medical team.',
      'Engage specialized supportive care services for symptom alleviation and comfort.',
      'Foster peaceful, loving connection with family, friends, and care advocates.',
      'Seek emergency clinical services without hesitation if acute distress arises.',
    ],
  },
]

/**
 * Returns the exact supportive guidance object matching the predicted probability.
 * @param {number} probability - Probability value between 0.0 and 1.0 (or percentage 0 to 100).
 * @returns {object} The matched supportive guidance band.
 */
export function getSupportiveGuidance(probability) {
  if (probability === null || probability === undefined || isNaN(probability)) {
    return null
  }

  // Normalize: if passed as 0.0–1.0, convert to percentage 0–100
  let pct = Number(probability)
  if (pct > 0 && pct <= 1.0) {
    pct = pct * 100
  }

  // Clamp within [0, 100]
  pct = Math.max(0, Math.min(100, pct))

  for (let i = 0; i < SUPPORTIVE_BANDS.length; i++) {
    const band = SUPPORTIVE_BANDS[i]
    const [min, max] = band.range
    // For the last band (95–100), include 100 exactly
    if (i === SUPPORTIVE_BANDS.length - 1) {
      if (pct >= min && pct <= max) {
        return band
      }
    } else {
      if (pct >= min && pct < max) {
        return band
      }
    }
  }

  // Fallback to highest band if somehow outside
  return SUPPORTIVE_BANDS[SUPPORTIVE_BANDS.length - 1]
}
