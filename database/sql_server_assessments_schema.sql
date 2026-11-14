-- ==============================================================================
-- Heart Failure Mortality Risk Predictor — Microsoft SQL Server Database Schema
-- Table: Assessments
-- Version: 1.0.0
-- Description: Stores recorded clinical biomarkers and metadata for patient
--              heart failure risk evaluations.
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
        [doctor_id]             NVARCHAR(64)   NOT NULL,
        [full_name]             NVARCHAR(128)  NOT NULL,
        [email]                 NVARCHAR(256)  NOT NULL,
        [password_hash]         NVARCHAR(256)  NOT NULL,
        [mobile]                NVARCHAR(32)   NOT NULL,
        [medical_degree]        NVARCHAR(128)  NOT NULL,
        [registration_number]   NVARCHAR(64)   NOT NULL,
        [registration_council]  NVARCHAR(128)  NOT NULL,
        [email_verified]        BIT            NOT NULL DEFAULT 0,
        [verification_status]   NVARCHAR(32)   NOT NULL DEFAULT N'PENDING',
        [is_active]             BIT            NOT NULL DEFAULT 1,
        [created_at]            DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        [document_filename]     NVARCHAR(256)  NULL,
        [document_path]         NVARCHAR(512)  NULL,
        [document_uploaded_at]  DATETIMEOFFSET NULL,
        [verified_at]           DATETIMEOFFSET NULL,
        [verified_by]           NVARCHAR(64)   NULL,
        [rejection_reason]      NVARCHAR(512)  NULL,
        CONSTRAINT [PK_Doctors] PRIMARY KEY CLUSTERED ([doctor_id]),
        CONSTRAINT [UQ_Doctors_Email] UNIQUE NONCLUSTERED ([email]),
        CONSTRAINT [UQ_Doctors_RegNumber] UNIQUE NONCLUSTERED ([registration_number]),
        CONSTRAINT [CK_Doctors_VerificationStatus] CHECK ([verification_status] IN (N'PENDING', N'APPROVED', N'REJECTED'))
    );

    CREATE NONCLUSTERED INDEX [IX_Doctors_Email] ON [clinical].[Doctors] ([email]);
    CREATE NONCLUSTERED INDEX [IX_Doctors_RegNumber] ON [clinical].[Doctors] ([registration_number]);
    CREATE NONCLUSTERED INDEX [IX_Doctors_VerificationStatus] ON [clinical].[Doctors] ([verification_status]);
END
GO

-- 2B. Create Email OTP Verification Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[EmailOTP]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[EmailOTP] (
        [otp_id]      NVARCHAR(64)   NOT NULL,
        [doctor_id]   NVARCHAR(64)   NOT NULL,
        [otp_hash]    NVARCHAR(256)  NOT NULL,
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

-- 2C. Create Administrators Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Administrators]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Administrators] (
        [admin_id]       NVARCHAR(64)   NOT NULL,
        [username]       NVARCHAR(64)   NOT NULL,
        [email]          NVARCHAR(256)  NOT NULL,
        [password_hash]  NVARCHAR(256)  NOT NULL,
        [full_name]      NVARCHAR(128)  NOT NULL,
        [role]           NVARCHAR(64)   NOT NULL DEFAULT N'Medical Credentialing Officer',
        [is_active]      BIT            NOT NULL DEFAULT 1,
        [created_at]     DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT [PK_Administrators] PRIMARY KEY CLUSTERED ([admin_id]),
        CONSTRAINT [UQ_Admin_Username] UNIQUE NONCLUSTERED ([username]),
        CONSTRAINT [UQ_Admin_Email] UNIQUE NONCLUSTERED ([email])
    );

    CREATE NONCLUSTERED INDEX [IX_Admin_Email] ON [clinical].[Administrators] ([email]);
END
GO

