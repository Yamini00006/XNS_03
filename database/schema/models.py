"""
database/schema/models.py

SQLAlchemy ORM models for the Customer Data Platform.
These are the authoritative table definitions.

Tables:
  - upload_files       : tracks every file uploaded by users
  - processing_jobs    : tracks ETL job status per file
  - customers          : standardized, merged customer records
  - customer_sources   : raw source data rows (data lineage)
  - validation_errors  : per-row/field validation failures
  - data_quality       : aggregate quality metrics per job
  - processing_logs    : detailed log lines per job
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, Index, Enum as SAEnum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────

class FileFormat(str, enum.Enum):
    CSV  = "csv"
    JSON = "json"
    XLSX = "xlsx"
    XML  = "xml"
    PDF  = "pdf"


class JobStatus(str, enum.Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class ValidationSeverity(str, enum.Enum):
    ERROR   = "error"
    WARNING = "warning"


# ─── Tables ──────────────────────────────────────────────────────────────────

class UploadFile(Base):
    """
    One row per file uploaded by a user.
    Created by the backend (Member 2) when a file arrives via the API.
    The data pipeline reads from this table to know what to process.
    """
    __tablename__ = "upload_files"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    original_name   = Column(String(255), nullable=False)
    stored_path     = Column(String(512), nullable=False)          # path on disk / object store
    file_format     = Column(SAEnum(FileFormat), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    uploaded_by     = Column(Integer, nullable=True)               # FK to auth_user (backend owns that table)
    uploaded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    checksum_md5    = Column(String(32), nullable=True)

    jobs            = relationship("ProcessingJob", back_populates="upload_file")

    __table_args__ = (
        Index("ix_upload_files_format", "file_format"),
        Index("ix_upload_files_uploaded_at", "uploaded_at"),
    )


class ProcessingJob(Base):
    """
    One row per processing attempt of an uploaded file.
    A file can be re-processed (multiple jobs), so this is separate from UploadFile.
    Status transitions: QUEUED → RUNNING → COMPLETED | FAILED
    The background worker (Member 4) triggers pipeline.run(); this table is
    updated by the pipeline itself.
    """
    __tablename__ = "processing_jobs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    upload_file_id   = Column(Integer, ForeignKey("upload_files.id"), nullable=False)
    status           = Column(SAEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    started_at       = Column(DateTime, nullable=True)
    completed_at     = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    rows_extracted   = Column(Integer, default=0)
    rows_valid       = Column(Integer, default=0)
    rows_invalid     = Column(Integer, default=0)
    rows_merged      = Column(Integer, default=0)
    error_message    = Column(Text, nullable=True)               # top-level failure reason
    pipeline_version = Column(String(20), default="1.0.0")

    upload_file      = relationship("UploadFile", back_populates="jobs")
    validation_errors = relationship("ValidationError", back_populates="job")
    quality_report   = relationship("DataQuality", back_populates="job", uselist=False)
    logs             = relationship("ProcessingLog", back_populates="job")

    __table_args__ = (
        Index("ix_processing_jobs_status", "status"),
        Index("ix_processing_jobs_upload_file_id", "upload_file_id"),
    )


class Customer(Base):
    """
    Standardized, deduplicated customer records.
    This is the golden record produced after merging data from all sources.
    Downstream: the backend (Member 2) exposes this via the Data Explorer API.
    """
    __tablename__ = "customers"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    # Core identity fields (standardized)
    email            = Column(String(255), nullable=True, index=True)
    phone            = Column(String(30), nullable=True)
    full_name        = Column(String(255), nullable=True)
    first_name       = Column(String(100), nullable=True)
    last_name        = Column(String(100), nullable=True)
    # Address
    address_line1    = Column(String(255), nullable=True)
    address_line2    = Column(String(255), nullable=True)
    city             = Column(String(100), nullable=True)
    state            = Column(String(100), nullable=True)
    postal_code      = Column(String(20), nullable=True)
    country          = Column(String(100), nullable=True)
    # Additional fields stored as JSON to handle varying source schemas
    extra_fields     = Column(JSON, nullable=True)
    # Merge metadata
    source_count     = Column(Integer, default=1)               # how many sources contributed
    is_duplicate     = Column(Boolean, default=False)           # merged into another record
    merged_into_id   = Column(Integer, ForeignKey("customers.id"), nullable=True)
    # Timestamps
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources          = relationship("CustomerSource", back_populates="customer")

    __table_args__ = (
        Index("ix_customers_email", "email"),
        Index("ix_customers_phone", "phone"),
        Index("ix_customers_full_name", "full_name"),
    )


class CustomerSource(Base):
    """
    Raw source rows before transformation — preserves data lineage.
    Every row extracted from a file gets one entry here, linked to the
    final Customer record it contributed to.
    """
    __tablename__ = "customer_sources"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    customer_id    = Column(Integer, ForeignKey("customers.id"), nullable=True)   # null until merged
    job_id         = Column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    upload_file_id = Column(Integer, ForeignKey("upload_files.id"), nullable=False)
    source_row_num = Column(Integer, nullable=True)            # original row number in file
    raw_data       = Column(JSON, nullable=False)              # original row as-extracted
    mapped_data    = Column(JSON, nullable=True)               # after schema mapping
    is_valid       = Column(Boolean, default=True)
    extracted_at   = Column(DateTime, default=datetime.utcnow)

    customer       = relationship("Customer", back_populates="sources")

    __table_args__ = (
        Index("ix_customer_sources_job_id", "job_id"),
        Index("ix_customer_sources_customer_id", "customer_id"),
        Index("ix_customer_sources_upload_file_id", "upload_file_id"),
    )


class ValidationError(Base):
    """
    One row per validation failure (field-level or row-level).
    Linked to the job, and optionally to the specific source row.
    Exposed via the backend's error log API.
    """
    __tablename__ = "validation_errors"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    job_id         = Column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    source_row_id  = Column(Integer, ForeignKey("customer_sources.id"), nullable=True)
    row_number     = Column(Integer, nullable=True)
    field_name     = Column(String(100), nullable=True)
    error_code     = Column(String(50), nullable=False)         # e.g. "INVALID_EMAIL"
    error_message  = Column(Text, nullable=False)
    severity       = Column(SAEnum(ValidationSeverity), default=ValidationSeverity.ERROR)
    raw_value      = Column(Text, nullable=True)                # the bad value itself
    created_at     = Column(DateTime, default=datetime.utcnow)

    job            = relationship("ProcessingJob", back_populates="validation_errors")

    __table_args__ = (
        Index("ix_validation_errors_job_id", "job_id"),
        Index("ix_validation_errors_error_code", "error_code"),
    )


class DataQuality(Base):
    """
    Aggregate data quality metrics for one processing job.
    One row per job. Used by the dashboard API (Member 2).
    """
    __tablename__ = "data_quality"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    job_id                  = Column(Integer, ForeignKey("processing_jobs.id"), unique=True, nullable=False)
    total_rows              = Column(Integer, default=0)
    valid_rows              = Column(Integer, default=0)
    invalid_rows            = Column(Integer, default=0)
    duplicate_rows          = Column(Integer, default=0)
    missing_fields_count    = Column(Integer, default=0)        # total missing field occurrences
    missing_pct             = Column(Float, default=0.0)        # % of fields that are null/empty
    validation_error_count  = Column(Integer, default=0)
    completeness_score      = Column(Float, default=0.0)        # 0–100
    uniqueness_score        = Column(Float, default=0.0)        # 0–100
    computed_at             = Column(DateTime, default=datetime.utcnow)

    job                     = relationship("ProcessingJob", back_populates="quality_report")

    __table_args__ = (
        Index("ix_data_quality_job_id", "job_id"),
    )


class ProcessingLog(Base):
    """
    Detailed structured log lines for a processing job.
    Complements the infrastructure-level logging (Member 4).
    Lets the backend expose per-job logs via the API.
    """
    __tablename__ = "processing_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    job_id     = Column(Integer, ForeignKey("processing_jobs.id"), nullable=False)
    level      = Column(String(10), nullable=False)             # INFO / WARNING / ERROR
    stage      = Column(String(50), nullable=True)              # extract / transform / validate / merge / load
    message    = Column(Text, nullable=False)
    detail     = Column(JSON, nullable=True)                    # extra structured data
    logged_at  = Column(DateTime, default=datetime.utcnow)

    job        = relationship("ProcessingJob", back_populates="logs")

    __table_args__ = (
        Index("ix_processing_logs_job_id", "job_id"),
        Index("ix_processing_logs_level", "level"),
    )
