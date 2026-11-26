"""
scripts/test_phase14_prediction_redesign.py
=========================================
Comprehensive end-to-end verification for Phase 14 — Final Prediction Experience Redesign:
1. Backend Logistic Regression pipeline fidelity & exclusion of 'time' and ANN in /predict & /api/predict
2. Mathematical proof: contribution_i = standardized_i * coef_i and intercept + sum(contributions) == logit
3. Dynamic patient-specific contribution differences across multiple clinical profiles
4. Auth & validation guards (401 on invalid token, 422 on missing/invalid parameters)
5. Frontend Page 1 & Page 2 SSR + bundle verification against REAL FastAPI /api/predict responses
6. Medical safety audit across all 11 feature explanations
"""

import json
import math
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from main import app, lr_model, lr_feature_names

client = TestClient(app)


PROFILES = {
    "low_risk": {
        "patient_reference_id": "PT-2026-LOW-01",
        "age": 48.0,
        "anaemia": 0,
        "creatinine_phosphokinase": 150.0,
        "diabetes": 0,
        "ejection_fraction": 55.0,
        "high_blood_pressure": 0,
        "platelets": 270000.0,
        "serum_creatinine": 0.9,
        "serum_sodium": 140.0,
        "sex": 0,
        "smoking": 0,
    },
    "high_risk": {
        "patient_reference_id": "PT-2026-HIGH-02",
        "age": 78.0,
        "anaemia": 1,
        "creatinine_phosphokinase": 780.0,
        "diabetes": 1,
        "ejection_fraction": 20.0,
        "high_blood_pressure": 1,
        "platelets": 190000.0,
        "serum_creatinine": 2.7,
        "serum_sodium": 129.0,
        "sex": 1,
        "smoking": 1,
    },
    "moderate_profile": {
        "patient_reference_id": "PT-2026-MOD-03",
        "age": 65.0,
        "anaemia": 0,
        "creatinine_phosphokinase": 310.0,
        "diabetes": 1,
        "ejection_fraction": 35.0,
        "high_blood_pressure": 1,
        "platelets": 245000.0,
        "serum_creatinine": 1.3,
        "serum_sodium": 136.0,
        "sex": 1,
        "smoking": 0,
    },
}


