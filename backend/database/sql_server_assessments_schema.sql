-- ==============================================================================
-- Heart Failure Mortality Risk Predictor — Microsoft SQL Server Database Schema
-- Schema: [clinical]
-- Version: 2.0.0 (Unified with SQLAlchemy ORM and SQLite)
-- ==============================================================================

-- 1. Create Schema if needed
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'clinical')
BEGIN
    EXEC('CREATE SCHEMA [clinical]')
END
GO

-- 2. Create Doctors Reference Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Doctors]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Doctors] (
        [doctor_id]             VARCHAR(64)    NOT NULL,
        [full_name]             VARCHAR(128)   NOT NULL,
        [email]                 VARCHAR(256)   NOT NULL,
        [password_hash]         VARCHAR(256)   NOT NULL,
        [mobile]                VARCHAR(32)    NOT NULL,
        [medical_degree]        VARCHAR(128)   NOT NULL,
        [registration_number]   VARCHAR(64)    NOT NULL,
        [registration_council]  VARCHAR(128)   NOT NULL,
        [email_verified]        BIT            NOT NULL DEFAULT 0,
        [verification_status]   VARCHAR(32)    NOT NULL DEFAULT 'PENDING',
        [is_active]             BIT            NOT NULL DEFAULT 1,
        [created_at]            DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        [username]              VARCHAR(64)    NULL,
        [last_login]            DATETIME       NULL,
        [approved_at]           DATETIMEOFFSET NULL,
        [document_filename]     VARCHAR(256)   NULL,
        [document_path]         VARCHAR(512)   NULL,
        [document_uploaded_at]  DATETIMEOFFSET NULL,
        [verified_at]           DATETIMEOFFSET NULL,
        [verified_by]           VARCHAR(64)    NULL,
        [rejection_reason]      VARCHAR(512)   NULL,
        CONSTRAINT [PK_Doctors] PRIMARY KEY CLUSTERED ([doctor_id]),
        CONSTRAINT [UQ_Doctors_Email] UNIQUE NONCLUSTERED ([email]),
        CONSTRAINT [UQ_Doctors_RegNumber] UNIQUE NONCLUSTERED ([registration_number]),
        CONSTRAINT [CK_Doctors_VerificationStatus] CHECK ([verification_status] IN ('PENDING', 'APPROVED', 'REJECTED'))
    );

    CREATE NONCLUSTERED INDEX [IX_Doctors_Email] ON [clinical].[Doctors] ([email]);
    CREATE NONCLUSTERED INDEX [IX_Doctors_RegNumber] ON [clinical].[Doctors] ([registration_number]);
    CREATE NONCLUSTERED INDEX [IX_Doctors_VerificationStatus] ON [clinical].[Doctors] ([verification_status]);
END
GO

-- Ensure Filtered Unique Index on Doctors.username (allows multiple NULLs for pending doctors)
IF EXISTS (SELECT * FROM sys.key_constraints WHERE name = 'UQ_Doctors_Username' AND parent_object_id = OBJECT_ID('[clinical].[Doctors]'))
BEGIN
    ALTER TABLE [clinical].[Doctors] DROP CONSTRAINT [UQ_Doctors_Username];
END
GO
IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ_Doctors_Username' AND object_id = OBJECT_ID('[clinical].[Doctors]'))
BEGIN
    DROP INDEX [UQ_Doctors_Username] ON [clinical].[Doctors];
END
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ_Doctors_Username' AND object_id = OBJECT_ID('[clinical].[Doctors]'))
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX [UQ_Doctors_Username]
    ON [clinical].[Doctors] ([username])
    WHERE [username] IS NOT NULL;
END
GO

-- 3. Create Email OTP Verification Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[EmailOTP]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[EmailOTP] (
        [otp_id]      VARCHAR(64)    NOT NULL,
        [doctor_id]   VARCHAR(64)    NOT NULL,
        [otp_hash]    VARCHAR(256)   NOT NULL,
        [expires_at]  DATETIMEOFFSET NOT NULL,
        [attempts]    INT            NOT NULL DEFAULT 0,
        [is_used]     BIT            NOT NULL DEFAULT 0,
        [created_at]  DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT [PK_EmailOTP] PRIMARY KEY CLUSTERED ([otp_id]),
        CONSTRAINT [FK_EmailOTP_Doctors] FOREIGN KEY ([doctor_id])
            REFERENCES [clinical].[Doctors] ([doctor_id]) ON DELETE CASCADE
    );

    CREATE NONCLUSTERED INDEX [IX_EmailOTP_DoctorId] ON [clinical].[EmailOTP] ([doctor_id], [created_at] DESC);
    CREATE NONCLUSTERED INDEX [IX_EmailOTP_ExpiresAt] ON [clinical].[EmailOTP] ([expires_at]);
END
GO