-- 3. Create Assessments Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Assessments]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Assessments] (
        -- Primary Surrogate Key (Internal UUID, never exposed directly in UI)
        [id]                          UNIQUEIDENTIFIER NOT NULL DEFAULT NEWSEQUENTIALID(),
        
        -- Public-facing Clinical Identifier (e.g., ASM-2026-0001)
        [assessment_code]             NVARCHAR(32)     NOT NULL,
        
        -- Optional Patient Reference Code (e.g., PT-8942 or NULL for anonymous)
        [patient_reference_id]        NVARCHAR(64)     NULL,
        
        -- Physician attribution
        [doctor_id]                   NVARCHAR(64)     NULL,
        
        -- 11 Patient Clinical Parameters (UCI Dataset Specs)
        [age]                         DECIMAL(5, 1)    NOT NULL,
        [anaemia]                     TINYINT          NOT NULL,
        [creatinine_phosphokinase]    DECIMAL(8, 2)    NOT NULL,
        [diabetes]                    TINYINT          NOT NULL,
        [ejection_fraction]           DECIMAL(5, 2)    NOT NULL,
        [high_blood_pressure]         TINYINT          NOT NULL,
        [platelets]                   DECIMAL(10, 2)   NOT NULL,
        [serum_creatinine]            DECIMAL(5, 2)    NOT NULL,
        [serum_sodium]                DECIMAL(5, 2)    NOT NULL,
        [sex]                         TINYINT          NOT NULL,
        [smoking]                     TINYINT          NOT NULL,
        
        -- Model Inference Tracking
        [selected_model]              NVARCHAR(64)     NULL,
        [predicted_class]             TINYINT          NULL,
        [predicted_probability]       DECIMAL(6, 4)    NULL,
        [prediction_timestamp]        DATETIMEOFFSET   NULL,
        [is_prediction_stale]         BIT              NOT NULL DEFAULT 0,
        [version]                     INT              NOT NULL DEFAULT 1,

        -- Audit Timestamps
        [created_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        [updated_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),

        -- Primary Key
        CONSTRAINT [PK_Assessments] PRIMARY KEY CLUSTERED ([id]),
        
        -- Unique Public Code
        CONSTRAINT [UQ_Assessments_Code] UNIQUE NONCLUSTERED ([assessment_code]),

        -- Foreign Key to Doctors
        CONSTRAINT [FK_Assessments_Doctors] FOREIGN KEY ([doctor_id])
            REFERENCES [clinical].[Doctors] ([doctor_id])
            ON DELETE SET NULL,

        -- Clinical Range Check Constraints
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

-- 4. Create Performance Indexes for Search & Filter queries
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

-- 5. Audit Trigger to automatically maintain [updated_at] timestamp
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

-- 6. Create Predictions Table
-- One assessment may have multiple prediction records (e.g., comparing models or repeated runs)
-- Records are immutable and never overwritten upon re-prediction.
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Predictions]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Predictions] (
        -- Primary Key
        [id]                          UNIQUEIDENTIFIER NOT NULL DEFAULT NEWSEQUENTIALID(),

        -- Public Prediction Identifier (e.g., PRD-2026-0001)
        [prediction_code]             NVARCHAR(32)     NOT NULL,

        -- Foreign Key to Parent Assessment
        [assessment_id]               UNIQUEIDENTIFIER NOT NULL,

        -- Model Details
        [model_name]                  NVARCHAR(64)     NOT NULL,
        [predicted_class]             TINYINT          NOT NULL,
        [predicted_probability]       DECIMAL(6, 4)    NOT NULL,
        [classification_threshold]    DECIMAL(4, 2)    NOT NULL DEFAULT 0.50,
        [model_version]               NVARCHAR(32)     NOT NULL DEFAULT N'v1.0.0',

        -- Audit Timestamp
        [created_at]                  DATETIMEOFFSET   NOT NULL DEFAULT SYSDATETIMEOFFSET(),

        -- Constraints
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

-- 7. Performance Indexes for Predictions
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