def run_tests():
    print("=" * 80)
    print("PHASE 14 — FINAL PREDICTION EXPERIENCE REDESIGN VERIFICATION")
    print("=" * 80)

    passed = 0
    failed = 0

    def check(test_id: str, title: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        status = "PASS" if condition else "FAIL"
        if condition:
            passed += 1
        else:
            failed += 1
        suffix = f" - {detail}" if detail else ""
        print(f"[{status}] {test_id}: {title}{suffix}")

    # 1. Authenticate demo physician & verify auth + db health
    login_resp = client.post(
        "/auth/login",
        json={"email": "dr.carter@hospital.org", "password": "demo-doctor-2026"},
    )
    check("P14-AUTH-01", "Physician login succeeds", login_resp.status_code == 200)
    token = login_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    bad_auth = client.post("/api/predict", json=PROFILES["low_risk"], headers={"Authorization": "Bearer invalid-jwt"})
    check("P14-AUTH-02", "Tampered Bearer token blocked on /api/predict", bad_auth.status_code == 401)

    # 2. Verify LR feature schema excludes 'time'
    check(
        "P14-LR-01",
        "LR pipeline uses exactly 11 features without 'time'",
        len(lr_feature_names) == 11 and "time" not in lr_feature_names,
        f"Features={lr_feature_names}",
    )

    # 3. Validate input handling (missing ref & out-of-range age)
    missing_ref = dict(PROFILES["low_risk"])
    del missing_ref["patient_reference_id"]
    check("P14-VAL-01", "Missing patient_reference_id rejected with 422", client.post("/api/predict", json=missing_ref, headers=headers).status_code == 422)

    bad_age = dict(PROFILES["low_risk"], age=-5)
    check("P14-VAL-02", "Invalid age rejected with 422", client.post("/api/predict", json=bad_age, headers=headers).status_code == 422)

    # 4. Run real predictions on /predict and /api/predict & verify exact math
    scaler = lr_model.named_steps["scaler"]
    clf = lr_model.named_steps["classifier"]
    coef_map = {name: float(clf.coef_[0][i]) for i, name in enumerate(lr_feature_names)}
    real_api_responses = {}

    for key, payload in PROFILES.items():
        resp_root = client.post("/predict", json=payload, headers=headers)
        resp_api = client.post("/api/predict", json=payload, headers=headers)
        check(f"P14-API-{key.upper()}-1", f"/predict returns 200 for {key}", resp_root.status_code == 200)
        check(f"P14-API-{key.upper()}-2", f"/api/predict returns 200 for {key}", resp_api.status_code == 200)

        data = resp_api.json()
        real_api_responses[key] = {"payload": payload, "response": data}

        check(f"P14-LR-{key.upper()}-MODEL", "Prediction strictly uses Logistic Regression", data.get("model") == "Logistic Regression" and "Neural" not in json.dumps(data))
        check(f"P14-LR-{key.upper()}-THRESH", "Classification threshold remains 0.50", data.get("threshold") == 0.5)

        df = pd.DataFrame([payload])[lr_feature_names]
        direct_prob = float(lr_model.predict_proba(df)[0][1])
        direct_logit = float(lr_model.decision_function(df)[0])
        direct_scaled = scaler.transform(df)[0]

        check(
            f"P14-PROB-{key.upper()}",
            f"API probability matches sklearn pipeline ({direct_prob:.4f})",
            abs(data["predicted_probability"] - round(direct_prob, 4)) < 1e-4,
            f"api={data['predicted_probability']} vs pipeline={round(direct_prob, 4)}",
        )

        contribs = data.get("feature_contributions", [])
        check(f"P14-CONTRIB-LEN-{key.upper()}", "Returned all 11 feature contributions without 'time'", len(contribs) == 11 and all(c["feature"] != "time" for c in contribs))

        # Verify sorted descending by abs_contribution
        abs_list = [c["abs_contribution"] for c in contribs]
        check(f"P14-SORT-{key.upper()}", "Feature contributions ranked descending by |contribution|", abs_list == sorted(abs_list, reverse=True))

        # Verify each item's standardized_i * coef_i & patient_value
        max_item_diff = 0.0
        for item in contribs:
            idx = lr_feature_names.index(item["feature"])
            expected_z = float(direct_scaled[idx])
            expected_c = coef_map[item["feature"]]
            expected_contrib = expected_z * expected_c
            max_item_diff = max(max_item_diff, abs(item["contribution"] - expected_contrib))
            assert abs(float(item["patient_value"]) - float(payload[item["feature"]])) < 1e-4

        sum_c = sum(c["contribution"] for c in contribs)
        reconstructed = data["baseline_intercept"] + sum_c
        sigmoid_prob = 1.0 / (1.0 + math.exp(-direct_logit))
        check(
            f"P14-MATH-{key.upper()}",
            "Intercept + sum(z_i * coef_i) reconstructs model logit",
            abs(reconstructed - direct_logit) < 1e-4 and data["logit_reconstruction_error"] < 1e-10 and max_item_diff < 1e-5 and abs(sigmoid_prob - direct_prob) < 1e-6,
            f"reconstructed={reconstructed:.6f}, decision_function={direct_logit:.6f}, raw_err={data['logit_reconstruction_error']:.2e}",
        )

    # Confirm patient-specific contributions actually differ between low & high risk
    low_map = {c["feature"]: c["contribution"] for c in real_api_responses["low_risk"]["response"]["feature_contributions"]}
    high_map = {c["feature"]: c["contribution"] for c in real_api_responses["high_risk"]["response"]["feature_contributions"]}
    changed_count = sum(1 for k in lr_feature_names if abs(low_map[k] - high_map[k]) > 1e-3)
    check("P14-DYNAMIC-01", "Feature contributions dynamically change across patient inputs", changed_count == 11, f"features_changed={changed_count}/11")

    # 5. Run Node verification for frontend SSR (Page 1, Page 2 with REAL backend payloads, safety audit)
    tmp_payload_file = PROJECT_ROOT / "frontend" / ".tmp_phase14_payloads.json"
    tmp_payload_file.write_text(json.dumps(real_api_responses), encoding="utf-8")

    node_script = """
import fs from 'node:fs';
import { createServer } from 'vite';
import React from 'react';
import { renderToString } from 'react-dom/server';

const mkStore = () => {
  const s = new Map();
  return {
    getItem: (k) => s.has(k) ? s.get(k) : null,
    setItem: (k, v) => s.set(k, String(v)),
    removeItem: (k) => s.delete(k),
    clear: () => s.clear(),
  };
};
globalThis.localStorage = mkStore();
globalThis.sessionStorage = mkStore();
globalThis.window = globalThis;
globalThis.window.addEventListener = () => {};
globalThis.window.removeEventListener = () => {};
globalThis.window.dispatchEvent = () => true;
globalThis.window.matchMedia = () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} });
globalThis.document = {
  documentElement: { classList: { add: () => {}, remove: () => {}, toggle: () => {} }, setAttribute: () => {} },
  querySelector: () => null,
};

const payloads = JSON.parse(fs.readFileSync('.tmp_phase14_payloads.json', 'utf8'));
const server = await createServer({ server: { middlewareMode: true }, appType: 'custom', logLevel: 'silent' });

try {
  const { ThemeProvider } = await server.ssrLoadModule('/src/context/ThemeContext.jsx');
  const App = (await server.ssrLoadModule('/src/App.jsx')).default;
  const AppLayout = (await server.ssrLoadModule('/src/layouts/AppLayout.jsx')).default;
  const DoctorDashboard = (await server.ssrLoadModule('/src/DoctorDashboard.jsx')).default;
  const PredictionResultsPage = (await server.ssrLoadModule('/src/pages/PredictionResultsPage.jsx')).default;
  const { buildFeatureExplanation } = await server.ssrLoadModule('/src/utils/featureExplanations.js');

  const wrap = (el) => renderToString(React.createElement(ThemeProvider, null, el));
  const noop = () => {};
  const user = { id: 1, name: 'Dr. Julian Carter, MD', email: 'dr.carter@hospital.org', role: 'Attending Physician' };

  // Page 1 checks
  const outPage1 = wrap(React.createElement(DoctorDashboard, {
    doctorUser: user,
    embedded: true,
    onLogout: noop,
    onPredictionSuccess: noop,
  }));

  if (!outPage1.includes('Patient Risk Assessment')) throw new Error('Missing Patient Risk Assessment heading');
  if (!outPage1.includes('Generate Prediction')) throw new Error('Missing Generate Prediction button');
  for (const label of ['Age', 'Biological Sex', 'Ejection Fraction', 'Serum Creatinine', 'Serum Sodium', 'Platelets', 'Creatinine Phosphokinase', 'Anaemia', 'Diabetes', 'High Blood Pressure', 'Smoking']) {
    if (!outPage1.includes(label)) throw new Error('Missing input feature label: ' + label);
  }
  for (const forbidden of ['dashboard-right-column', 'model-selection-card', 'Artificial Neural Network', 'Dual Model', '/predict-ann']) {
    if (outPage1.includes(forbidden)) throw new Error('Page 1 still contains removed side panel or ANN element: ' + forbidden);
  }

  // AppLayout checks (no Dual Model badge)
  const outLayout = wrap(React.createElement(AppLayout, {
    doctorUser: user,
    onLogout: noop,
    activePage: 'prediction',
    onNavigate: noop,
  }, React.createElement('div', null, 'child')));
  if (outLayout.includes('Dual Model') || outLayout.includes('dual-model')) {
    throw new Error('AppLayout still exposes Dual Model wording');
  }

  // Page 2 checks with REAL backend responses (low risk and high risk)
  for (const [k, obj] of Object.entries(payloads)) {
    const outPage2 = wrap(React.createElement(PredictionResultsPage, {
      resultState: {
        predictionResponse: obj.response,
        patientInputs: obj.payload,
        patientRef: obj.payload.patient_reference_id,
        assessmentCode: 'ASM-TEST-001',
        predictionCode: 'PRD-TEST-001',
        displayTimestamp: '2026-11-26 15:30:00',
      },
      onBackToForm: noop,
      onNewAssessment: noop,
    }));

    const expectedPct = (obj.response.predicted_probability * 100).toFixed(1) + '%';
    if (!outPage2.includes(expectedPct)) throw new Error('Page 2 missing exact probability ' + expectedPct + ' for ' + k);
    if (!outPage2.includes(obj.payload.patient_reference_id)) throw new Error('Page 2 missing patient ID for ' + k);
    if (!outPage2.includes('Factors Influencing This Prediction')) throw new Error('Page 2 missing Factors Influencing This Prediction heading');
    if (!outPage2.includes('Why it matters in this prediction')) throw new Error('Page 2 missing Why it matters block');
    if (!outPage2.includes('Clinical Review / Next Step')) throw new Error('Page 2 missing Clinical Review / Next Step block');
    if (!outPage2.includes('Back to Patient Form') || !outPage2.includes('New Assessment')) throw new Error('Page 2 missing Back / New Assessment navigation');
    if (!outPage2.includes('educational machine-learning prototype')) throw new Error('Page 2 missing required educational disclaimer');
    if (!outPage2.includes('This assessment uses a Logistic Regression model')) throw new Error('Page 2 missing model explanation note');
    if (outPage2.includes('Artificial Neural Network') || outPage2.includes('model-selection')) {
      throw new Error('Page 2 exposed ANN or model selection controls');
    }

    // Medical safety check across all 11 feature cards
    const bannedPhrases = [
      'stop taking', 'start taking', 'change dose', 'increase dose', 'reduce dose',
      'raise your platelets', 'lower your creatinine', 'raise sodium', 'increase ejection fraction',
      'treatment priority', 'manipulate'
    ];
    for (const item of obj.response.feature_contributions) {
      const exp = buildFeatureExplanation(item);
      const combined = (exp.whyItMatters + ' ' + exp.clinicalNextStep).toLowerCase();
      for (const bad of bannedPhrases) {
        if (combined.includes(bad)) throw new Error('Banned prescriptive phrase found: ' + bad);
      }
      if ((item.feature === 'age' || item.feature === 'sex') && !exp.clinicalNextStep.toLowerCase().includes('non-modifiable')) {
        throw new Error('Non-modifiable note missing for ' + item.feature);
      }
    }
  }

  console.log('PHASE14_FRONTEND_SSR_OK');
} finally {
  await server.close();
}
"""
    try:
        node_proc = subprocess.run(
            ["node", "--input-type=module", "-e", node_script],
            cwd=str(PROJECT_ROOT / "frontend"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        ok_ssr = node_proc.returncode == 0 and "PHASE14_FRONTEND_SSR_OK" in node_proc.stdout
        check(
            "P14-FE-SSR",
            "Frontend Page 1, Page 2, Navigation & Safety checks pass with real backend payloads",
            ok_ssr,
            node_proc.stdout.strip() if ok_ssr else (node_proc.stderr or node_proc.stdout),
        )
    finally:
        if tmp_payload_file.exists():
            tmp_payload_file.unlink()

    print("\n" + "=" * 80)
    print(f"PHASE 14 TEST SUMMARY: {passed} / {passed + failed} PASSED (Failed: {failed})")
    print("=" * 80)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