-- 4. Create Administrators Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Administrators]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Administrators] (
        [admin_id]       VARCHAR(64)    NOT NULL,
        [username]       VARCHAR(64)    NOT NULL,
        [email]          VARCHAR(256)   NOT NULL,
        [password_hash]  VARCHAR(256)   NOT NULL,
        [full_name]      VARCHAR(128)   NOT NULL,
        [role]           VARCHAR(64)    NOT NULL DEFAULT 'Medical Credentialing Officer',
        [is_active]      BIT            NOT NULL DEFAULT 1,
        [created_at]     DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT [PK_Administrators] PRIMARY KEY CLUSTERED ([admin_id]),
        CONSTRAINT [UQ_Admin_Username] UNIQUE NONCLUSTERED ([username]),
        CONSTRAINT [UQ_Admin_Email] UNIQUE NONCLUSTERED ([email])
    );

    CREATE NONCLUSTERED INDEX [IX_Admin_Email] ON [clinical].[Administrators] ([email]);
END
GO

-- 5. Create DoctorSessions Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[DoctorSessions]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[DoctorSessions] (
        [session_id]         VARCHAR(64)    NOT NULL,
        [doctor_id]          VARCHAR(64)    NOT NULL,
        [refresh_token_hash] VARCHAR(256)   NOT NULL,
        [expires_at]         DATETIMEOFFSET NOT NULL,
        [is_revoked]         BIT            NOT NULL DEFAULT 0,
        [created_at]         DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        [user_agent]         VARCHAR(256)   NULL,
        [ip_address]         VARCHAR(64)    NULL,
        CONSTRAINT [PK_DoctorSessions] PRIMARY KEY CLUSTERED ([session_id]),
        CONSTRAINT [FK_DoctorSessions_Doctors] FOREIGN KEY ([doctor_id])
            REFERENCES [clinical].[Doctors] ([doctor_id]) ON DELETE CASCADE
    );

    CREATE NONCLUSTERED INDEX [IX_DoctorSessions_DoctorId] ON [clinical].[DoctorSessions] ([doctor_id], [created_at]);
    CREATE NONCLUSTERED INDEX [IX_DoctorSessions_ExpiresAt] ON [clinical].[DoctorSessions] ([expires_at]);
END
GO

-- Reconcile legacy Assessments / Predictions tables if schema columns are mismatched
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND type in (N'U'))
BEGIN
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND name = 'id')
       OR NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND name = 'patient_reference_id')
       OR NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND name = 'assessment_code')
    BEGIN
        DROP TABLE IF EXISTS [clinical].[Predictions];
        DROP TABLE IF EXISTS [clinical].[Assessments];
    END
END
GO

-- 6. Create Assessments Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Assessments] (
        -- Primary Surrogate Key (Internal UUID, VARCHAR(64) aligned with ORM model)
        [id]                          VARCHAR(64)      NOT NULL,
        
        -- Public-facing Clinical Identifier (e.g., ASM-2026-0001)
        [assessment_code]             VARCHAR(32)      NOT NULL,
        
        -- Optional Patient Reference Code (e.g., PT-8942 or NULL for anonymous)
        [patient_reference_id]        VARCHAR(64)      NULL,
        
        -- Physician attribution (VARCHAR(64) strictly matching Doctors.doctor_id)
        [doctor_id]                   VARCHAR(64)      NULL,
        
        -- 11 Patient Clinical Parameters (UCI Dataset Specs)
        [age]                         DECIMAL(5, 1)    NOT NULL,
        [anaemia]                     SMALLINT         NOT NULL,
        [creatinine_phosphokinase]    DECIMAL(8, 2)    NOT NULL,
        [diabetes]                    SMALLINT         NOT NULL,
        [ejection_fraction]           DECIMAL(5, 2)    NOT NULL,
        [high_blood_pressure]         SMALLINT         NOT NULL,
        [platelets]                   DECIMAL(10, 2)   NOT NULL,
        [serum_creatinine]            DECIMAL(5, 2)    NOT NULL,
        [serum_sodium]                DECIMAL(5, 2)    NOT NULL,
        [sex]                         SMALLINT         NOT NULL,
        [smoking]                     SMALLINT         NOT NULL,
        
        -- Model Inference Tracking
        [selected_model]              VARCHAR(64)      NULL,
        [predicted_class]             SMALLINT         NULL,
        [predicted_probability]       DECIMAL(6, 4)    NULL,
        [prediction_timestamp]        DATETIMEOFFSET   NULL,
        [is_prediction_stale]         BIT              NOT NULL DEFAULT 0,
        [version]                     INT              NOT NULL DEFAULT 1,

        -- Audit Timestamps
        [created_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        [updated_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),

        -- Constraints
        CONSTRAINT [PK_Assessments] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Assessments_Code] UNIQUE NONCLUSTERED ([assessment_code]),
        CONSTRAINT [FK_Assessments_Doctors] FOREIGN KEY ([doctor_id])
            REFERENCES [clinical].[Doctors] ([doctor_id])
            ON DELETE SET NULL,

        -- Range Checks
        CONSTRAINT [CK_Assessments_Age] 
            CHECK ([age] >= 1.0 AND [age] <= 120.0),
        CONSTRAINT [CK_Assessments_Anaemia] 
            CHECK ([anaemia] IN (0, 1)),
        CONSTRAINT [CK_Assessments_CPK] 
            CHECK ([creatinine_phosphokinase] > 0.0 AND [creatinine_phosphokinase] <= 20000.0),
        CONSTRAINT [CK_Assessments_Diabetes] 
            CHECK ([diabetes] IN (0, 1)),
        CONSTRAINT [CK_Assessments_EF] 
            CHECK ([ejection_fraction] >= 1.0 AND [ejection_fraction] <= 100.0),
        CONSTRAINT [CK_Assessments_HBP] 
            CHECK ([high_blood_pressure] IN (0, 1)),
        CONSTRAINT [CK_Assessments_Platelets] 
            CHECK ([platelets] > 0.0 AND [platelets] <= 2000000.0),
        CONSTRAINT [CK_Assessments_Creatinine] 
            CHECK ([serum_creatinine] >= 0.1 AND [serum_creatinine] <= 30.0),
        CONSTRAINT [CK_Assessments_Sodium] 
            CHECK ([serum_sodium] >= 50.0 AND [serum_sodium] <= 200.0),
        CONSTRAINT [CK_Assessments_Sex] 
            CHECK ([sex] IN (0, 1)),
        CONSTRAINT [CK_Assessments_Smoking] 
            CHECK ([smoking] IN (0, 1)),
        CONSTRAINT [CK_Assessments_PredictedClass] 
            CHECK ([predicted_class] IS NULL OR [predicted_class] IN (0, 1)),
        CONSTRAINT [CK_Assessments_PredictedProb] 
            CHECK ([predicted_probability] IS NULL OR ([predicted_probability] >= 0.0 AND [predicted_probability] <= 1.0))
    );
