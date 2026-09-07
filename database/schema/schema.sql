-- =============================================================
-- Customer Data Platform — Database Schema
-- Database: PostgreSQL 15+
-- Member 3 owns this file.
-- =============================================================

-- Enums
CREATE TYPE file_format AS ENUM ('csv', 'json', 'xlsx', 'xml', 'pdf');
CREATE TYPE job_status AS ENUM ('queued', 'running', 'completed', 'failed');
CREATE TYPE validation_severity AS ENUM ('error', 'warning');

-- ──────────────────────────────────────────────────────────────
-- upload_files
-- Populated by the backend (Member 2) when a file is uploaded.
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS upload_files (
    id               SERIAL PRIMARY KEY,
    original_name    VARCHAR(255)  NOT NULL,
    stored_path      VARCHAR(512)  NOT NULL,
    file_format      file_format   NOT NULL,
    file_size_bytes  INTEGER,
    uploaded_by      INTEGER,                        -- FK to auth_user (backend table)
    uploaded_at      TIMESTAMP     NOT NULL DEFAULT NOW(),
    checksum_md5     CHAR(32)
);

CREATE INDEX ix_upload_files_format      ON upload_files (file_format);
CREATE INDEX ix_upload_files_uploaded_at ON upload_files (uploaded_at);

-- ──────────────────────────────────────────────────────────────
-- processing_jobs
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processing_jobs (
    id               SERIAL PRIMARY KEY,
    upload_file_id   INTEGER       NOT NULL REFERENCES upload_files(id) ON DELETE CASCADE,
    status           job_status    NOT NULL DEFAULT 'queued',
    started_at       TIMESTAMP,
    completed_at     TIMESTAMP,
    duration_seconds FLOAT,
    rows_extracted   INTEGER       NOT NULL DEFAULT 0,
    rows_valid       INTEGER       NOT NULL DEFAULT 0,
    rows_invalid     INTEGER       NOT NULL DEFAULT 0,
    rows_merged      INTEGER       NOT NULL DEFAULT 0,
    error_message    TEXT,
    pipeline_version VARCHAR(20)   NOT NULL DEFAULT '1.0.0'
);

CREATE INDEX ix_processing_jobs_status         ON processing_jobs (status);
CREATE INDEX ix_processing_jobs_upload_file_id ON processing_jobs (upload_file_id);

-- ──────────────────────────────────────────────────────────────
-- customers  (golden records)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id             SERIAL PRIMARY KEY,
    email          VARCHAR(255),
    phone          VARCHAR(30),
    full_name      VARCHAR(255),
    first_name     VARCHAR(100),
    last_name      VARCHAR(100),
    address_line1  VARCHAR(255),
    address_line2  VARCHAR(255),
    city           VARCHAR(100),
    state          VARCHAR(100),
    postal_code    VARCHAR(20),
    country        VARCHAR(100),
    extra_fields   JSONB,
    source_count   INTEGER       NOT NULL DEFAULT 1,
    is_duplicate   BOOLEAN       NOT NULL DEFAULT FALSE,
    merged_into_id INTEGER       REFERENCES customers(id),
    created_at     TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_customers_email     ON customers (email);
CREATE INDEX ix_customers_phone     ON customers (phone);
CREATE INDEX ix_customers_full_name ON customers (full_name);
-- GIN index for searching inside extra_fields JSON
CREATE INDEX ix_customers_extra_gin ON customers USING GIN (extra_fields);

-- ──────────────────────────────────────────────────────────────
-- customer_sources  (data lineage)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customer_sources (
    id             SERIAL PRIMARY KEY,
    customer_id    INTEGER       REFERENCES customers(id) ON DELETE SET NULL,
    job_id         INTEGER       NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
    upload_file_id INTEGER       NOT NULL REFERENCES upload_files(id) ON DELETE CASCADE,
    source_row_num INTEGER,
    raw_data       JSONB         NOT NULL,
    mapped_data    JSONB,
    is_valid       BOOLEAN       NOT NULL DEFAULT TRUE,
    extracted_at   TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_customer_sources_job_id         ON customer_sources (job_id);
CREATE INDEX ix_customer_sources_customer_id    ON customer_sources (customer_id);
CREATE INDEX ix_customer_sources_upload_file_id ON customer_sources (upload_file_id);
CREATE INDEX ix_customer_sources_raw_gin        ON customer_sources USING GIN (raw_data);

-- ──────────────────────────────────────────────────────────────
-- validation_errors
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS validation_errors (
    id             SERIAL PRIMARY KEY,
    job_id         INTEGER              NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
    source_row_id  INTEGER              REFERENCES customer_sources(id) ON DELETE SET NULL,
    row_number     INTEGER,
    field_name     VARCHAR(100),
    error_code     VARCHAR(50)          NOT NULL,
    error_message  TEXT                 NOT NULL,
    severity       validation_severity  NOT NULL DEFAULT 'error',
    raw_value      TEXT,
    created_at     TIMESTAMP            NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_validation_errors_job_id     ON validation_errors (job_id);
CREATE INDEX ix_validation_errors_error_code ON validation_errors (error_code);

-- ──────────────────────────────────────────────────────────────
-- data_quality  (one row per job)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_quality (
    id                     SERIAL PRIMARY KEY,
    job_id                 INTEGER  NOT NULL UNIQUE REFERENCES processing_jobs(id) ON DELETE CASCADE,
    total_rows             INTEGER  NOT NULL DEFAULT 0,
    valid_rows             INTEGER  NOT NULL DEFAULT 0,
    invalid_rows           INTEGER  NOT NULL DEFAULT 0,
    duplicate_rows         INTEGER  NOT NULL DEFAULT 0,
    missing_fields_count   INTEGER  NOT NULL DEFAULT 0,
    missing_pct            FLOAT    NOT NULL DEFAULT 0.0,
    validation_error_count INTEGER  NOT NULL DEFAULT 0,
    completeness_score     FLOAT    NOT NULL DEFAULT 0.0,
    uniqueness_score       FLOAT    NOT NULL DEFAULT 0.0,
    computed_at            TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_data_quality_job_id ON data_quality (job_id);

-- ──────────────────────────────────────────────────────────────
-- processing_logs
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS processing_logs (
    id         SERIAL PRIMARY KEY,
    job_id     INTEGER      NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
    level      VARCHAR(10)  NOT NULL,
    stage      VARCHAR(50),
    message    TEXT         NOT NULL,
    detail     JSONB,
    logged_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_processing_logs_job_id ON processing_logs (job_id);
CREATE INDEX ix_processing_logs_level  ON processing_logs (level);

-- ──────────────────────────────────────────────────────────────
-- Trigger: auto-update customers.updated_at
-- ──────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated_at
BEFORE UPDATE ON customers
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
