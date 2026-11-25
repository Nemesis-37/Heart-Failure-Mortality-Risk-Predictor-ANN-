# Database Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    Doctors ||--o{ Assessments : "performs"
    Doctors ||--o{ Predictions : "records"
    Doctors ||--o{ EmailOTPs : "receives"
    Doctors ||--o{ DoctorSessions : "maintains"
    Assessments ||--o{ Predictions : "evaluates"

    Doctors {
        string doctor_id PK
        string full_name
        string email UK
        string password_hash
        string mobile
        string medical_degree
        string registration_number UK
        string registration_council
        string username UK
        boolean email_verified
        string verification_status "PENDING, APPROVED, REJECTED"
        boolean is_active
        datetime created_at
        datetime updated_at
        string profile_photo_path
    }

    Administrators {
        string admin_id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        string role "Super Administrator"
        boolean is_active
        datetime created_at
    }

    Assessments {
        string assessment_id PK
        string doctor_id FK
        string patient_reference
        string patient_reference_id
        string assessment_code
        float age
        int anaemia
        float creatinine_phosphokinase
        int diabetes
        float ejection_fraction
        int high_blood_pressure
        float platelets
        float serum_creatinine
        float serum_sodium
        int sex
        int smoking
        string selected_model
        int predicted_class
        float predicted_probability
        float classification_threshold
        datetime created_at
    }

    Predictions {
        string prediction_id PK
        string assessment_id FK
        string doctor_id FK
        string model_name
        string model_version
        float probability
        int predicted_class
        float threshold_used
        json input_features
        datetime created_at
    }

    EmailOTPs {
        string otp_id PK
        string doctor_id FK
        string otp_hash
        datetime expires_at
        int attempts
        boolean is_used
        datetime created_at
    }

    DoctorSessions {
        string session_id PK
        string doctor_id FK
        string refresh_token_hash
        datetime expires_at
        boolean is_revoked
        datetime created_at
        datetime last_used_at
    }
```
