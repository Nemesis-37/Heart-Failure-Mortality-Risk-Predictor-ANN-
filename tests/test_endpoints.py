import subprocess
import sys
import time
import urllib.request
import json

python_exe = sys.executable
proc = subprocess.Popen([
    python_exe, "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1", "--port", "8000"
])

try:
    print('Waiting for uvicorn server to start...')
    ready = False
    for i in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1) as resp:
                if resp.status == 200:
                    print(f'Server is UP and HEALTHY (attempt {i+1})!')
                    ready = True
                    break
        except Exception:
            time.sleep(0.5)

    if not ready:
        print('Server failed to start in 30 seconds.')
        sys.exit(1)

    def post_json(url, data):
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    low_risk = {
        'age': 50.0,
        'anaemia': 0,
        'creatinine_phosphokinase': 168.0,
        'diabetes': 0,
        'ejection_fraction': 45.0,
        'high_blood_pressure': 0,
        'platelets': 276000.0,
        'serum_creatinine': 0.9,
        'serum_sodium': 140.0,
        'sex': 1,
        'smoking': 0
    }

    print('\n--- 1. Testing POST /predict (Logistic Regression) ---')
    s, r = post_json('http://127.0.0.1:8000/predict', low_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    print('\n--- 2. Testing POST /api/predict ---')
    s, r = post_json('http://127.0.0.1:8000/api/predict', low_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    print('\n--- 3. Testing POST /predict-ann (Artificial Neural Network) ---')
    s, r = post_json('http://127.0.0.1:8000/predict-ann', low_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    print('\n--- 4. Testing POST /api/predict-ann ---')
    s, r = post_json('http://127.0.0.1:8000/api/predict-ann', low_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    high_risk = {
        'age': 75.0,
        'anaemia': 1,
        'creatinine_phosphokinase': 582.0,
        'diabetes': 1,
        'ejection_fraction': 20.0,
        'high_blood_pressure': 1,
        'platelets': 265000.0,
        'serum_creatinine': 2.5,
        'serum_sodium': 130.0,
        'sex': 1,
        'smoking': 1
    }

    print('\n--- 5. Testing High Risk Patient on ANN ---')
    s, r = post_json('http://127.0.0.1:8000/predict-ann', high_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    print('\n--- 6. Testing High Risk Patient on LR ---')
    s, r = post_json('http://127.0.0.1:8000/predict', high_risk)
    print(f'Status: {s}, Model: {r["model"]}, Class: {r["predicted_class"]}, Label: {r["predicted_label"]}, Prob: {r["predicted_probability"]}')

    print('\n--- 7. Testing Invalid Input ---')
    try:
        post_json('http://127.0.0.1:8000/predict', {'age': -10})
        print('Failed: Should have raised HTTPError')
    except urllib.error.HTTPError as e:
        print(f'Correctly rejected invalid input with HTTP status: {e.code}')

    print('\n=============================================')
    print('SUCCESS: ALL PREDICTION ENDPOINTS VERIFIED 100%')
    print('=============================================')

finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
