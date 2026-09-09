CREATE TYPE batch_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed'
);

CREATE TABLE processing_batches (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    status          batch_status NOT NULL DEFAULT 'queued',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP NULL,
    error_message   TEXT NULL
);

CREATE INDEX ix_processing_batches_status
    ON processing_batches(status);

CREATE INDEX ix_processing_batches_created_at
    ON processing_batches(created_at);

ALTER TABLE upload_files
    ADD COLUMN batch_id INTEGER NULL
    REFERENCES processing_batches(id);

CREATE INDEX ix_upload_files_batch_id
    ON upload_files(batch_id);

ALTER TABLE processing_jobs
    ADD COLUMN batch_id INTEGER NULL
    REFERENCES processing_batches(id);

CREATE INDEX ix_processing_jobs_batch_id
    ON processing_jobs(batch_id);

ALTER TABLE customers
    ADD COLUMN batch_id INTEGER NULL
    REFERENCES processing_batches(id);

CREATE INDEX ix_customers_batch_id
    ON customers(batch_id);