END
GO

-- Indexes on Assessments
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Assessments_PatientRef' AND object_id = OBJECT_ID('[clinical].[Assessments]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Assessments_PatientRef]
    ON [clinical].[Assessments] ([patient_reference_id])
    WHERE [patient_reference_id] IS NOT NULL;
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Assessments_CreatedAt' AND object_id = OBJECT_ID('[clinical].[Assessments]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Assessments_CreatedAt]
    ON [clinical].[Assessments] ([created_at] DESC);
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Assessments_DoctorId' AND object_id = OBJECT_ID('[clinical].[Assessments]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Assessments_DoctorId]
    ON [clinical].[Assessments] ([doctor_id], [created_at] DESC);
END
GO

-- Audit Trigger to maintain updated_at
IF OBJECT_ID(N'[clinical].[TR_Assessments_UpdateAudit]', N'TR') IS NOT NULL
    DROP TRIGGER [clinical].[TR_Assessments_UpdateAudit];
GO

CREATE TRIGGER [clinical].[TR_Assessments_UpdateAudit]
ON [clinical].[Assessments]
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE a
    SET [updated_at] = SYSDATETIMEOFFSET()
    FROM [clinical].[Assessments] a
    INNER JOIN inserted i ON a.id = i.id;
END;
GO

-- 7. Create Predictions Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Predictions]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Predictions] (
        [id]                          VARCHAR(64)      NOT NULL,
        [prediction_code]             VARCHAR(32)      NOT NULL,
        [assessment_id]               VARCHAR(64)      NOT NULL,
        [model_name]                  VARCHAR(64)      NOT NULL,
        [predicted_class]             SMALLINT         NOT NULL,
        [predicted_probability]       DECIMAL(6, 4)    NOT NULL,
        [classification_threshold]    DECIMAL(4, 2)    NOT NULL DEFAULT 0.50,
        [model_version]               VARCHAR(32)      NOT NULL DEFAULT 'v1.0.0',
        [created_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT [PK_Predictions] PRIMARY KEY CLUSTERED ([id]),
        CONSTRAINT [UQ_Predictions_Code] UNIQUE NONCLUSTERED ([prediction_code]),
        CONSTRAINT [FK_Predictions_Assessments] FOREIGN KEY ([assessment_id])
            REFERENCES [clinical].[Assessments] ([id])
            ON DELETE CASCADE,
        CONSTRAINT [CK_Predictions_Class] CHECK ([predicted_class] IN (0, 1)),
        CONSTRAINT [CK_Predictions_Prob] CHECK ([predicted_probability] >= 0.0 AND [predicted_probability] <= 1.0)
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Predictions_AssessmentId' AND object_id = OBJECT_ID('[clinical].[Predictions]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Predictions_AssessmentId]
    ON [clinical].[Predictions] ([assessment_id], [created_at] DESC);
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Predictions_CreatedAt' AND object_id = OBJECT_ID('[clinical].[Predictions]'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_Predictions_CreatedAt]
    ON [clinical].[Predictions] ([created_at] DESC);
END
GO
