-- ==============================================================================
-- Heart Failure Mortality Risk Predictor — PostgreSQL Database Schema
-- Schema: clinical
-- Database Target: PostgreSQL 14+ (Local PostgreSQL 18 & Render Production)
-- Version: 3.0.0 (Unified with SQLAlchemy ORM and Alembic)
-- ==============================================================================

-- 1. Create Schema
CREATE SCHEMA IF NOT EXISTS clinical;

-- 2. Create Doctors Table
CREATE TABLE IF NOT EXISTS clinical."Doctors" (
    doctor_id             VARCHAR(64)                  PRIMARY KEY,
    full_name             VARCHAR(128)                 NOT NULL,
    email                 VARCHAR(256)                 NOT NULL,
    password_hash         VARCHAR(256)                 NOT NULL,
    mobile                VARCHAR(32)                  NOT NULL,
    medical_degree        VARCHAR(128)                 NOT NULL,
    registration_number   VARCHAR(64)                  NOT NULL,
    registration_council  VARCHAR(128)                 NOT NULL,
    email_verified        BOOLEAN                      NOT NULL DEFAULT FALSE,
    verification_status   VARCHAR(32)                  NOT NULL DEFAULT 'PENDING',
    is_active             BOOLEAN                      NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMP WITH TIME ZONE     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username              VARCHAR(64)                  NULL,
    last_login            TIMESTAMP WITH TIME ZONE     NULL,
    approved_at           TIMESTAMP WITH TIME ZONE     NULL,
    document_filename     VARCHAR(256)                 NULL,
    document_path         VARCHAR(512)                 NULL,
    document_uploaded_at  TIMESTAMP WITH TIME ZONE     NULL,
    verified_at           TIMESTAMP WITH TIME ZONE     NULL,
    verified_by           VARCHAR(64)                  NULL,
    rejection_reason      VARCHAR(512)                 NULL,
    CONSTRAINT "UQ_Doctors_Email" UNIQUE (email),
    CONSTRAINT "UQ_Doctors_RegNumber" UNIQUE (registration_number),
    CONSTRAINT "CK_Doctors_VerificationStatus" CHECK (verification_status IN ('PENDING', 'APPROVED', 'REJECTED'))
);

CREATE INDEX IF NOT EXISTS "IX_Doctors_Email" ON clinical."Doctors" (email);
CREATE INDEX IF NOT EXISTS "IX_Doctors_RegistrationNumber" ON clinical."Doctors" (registration_number);
CREATE INDEX IF NOT EXISTS "IX_Doctors_VerificationStatus" ON clinical."Doctors" (verification_status);
CREATE UNIQUE INDEX IF NOT EXISTS "UQ_Doctors_Username" ON clinical."Doctors" (username) WHERE username IS NOT NULL;

