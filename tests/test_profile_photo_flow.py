"""
test_profile_photo_flow.py
==========================
End-to-end test suite for Physician Profile Photo uploading, serving, and persistence.
"""
import io
import time
from fastapi.testclient import TestClient
from main import app
from backend.database.config import SessionLocal
from backend.database.models import Doctor

def test_profile_photo_lifecycle():
    client = TestClient(app)
    
    # 1. Prepare valid PNG image bytes (1x1 red pixel PNG)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
        b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    # 2. Upload photo with authorized bearer token
    headers = {"Authorization": "Bearer demo-access-token-carter-2026"}
    files = {"file": ("physician_photo.png", png_bytes, "image/png")}
    
    upload_res = client.post("/auth/profile-photo", headers=headers, files=files)
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.status_code} {upload_res.text}"
    
    data = upload_res.json()
    assert data["status"] == "success"
    assert "profile_photo_url" in data
    photo_url = data["profile_photo_url"]
    print(f"✓ Upload succeeded: {photo_url}")

    # 3. Verify in database
    db = SessionLocal()
    try:
        doctor = db.query(Doctor).filter(Doctor.email == "dr.carter@hospital.org").first()
        assert doctor is not None, "Doctor dr.carter@hospital.org not found in DB"
        assert doctor.profile_photo_path is not None, "profile_photo_path is None in DB"
        print(f"✓ DB Persistence verified: {doctor.doctor_id} -> {doctor.profile_photo_path}")
        doc_id = doctor.doctor_id
    finally:
        db.close()

    # 4. Fetch photo via GET /auth/profile-photo/{doctor_id}
    clean_url = photo_url.split("?")[0]
    get_res = client.get(clean_url)
    assert get_res.status_code == 200, f"Fetch by URL failed: {get_res.status_code}"
    assert get_res.headers["content-type"] in ("image/png", "image/jpeg", "image/webp")
    assert len(get_res.content) == len(png_bytes)
    print(f"✓ Photo serving verified: {len(get_res.content)} bytes returned with 200 OK")

    # 5. Fetch photo via demo ID
    demo_res = client.get("/auth/profile-photo/demo-carter-local-2026")
    assert demo_res.status_code == 200, f"Fetch by demo ID failed: {demo_res.status_code}"
    assert len(demo_res.content) == len(png_bytes)
    print("✓ Demo ID fallback serving verified with 200 OK")

    # 6. Verify /auth/me returns profile_photo_url
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200, f"/auth/me failed: {me_res.status_code}"
    me_data = me_res.json()
    assert me_data.get("profile_photo_url") is not None
    print(f"✓ /auth/me returned profile_photo_url: {me_data['profile_photo_url']}")

    print("\n>>> ALL PROFILE PHOTO TESTS PASSED! <<<\n")

if __name__ == "__main__":
    test_profile_photo_lifecycle()
