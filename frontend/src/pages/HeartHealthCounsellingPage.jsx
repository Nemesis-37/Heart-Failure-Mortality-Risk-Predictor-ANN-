import React, { useState } from 'react'

export default function HeartHealthCounsellingPage({ onNavigate }) {
  const [activeCategory, setActiveCategory] = useState('nutrition')
  const [checkedPoints, setCheckedPoints] = useState({})

  const toggleCheck = (id) => {
    setCheckedPoints((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const categories = [
    {
      id: 'nutrition',
      code: 'A',
      title: 'Healthy Nutrition',
      tagline: 'Wholesome dietary foundations to nourish the myocardium and protect blood vessels',
      icon: '🥗',
      accent: '#16A34A',
      accentBg: '#DCFCE7',
      counsellingPoints: [
        {
          id: 'nut_balanced',
          title: 'Embrace a Balanced, Varied Diet',
          explanation: 'Guide patients towards balanced plates composed of fresh produce, lean proteins, and complex carbohydrates. Balanced nutrition provides essential micronutrients and antioxidants that reduce systemic vascular inflammation.',
          counsellingTip: 'Suggest the "Half-Plate Rule": Fill half the meal with vegetables/greens, one quarter with lean protein, and one quarter with whole grains.',
        },
        {
          id: 'nut_produce',
          title: 'Prioritize Colorful Fruits and Vegetables',
          explanation: 'Encourage consumption of a vibrant spectrum of seasonal vegetables and fresh fruits. These are naturally rich in potassium, dietary fiber, and polyphenols which naturally support blood pressure regulation.',
          counsellingTip: 'Aim for at least 4 to 5 servings daily. Recommend fresh, steamed, or raw over deep-fried or battered.',
        },
        {
          id: 'nut_grains',
          title: 'Choose Whole Grains over Refined Carbohydrates',
          explanation: 'Opting for whole oats, brown rice, barley, quinoa, and whole-wheat breads sustains steady blood glucose levels and supplies soluble fibers that help lower circulating LDL cholesterol.',
          counsellingTip: 'Advise patients to check labels and ensure "whole grain" is listed as the very first ingredient on cereal and bread packaging.',
        },
        {
          id: 'nut_salt',
          title: 'Limit Excess Dietary Sodium (Salt)',
          explanation: 'Excessive dietary sodium causes fluid retention in the circulatory system, forcing the myocardium to work harder against elevated vascular pressures and worsening heart failure symptoms.',
          counsellingTip: 'Recommend keeping total sodium under 2,000 mg/day (about 1 level teaspoon). Advise replacing table salt with fresh herbs, lemon juice, garlic, and aromatic spices.',
        },
        {
          id: 'nut_fats',
          title: 'Limit Saturated and Trans Fats',
          explanation: 'Minimizing intake of hydrogenated oils, trans fats, fatty cuts of red meat, full-fat dairy, and commercial baked goods prevents atherogenic plaque accumulation in coronary arteries.',
          counsellingTip: 'Substitute with heart-healthy monounsaturated and polyunsaturated fats from olive oil, avocados, nuts, seeds, and omega-3-rich fish.',
        },
        {
          id: 'nut_habits',
          title: 'Cultivate Mindful Eating Habits',
          explanation: 'Eating slowly, chewing thoroughly, paying attention to hunger and fullness cues, and avoiding mindless snacking while watching screens prevents overeating and metabolic strain.',
          counsellingTip: 'Encourage regular meal intervals and avoiding heavy late-night dinners to promote healthy digestion and sound nocturnal sleep.',
        },
      ],
    },
    {
      id: 'activity',
      code: 'B',
      title: 'Physical Activity',
      tagline: 'Gradual, enjoyable movement to strengthen cardiovascular endurance and circulation',
      icon: '🚶',
      accent: '#2563EB',
      accentBg: '#DBEAFE',
      counsellingPoints: [
        {
          id: 'act_walking',
          title: 'Engage in Regular Daily Walking',
          explanation: 'Brisk walking is one of the safest, most accessible aerobic exercises. It improves myocardial stroke volume, enhances peripheral oxygen extraction, and aids venous blood return from lower limbs.',
          counsellingTip: 'Encourage a daily 20–30 minute walk at a comfortable pace. Breaking it into two 15-minute walks is equally effective for building stamina.',
        },
        {
          id: 'act_appropriate',
          title: 'Choose Appropriate, Low-Impact Activities',
          explanation: 'Selecting activities tailored to physical fitness—such as light cycling, swimming, water aerobics, or gentle mobility stretches—minimizes joint strain while elevating cardiovascular conditioning.',
          counsellingTip: 'Remind patients of the "Talk Test": They should be able to hold a conversation while exercising without gasping for breath.',
        },
        {
          id: 'act_inactivity',
          title: 'Avoid Prolonged Inactivity and Sedentary Blocks',
          explanation: 'Prolonged uninterrupted sitting or lying down impairs vascular endothelial health, promotes peripheral venous pooling, and reduces skeletal muscle insulin sensitivity.',
          counsellingTip: 'Advise standing up, stretching, or walking lightly for 2 to 3 minutes for every 45 to 60 minutes of seated time.',
        },
        {
          id: 'act_gradual',
          title: 'Build Activity Gradually According to Ability',
          explanation: 'Patients should start slowly and progressively increase duration before intensity. Overtaxing an unconditioned heart can lead to severe fatigue or compensatory arrhythmias.',
          counsellingTip: 'Encourage setting modest weekly goals (e.g., adding 3 to 5 minutes of walking each week) rather than attempting vigorous sudden workouts.',
        },
        {
          id: 'act_consult',
          title: 'Consult a Healthcare Professional Before Significant Changes',
          explanation: 'Before initiating any new exercise regimen or significantly escalating workout intensity, cardiac patients must seek medical clearance and personalized safety parameters.',
          counsellingTip: 'Instruct patients to immediately stop activity and seek medical advice if they experience chest discomfort, dizziness, palpitations, or unusual shortness of breath.',
        },
      ],
    },
    {
      id: 'wellbeing',
      code: 'C',
      title: 'Emotional & Mental Wellbeing',
      tagline: 'Fostering emotional equilibrium to modulate autonomic tone and protect the vascular bed',
      icon: '🧠',
      accent: '#7C3AED',
      accentBg: '#EDE9FE',
      counsellingPoints: [
        {
          id: 'wb_stress',
          title: 'Proactive Stress Management',
          explanation: 'Chronic emotional distress sustains high levels of circulating cortisol and catecholamines (adrenaline), which elevate heart rate, increase systemic vascular resistance, and exacerbate myocardial workload.',
          counsellingTip: 'Encourage identifying personal emotional triggers and allocating 15 to 20 minutes daily for calming, restorative activities away from work.',
        },
        {
          id: 'wb_relaxation',
          title: 'Practice Relaxation & Breathing Techniques',
          explanation: 'Diaphragmatic breathing, progressive muscle relaxation, guided imagery, and mindfulness meditation stimulate parasympathetic vagal tone, reducing arterial blood pressure and myocardial oxygen demand.',
          counsellingTip: 'Demonstrate the 4-7-8 breathing exercise: Inhale gently through the nose for 4 counts, hold for 7 counts, and exhale completely through the mouth for 8 counts.',
        },
        {
          id: 'wb_social',
          title: 'Maintain Warm Social Connections',
          explanation: 'Strong interpersonal relationships, family bonding, and positive community engagement are clinically linked to lower cardiovascular morbidity and improved longevity.',
          counsellingTip: 'Encourage regular contact with friends, participation in community groups, or scheduling routine video/phone calls with loved ones.',
        },
        {
          id: 'wb_support',
          title: 'Cultivate and Accept Emotional Support',
          explanation: 'Navigating chronic health management alone can feel overwhelming. Sharing fears, health concerns, and emotional burdens with trusted confidants alleviates psychological distress.',
          counsellingTip: 'Recommend joining structured patient peer support groups or attending heart failure community forums to share lived experiences.',
        },
        {
          id: 'wb_professional',
          title: 'Seek Professional Help for Anxiety or Depression',
          explanation: 'Clinical depression and generalized anxiety disorder are highly prevalent in cardiac patients and significantly worsen adherence to medications and healthy lifestyles.',
          counsellingTip: 'Reassure patients that seeking mental health counseling or psychiatric support is a proactive sign of strength and an integral pillar of comprehensive cardiac care.',
        },
      ],
    },
    {
      id: 'sleep',
      code: 'D',
      title: 'Healthy Sleep',
      tagline: 'Restorative nocturnal rest for systemic hemodynamic recovery and autonomic balance',
      icon: '🌙',
      accent: '#0D9488',
      accentBg: '#CCFBF1',
      counsellingPoints: [
        {
          id: 'slp_schedule',
          title: 'Maintain Consistent Sleep-Wake Schedules',
          explanation: 'Retaining regular bedtimes and wake-up times—including on weekends—stabilizes internal circadian rhythms, promoting nocturnal blood pressure dipping and restorative slow-wave sleep.',
          counsellingTip: 'Aim for 7 to 8 hours of uninterrupted nocturnal sleep every night. Keep wake-up times within 30 minutes of the same time daily.',
        },
        {
          id: 'slp_habits',
          title: 'Practice Healthy Sleep Hygiene Habits',
          explanation: 'Creating a dark, quiet, cool bedroom environment and avoiding bright screens (blue light) 60 minutes before bed enhances natural melatonin secretion.',
          counsellingTip: 'Advise avoiding caffeine, heavy meals, and vigorous physical exertion in the late evening, and reserve the bed exclusively for sleep and rest.',
        },
        {
          id: 'slp_problems',
          title: 'Address Persistent Sleep Difficulties with Healthcare Providers',
          explanation: 'Persistent insomnia, frequent nocturnal awakenings, loud snoring, morning headaches, or daytime drowsiness can signal underlying obstructive sleep apnea (OSA), a potent driver of hypertension and cardiac remodeling.',
          counsellingTip: 'Prompt patients to mention sleep issues during checkups so diagnostic sleep studies (polysomnography) can be arranged when indicated.',
        },
      ],
    },
    {
      id: 'lifestyle',
      code: 'E',
      title: 'Lifestyle Changes',
      tagline: 'Eliminating environmental toxins and aligning daily habits with cardiovascular wellness',
      icon: '🚭',
      accent: '#EA580C',
      accentBg: '#FFEDD5',
      counsellingPoints: [
        {
          id: 'ls_cessation',
          title: 'Complete Smoking Cessation',
          explanation: 'Tobacco smoke contains thousands of toxic chemicals that directly damage the vascular endothelium, promote platelet aggregation, trigger coronary vasoconstriction, and halve oxygen delivery to the heart.',
          counsellingTip: 'Emphasize that cardiovascular benefits begin within 24 hours of quitting. Provide smoking cessation helpline resources and discuss nicotine replacement or pharmacotherapy options.',
        },
        {
          id: 'ls_tobacco',
          title: 'Avoid All Forms of Tobacco and Secondhand Smoke',
          explanation: 'Smokeless tobacco (chewing tobacco, snuff) and exposure to environmental secondhand smoke deliver high nicotine doses that spike blood pressure and accelerate arterial stiffening.',
          counsellingTip: 'Advise patients to maintain a 100% smoke-free home and car, and firmly decline environments with passive smoke exposure.',
        },
        {
          id: 'ls_alcohol',
          title: 'Limit or Completely Avoid Alcohol Consumption',
          explanation: 'Excessive alcohol consumption exerts a direct toxic effect on cardiomyocytes (alcoholic cardiomyopathy), raises blood pressure, triggers atrial fibrillation, and adds empty calories.',
          counsellingTip: 'Recommend abstaining from alcohol or strictly limiting intake to zero or maximum 1 standard unit occasionally, following physician guidance.',
        },
        {
          id: 'ls_overall',
          title: 'Maintain an Overall Healthy Daily Routine',
          explanation: 'Harmonizing nutrition, movement, stress management, and hydration fosters resilience against progressive cardiovascular decline.',
          counsellingTip: 'Help patients establish simple daily routines, such as morning walks, water reminders, and prepared healthy snacks.',
        },
        {
          id: 'ls_medical_advice',
          title: 'Carefully Follow Prescribed Medical Advice',
          explanation: 'Cardiovascular therapies require consistent adherence. Stopping medications prematurely when feeling better is a leading cause of preventable decompensations and hospital readmissions.',
          counsellingTip: 'Encourage patients to maintain an updated medication list, use pill organizers, and never adjust prescription dosages without physician consultation.',
        },
      ],
    },
    {
      id: 'monitoring',
      code: 'F',
      title: 'Prevention & Regular Monitoring',
      tagline: 'Vigilant surveillance of clinical biomarkers and early detection of decompensation',
      icon: '🩺',
      accent: '#0284C7',
      accentBg: '#E0F2FE',
      counsellingPoints: [
        {
          id: 'mon_checkups',
          title: 'Attend Regular Preventive Health Checkups',
          explanation: 'Scheduled outpatient visits enable physicians to evaluate cardiovascular status, assess clinical stability, adjust guideline-directed therapies, and identify subclinical changes before symptoms worsen.',
          counsellingTip: 'Advise keeping a personal calendar of routine follow-up appointments and bringing all current medications to every clinical visit.',
        },
        {
          id: 'mon_bp',
          title: 'Monitor Blood Pressure at Home',
          explanation: 'Home blood pressure monitoring provides a realistic profile of cardiovascular load away from clinic anxiety ("white-coat effect"). Consistent control protects the left ventricle from afterload strain.',
          counsellingTip: 'Instruct patients to measure BP twice daily (morning and evening) while seated quietly for 5 minutes, recording results in a paper log or mobile app.',
        },
        {
          id: 'mon_labs',
          title: 'Monitor Blood Sugar and Lipid Panels as Advised',
          explanation: 'Regular laboratory testing of fasting glucose, HbA1c, lipid profiles (cholesterol, triglycerides), and renal biomarkers (creatinine, electrolytes) guards against silent metabolic and cardiorenal injury.',
          counsellingTip: 'Encourage patients to adhere to recommended testing intervals and discuss test results openly with their healthcare team.',
        },
        {
          id: 'mon_meds',
          title: 'Take Prescribed Medications Exactly as Directed',
          explanation: 'Guideline-directed heart medications work synergistically to reduce mortality, improve ejection fraction, and prevent fluid overload. Consistency is the single most critical factor in their efficacy.',
          counsellingTip: 'Recommend setting smartphone alarms or coordinating pill-taking with daily morning routines (e.g., brushing teeth) to avoid missed doses.',
        },
        {
          id: 'mon_symptoms',
          title: 'Promptly Report Concerning Signs and Symptoms',
          explanation: 'Early detection of congestion signs—such as sudden unexpected weight gain (≥ 2 lbs overnight or ≥ 5 lbs in a week), ankle swelling, worsening breathlessness, or needing extra pillows to sleep—allows outpatient medication adjustments.',
          counsellingTip: 'Provide the clinic emergency contact number and instruct patients: "Never wait until the next routine visit if you notice increasing shortness of breath or sudden swelling."',
        },
      ],
    },
  ]

  const activeData = categories.find((c) => c.id === activeCategory) || categories[0]

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* 1. Header Hero Card */}
      <section style={{
        background: 'linear-gradient(135deg, #0B1F3A 0%, #102F56 60%, #1565D8 100%)',
        borderRadius: '16px',
        padding: '2rem 2.25rem',
        color: '#FFFFFF',
        marginBottom: '2rem',
        boxShadow: '0 8px 24px rgba(11, 31, 58, 0.12)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1.5rem',
      }}>
        <div style={{ maxWidth: '720px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255,255,255,0.12)',
            padding: '5px 14px',
            borderRadius: '20px',
            fontSize: '0.78rem',
            fontWeight: 700,
            marginBottom: '10px',
            color: '#38BDF8',
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
          }}>
            <span>❤️</span>
            <span>Preventive Cardiology &bull; Patient Education Framework</span>
          </div>
          <h1 style={{ margin: '0 0 8px', fontSize: '1.85rem', fontWeight: 800, color: '#FFFFFF' }}>
            Heart Health Counselling & Education Guide
          </h1>
          <p style={{ margin: 0, fontSize: '0.94rem', color: '#DBEAFE', lineHeight: '1.6', opacity: 0.95 }}>
            Evidence-based clinical counselling points structured across six core lifestyle domains. Use these practical, patient-friendly points during clinical consultations to promote sustained cardiovascular wellness and empower self-care.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => onNavigate('prediction')}
            style={{
              background: '#38BDF8',
              color: '#0B1F3A',
              border: 'none',
              padding: '12px 22px',
              borderRadius: '10px',
              fontWeight: 700,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 14px rgba(56, 189, 248, 0.3)',
            }}
          >
            <span>⚡</span>
            <span>Assess New Patient</span>
          </button>
        </div>
      </section>

      {/* 2. Regulatory & Educational Notice Banner */}
      <div style={{
        background: '#EFF6FF',
        border: '1.5px solid #BFDBFE',
        borderRadius: '12px',
        padding: '1rem 1.5rem',
        marginBottom: '2rem',
        color: '#1E40AF',
        fontSize: '0.86rem',
        lineHeight: '1.55',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
      }}>
        <span style={{ fontSize: '1.25rem', lineHeight: 1 }}>ℹ️</span>
        <div>
          <strong>Educational Reference Standard:</strong> This section provides general health education guidelines for physician-patient communication. In strict accordance with medical decision support governance, these points do not constitute automated treatment plans or personalized pharmacological recommendations derived from ANN or Logistic Regression model inferences. Clinical management remains the exclusive responsibility of the treating physician.
        </div>
      </div>

      {/* 3. Category Navigation Tabs (A through F) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '10px',
        marginBottom: '2rem',
      }}>
        {categories.map((cat) => {
          const isActive = cat.id === activeCategory
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => setActiveCategory(cat.id)}
              style={{
                background: isActive ? '#0B1F3A' : '#FFFFFF',
                color: isActive ? '#FFFFFF' : '#334155',
                border: isActive ? '2px solid #0B1F3A' : '1px solid #DBEAFE',
                borderRadius: '12px',
                padding: '14px 16px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                cursor: 'pointer',
                textAlign: 'left',
                boxShadow: isActive ? '0 4px 14px rgba(11, 31, 58, 0.15)' : '0 2px 6px rgba(11, 31, 58, 0.03)',
                transition: 'all 0.15s ease',
              }}
            >
              <span style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: isActive ? 'rgba(255,255,255,0.15)' : cat.accentBg,
                color: isActive ? '#FFFFFF' : cat.accent,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.15rem',
                flexShrink: 0,
              }}>
                {cat.icon}
              </span>
              <div>
                <div style={{ fontSize: '0.72rem', fontWeight: 800, color: isActive ? '#38BDF8' : '#64748B', textTransform: 'uppercase' }}>
                  Category {cat.code}
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: isActive ? '#FFFFFF' : '#0B1F3A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {cat.title}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* 4. Active Domain Counselling Content Card */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: '16px',
        border: '1px solid #DBEAFE',
        padding: '2rem 2.25rem',
        boxShadow: '0 4px 16px rgba(11, 31, 58, 0.04)',
      }}>
        {/* Category Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          borderBottom: '1px solid #F1F5F9',
          paddingBottom: '1.5rem',
          marginBottom: '2rem',
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '14px',
            background: activeData.accentBg,
            color: activeData.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.8rem',
            boxShadow: `0 4px 12px ${activeData.accentBg}`,
          }}>
            {activeData.icon}
          </div>
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 800, color: activeData.accent, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Category {activeData.code} &bull; Practice Domain
            </div>
            <h2 style={{ margin: '2px 0 4px', fontSize: '1.5rem', fontWeight: 800, color: '#0B1F3A' }}>
              {activeData.title}
            </h2>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#64748B' }}>
              {activeData.tagline}
            </p>
          </div>
        </div>

        {/* Counselling Points Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: '1.5rem',
        }}>
          {activeData.counsellingPoints.map((point) => {
            const isChecked = !!checkedPoints[point.id]
            return (
              <div
                key={point.id}
                onClick={() => toggleCheck(point.id)}
                style={{
                  border: isChecked ? '1.5px solid #93C5FD' : '1px solid #E2E8F0',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  background: isChecked ? '#F8FAFC' : '#FFFFFF',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: '0 2px 8px rgba(11, 31, 58, 0.03)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '10px' }}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      style={{
                        width: '20px',
                        height: '20px',
                        accentColor: activeData.accent,
                        cursor: 'pointer',
                        marginTop: '2px',
                        flexShrink: 0,
                      }}
                    />
                    <h3 style={{
                      margin: 0,
                      fontSize: '1.05rem',
                      fontWeight: 700,
                      color: isChecked ? '#64748B' : '#0B1F3A',
                      textDecoration: isChecked ? 'line-through' : 'none',
                    }}>
                      {point.title}
                    </h3>
                  </div>

                  <p style={{
                    margin: '0 0 1rem',
                    fontSize: '0.86rem',
                    color: '#475569',
                    lineHeight: '1.6',
                  }}>
                    {point.explanation}
                  </p>
                </div>

                {/* Practical Counselling Tip Box */}
                <div style={{
                  background: '#F8FAFC',
                  borderLeft: `4px solid ${activeData.accent}`,
                  borderRadius: '0 8px 8px 0',
                  padding: '10px 14px',
                  fontSize: '0.82rem',
                  color: '#334155',
                  lineHeight: '1.5',
                }}>
                  <strong style={{ color: activeData.accent, display: 'block', marginBottom: '2px', fontSize: '0.76rem', textTransform: 'uppercase' }}>
                    💡 Clinical Conversation Tip:
                  </strong>
                  {point.counsellingTip}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
