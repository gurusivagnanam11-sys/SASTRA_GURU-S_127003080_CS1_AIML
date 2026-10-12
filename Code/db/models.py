from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    document_id = Column(String, unique=True, nullable=False)
    project_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    document_type = Column(String, default='hld')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DocumentVersion(Base):
    __tablename__ = 'document_versions'
    id = Column(Integer, primary_key=True)
    document_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    page_count = Column(Integer)
    ingestion_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_path = Column(String)

class Chunk(Base):
    __tablename__ = 'chunks'
    id = Column(Integer, primary_key=True)
    chunk_id = Column(String, unique=True, nullable=False)
    document_id = Column(String, nullable=False)
    version = Column(String, nullable=False)
    page_number = Column(Integer)
    section = Column(String)
    section_title = Column(String)
    chunk_type = Column(String)
    entity_hint = Column(String)
    text = Column(Text)
    extraction_method = Column(String, default="text")


class ReviewRecord(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    decision = Column(String, nullable=False)  # accepted, rejected, modified
    engineer_id = Column(String, default="engineer_1")
    feedback = Column(Text, nullable=True)
    corrections = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EngineeringReviewRecord(Base):
    """Phase 8: Enhanced engineering review workflow record."""
    __tablename__ = 'engineering_reviews'
    id = Column(Integer, primary_key=True)
    report_type = Column(String, nullable=False, default="general")
    report_identifier = Column(String, nullable=False, default="")
    reviewer = Column(String, nullable=False, default="Engineering Reviewer")
    decision = Column(String, nullable=False)  # PENDING_REVIEW, ENGINEER_APPROVED, ENGINEER_CORRECTED, ENGINEER_REJECTED
    comment = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    source_document = Column(String, nullable=True)
    source_version = Column(String, nullable=True)
    original_result_summary = Column(Text, nullable=True)
    final_reviewed_result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GovernanceRecord(Base):
    """Phase 8: Document governance status audit trail."""
    __tablename__ = 'governance_audit'
    id = Column(Integer, primary_key=True)
    document_id = Column(String, nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    changed_by = Column(String, nullable=False, default="system")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