-- 3. Create DoctorSessions Table
CREATE TABLE IF NOT EXISTS clinical."DoctorSessions" (
    session_id            VARCHAR(64)                  PRIMARY KEY,
    doctor_id             VARCHAR(64)                  NOT NULL,
    refresh_token_hash    VARCHAR(256)                 NOT NULL,
    expires_at            TIMESTAMP WITH TIME ZONE     NOT NULL,
    is_revoked            BOOLEAN                      NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMP WITH TIME ZONE     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_agent            VARCHAR(256)                 NULL,
    ip_address            VARCHAR(64)                  NULL,
    CONSTRAINT "FK_DoctorSessions_Doctors" FOREIGN KEY (doctor_id) 
        REFERENCES clinical."Doctors" (doctor_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "IX_DoctorSessions_DoctorId" ON clinical."DoctorSessions" (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS "IX_DoctorSessions_ExpiresAt" ON clinical."DoctorSessions" (expires_at);

-- 4. Create EmailOTP Table
CREATE TABLE IF NOT EXISTS clinical."EmailOTP" (
    otp_id                VARCHAR(64)                  PRIMARY KEY,
    doctor_id             VARCHAR(64)                  NOT NULL,
    otp_hash              VARCHAR(256)                 NOT NULL,
    expires_at            TIMESTAMP WITH TIME ZONE     NOT NULL,
    attempts              INTEGER                      NOT NULL DEFAULT 0,
    is_used               BOOLEAN                      NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMP WITH TIME ZONE     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "FK_EmailOTP_Doctors" FOREIGN KEY (doctor_id) 
        REFERENCES clinical."Doctors" (doctor_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "IX_EmailOTP_DoctorId" ON clinical."EmailOTP" (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS "IX_EmailOTP_ExpiresAt" ON clinical."EmailOTP" (expires_at);

-- 5. Create Administrators Table
CREATE TABLE IF NOT EXISTS clinical."Administrators" (
    admin_id              VARCHAR(64)                  PRIMARY KEY,
    username              VARCHAR(64)                  NOT NULL,
    email                 VARCHAR(256)                 NOT NULL,
    password_hash         VARCHAR(256)                 NOT NULL,
    full_name             VARCHAR(128)                 NOT NULL,
    role                  VARCHAR(64)                  NOT NULL DEFAULT 'Medical Credentialing Officer',
    is_active             BOOLEAN                      NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMP WITH TIME ZONE     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "UQ_Admin_Username" UNIQUE (username),
    CONSTRAINT "UQ_Admin_Email" UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS "IX_Admin_Email" ON clinical."Administrators" (email);

-- 6. Create Patient Assessments Table
CREATE TABLE IF NOT EXISTS clinical."Assessments" (
    id                        VARCHAR(64)              PRIMARY KEY,
    assessment_code           VARCHAR(32)              NOT NULL,
    patient_reference_id      VARCHAR(64)              NULL,
    doctor_id                 VARCHAR(64)              NULL,
    age                       NUMERIC(5, 1)            NOT NULL,
    anaemia                   SMALLINT                 NOT NULL,
    creatinine_phosphokinase  NUMERIC(8, 2)            NOT NULL,
    diabetes                  SMALLINT                 NOT NULL,
    ejection_fraction         NUMERIC(5, 2)            NOT NULL,
    high_blood_pressure       SMALLINT                 NOT NULL,
    platelets                 NUMERIC(10, 2)           NOT NULL,
    serum_creatinine          NUMERIC(5, 2)            NOT NULL,
    serum_sodium              NUMERIC(5, 2)            NOT NULL,
    sex                       SMALLINT                 NOT NULL,
    smoking                   SMALLINT                 NOT NULL,
    selected_model            VARCHAR(64)              NULL,
    predicted_class           SMALLINT                 NULL,
    predicted_probability     NUMERIC(6, 4)            NULL,
    prediction_timestamp      TIMESTAMP WITH TIME ZONE NULL,
    is_prediction_stale       BOOLEAN                  NOT NULL DEFAULT FALSE,
    version                   INTEGER                  NOT NULL DEFAULT 1,
    created_at                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "UQ_Assessments_Code" UNIQUE (assessment_code),
    CONSTRAINT "CK_Assessments_Age" CHECK (age >= 1.0 AND age <= 120.0),
    CONSTRAINT "CK_Assessments_Anaemia" CHECK (anaemia IN (0, 1)),
    CONSTRAINT "CK_Assessments_CPK" CHECK (creatinine_phosphokinase > 0.0 AND creatinine_phosphokinase <= 20000.0),
    CONSTRAINT "CK_Assessments_Diabetes" CHECK (diabetes IN (0, 1)),
    CONSTRAINT "CK_Assessments_EF" CHECK (ejection_fraction >= 1.0 AND ejection_fraction <= 100.0),
    CONSTRAINT "CK_Assessments_HBP" CHECK (high_blood_pressure IN (0, 1)),
    CONSTRAINT "CK_Assessments_Platelets" CHECK (platelets > 0.0 AND platelets <= 2000000.0),
    CONSTRAINT "CK_Assessments_Creatinine" CHECK (serum_creatinine >= 0.1 AND serum_creatinine <= 30.0),
    CONSTRAINT "CK_Assessments_Sodium" CHECK (serum_sodium >= 50.0 AND serum_sodium <= 200.0),
    CONSTRAINT "CK_Assessments_Sex" CHECK (sex IN (0, 1)),
    CONSTRAINT "CK_Assessments_Smoking" CHECK (smoking IN (0, 1)),
    CONSTRAINT "CK_Assessments_PredictedClass" CHECK (predicted_class IS NULL OR predicted_class IN (0, 1)),
    CONSTRAINT "CK_Assessments_PredictedProb" CHECK (predicted_probability IS NULL OR (predicted_probability >= 0.0 AND predicted_probability <= 1.0)),
    CONSTRAINT "FK_Assessments_Doctors" FOREIGN KEY (doctor_id) 
        REFERENCES clinical."Doctors" (doctor_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "IX_Assessments_PatientRef" ON clinical."Assessments" (patient_reference_id);
CREATE INDEX IF NOT EXISTS "IX_Assessments_DoctorId" ON clinical."Assessments" (doctor_id, created_at);
CREATE INDEX IF NOT EXISTS "IX_Assessments_CreatedAt" ON clinical."Assessments" (created_at);

-- 7. Create Predictions Table
CREATE TABLE IF NOT EXISTS clinical."Predictions" (
    id                        VARCHAR(64)              PRIMARY KEY,
    prediction_code           VARCHAR(32)              NOT NULL,
    assessment_id             VARCHAR(64)              NOT NULL,
    model_name                VARCHAR(64)              NOT NULL,
    predicted_class           SMALLINT                 NOT NULL,
    predicted_probability     NUMERIC(6, 4)            NOT NULL,
    classification_threshold  NUMERIC(4, 2)            NOT NULL DEFAULT 0.50,
    model_version             VARCHAR(32)              NOT NULL DEFAULT 'v1.0.0',
    created_at                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "UQ_Predictions_Code" UNIQUE (prediction_code),
    CONSTRAINT "CK_Predictions_Class" CHECK (predicted_class IN (0, 1)),
    CONSTRAINT "CK_Predictions_Prob" CHECK (predicted_probability >= 0.0 AND predicted_probability <= 1.0),
    CONSTRAINT "FK_Predictions_Assessments" FOREIGN KEY (assessment_id) 
        REFERENCES clinical."Assessments" (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS "IX_Predictions_AssessmentId" ON clinical."Predictions" (assessment_id, created_at);
CREATE INDEX IF NOT EXISTS "IX_Predictions_CreatedAt" ON clinical."Predictions" (created_at);
