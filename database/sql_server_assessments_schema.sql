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

-- 2. Create Doctors Reference Table (Optional parent entity)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Doctors]') AND type in (N'U'))
BEGIN
    CREATE TABLE [clinical].[Doctors] (
        [doctor_id]           NVARCHAR(64)   NOT NULL,
        [full_name]           NVARCHAR(128)  NOT NULL,
        [email]               NVARCHAR(256)  NOT NULL,
        [clinical_role]       NVARCHAR(64)   NOT NULL DEFAULT N'Attending Physician',
        [is_active]           BIT            NOT NULL DEFAULT 1,
        [created_at]          DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
        CONSTRAINT [PK_Doctors] PRIMARY KEY CLUSTERED ([doctor_id]),
        CONSTRAINT [UQ_Doctors_Email] UNIQUE NONCLUSTERED ([email])
    );
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


