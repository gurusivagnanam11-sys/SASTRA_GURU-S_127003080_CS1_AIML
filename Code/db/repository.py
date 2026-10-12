import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from app.config import DB_PATH
from db.models import Base, Document, DocumentVersion, Chunk, ReviewRecord, EngineeringReviewRecord, GovernanceRecord
from chunking.models import HLDChunk

logger = logging.getLogger(__name__)

class HLDRepository:
    def __init__(self, db_path: Path = None):
        path = db_path or DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}")
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine))

    def init_db(self) -> None:
        """Create all tables."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables initialized successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def save_document(self, metadata: Any) -> None:
        """Save document and document version metadata."""
        session = self.SessionFactory()
        try:
            # Check if document exists
            doc = session.query(Document).filter_by(document_id=metadata.document_id).first()
            if not doc:
                doc = Document(
                    document_id=metadata.document_id,
                    project_id=metadata.project_id,
                    filename=metadata.filename,
                    document_type=getattr(metadata, 'document_type', 'hld'),
                    created_at=datetime.now(timezone.utc)
                )
                session.add(doc)
            
            # Save version info
            version = DocumentVersion(
                document_id=metadata.document_id,
                version=metadata.version,
                page_count=getattr(metadata, 'page_count', 0),
                ingestion_timestamp=datetime.now(timezone.utc),
                source_path=str(getattr(metadata, 'source_path', ''))
            )
            session.add(version)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save document metadata: {e}")
            raise
        finally:
            session.close()

    def save_chunks(self, chunks: List[HLDChunk]) -> None:
        """Save chunk details into database."""
        session = self.SessionFactory()
        try:
            for c in chunks:
                existing = session.query(Chunk).filter_by(chunk_id=c.chunk_id).first()
                if existing:
                    existing.document_id = c.document_id
                    existing.version = c.version
                    existing.page_number = c.page_number
                    existing.section = c.section
                    existing.section_title = c.section_title
                    existing.chunk_type = c.chunk_type
                    existing.entity_hint = c.entity_hint
                    existing.text = c.text
                    existing.extraction_method = getattr(c, 'extraction_method', 'text')
                else:
                    chunk_record = Chunk(
                        chunk_id=c.chunk_id,
                        document_id=c.document_id,
                        version=c.version,
                        page_number=c.page_number,
                        section=c.section,
                        section_title=c.section_title,
                        chunk_type=c.chunk_type,
                        entity_hint=c.entity_hint,
                        text=c.text,
                        extraction_method=getattr(c, 'extraction_method', 'text')
                    )
                    session.add(chunk_record)
            session.commit()
            logger.info(f"Saved {len(chunks)} chunks to database.")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save chunks: {e}")
            raise
        finally:
            session.close()

    def get_chunks(self, document_id: str = None, version: str = None) -> List[dict]:
        """Fetch chunks by document and/or version."""
        session = self.SessionFactory()
        try:
            query = session.query(Chunk)
            if document_id:
                query = query.filter(Chunk.document_id == document_id)
            if version:
                query = query.filter(Chunk.version == version)
                
            results = query.all()
            return [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "version": r.version,
                    "page_number": r.page_number,
                    "section": r.section,
                    "section_title": r.section_title,
                    "chunk_type": r.chunk_type,
                    "entity_hint": r.entity_hint,
                    "text": r.text,
                    "extraction_method": getattr(r, 'extraction_method', 'text')
                }
                for r in results
            ]
        finally:
            session.close()

    def get_documents(self) -> List[dict]:
        """Get a list of all documents."""
        session = self.SessionFactory()
        try:
            results = session.query(Document).all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "project_id": r.project_id,
                    "filename": r.filename,
                    "document_type": r.document_type,
                    "created_at": r.created_at
                }
                for r in results
            ]
        finally:
            session.close()

    def get_stats(self) -> dict:
        """Get database statistics: doc count, version count, chunk count, etc."""
        session = self.SessionFactory()
        try:
            doc_count = session.query(func.count(Document.id)).scalar()
            version_count = session.query(func.count(DocumentVersion.id)).scalar()
            chunk_count = session.query(func.count(Chunk.id)).scalar()
            
            return {
                "document_count": doc_count,
                "version_count": version_count,
                "chunk_count": chunk_count
            }
        finally:
            session.close()

    def save_review(
        self,
        question: str,
        decision: str,
        engineer_id: str = "engineer_1",
        feedback: Optional[str] = None,
        corrections: Optional[str] = None,
    ) -> dict:
        """Record an engineer review for a generated answer."""
        self.init_db()
        session = self.SessionFactory()
        try:
            review = ReviewRecord(
                question=question,
                decision=decision,
                engineer_id=engineer_id,
                feedback=feedback,
                corrections=corrections,
                created_at=datetime.now(timezone.utc),
            )
            session.add(review)
            session.commit()
            return {
                "id": review.id,
                "question": review.question,
                "decision": review.decision,
                "engineer_id": review.engineer_id,
                "feedback": review.feedback,
                "corrections": review.corrections,
                "created_at": review.created_at.isoformat() if review.created_at else None,
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save review: {e}")
            raise
        finally:
            session.close()

    def get_reviews(self, limit: int = 100) -> List[dict]:
        """Fetch recorded engineer reviews."""
        self.init_db()
        session = self.SessionFactory()
        try:
            results = session.query(ReviewRecord).order_by(ReviewRecord.id.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "question": r.question,
                    "decision": r.decision,
                    "engineer_id": r.engineer_id,
                    "feedback": r.feedback,
                    "corrections": r.corrections,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in results
            ]
        finally:
            session.close()

    # ==========================================
    # Phase 8: Engineering Reviews
    # ==========================================

    def save_engineering_review(
        self,
        report_type: str,
        report_identifier: str,
        decision: str,
        reviewer: str = "Engineering Reviewer",
        comment: Optional[str] = None,
        correction: Optional[str] = None,
        source_document: Optional[str] = None,
        source_version: Optional[str] = None,
        original_result_summary: Optional[str] = None,
        final_reviewed_result: Optional[str] = None,
    ) -> dict:
        """Save an enhanced engineering review record."""
        self.init_db()
        session = self.SessionFactory()
        try:
            review = EngineeringReviewRecord(
                report_type=report_type,
                report_identifier=report_identifier,
                reviewer=reviewer,
                decision=decision,
                comment=comment,
                correction=correction,
                source_document=source_document,
                source_version=source_version,
                original_result_summary=original_result_summary,
                final_reviewed_result=final_reviewed_result,
                created_at=datetime.now(timezone.utc),
            )
            session.add(review)
            session.commit()
            return {
                "review_id": review.id,
                "report_type": review.report_type,
                "report_identifier": review.report_identifier,
                "reviewer": review.reviewer,
                "decision": review.decision,
                "comment": review.comment,
                "correction": review.correction,
                "source_document": review.source_document,
                "source_version": review.source_version,
                "created_at": review.created_at.isoformat() if review.created_at else None,
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save engineering review: {e}")
            raise
        finally:
            session.close()

    def get_engineering_reviews(self, limit: int = 100) -> List[dict]:
        """Fetch enhanced engineering reviews."""
        self.init_db()
        session = self.SessionFactory()
        try:
            results = session.query(EngineeringReviewRecord).order_by(EngineeringReviewRecord.id.desc()).limit(limit).all()
            return [
                {
                    "review_id": r.id,
                    "report_type": r.report_type,
                    "report_identifier": r.report_identifier,
                    "reviewer": r.reviewer,
                    "decision": r.decision,
                    "comment": r.comment,
                    "correction": r.correction,
                    "source_document": r.source_document,
                    "source_version": r.source_version,
                    "original_result_summary": r.original_result_summary,
                    "final_reviewed_result": r.final_reviewed_result,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in results
            ]
        finally:
            session.close()

    # ==========================================
    # Phase 8: Governance Audit Trail
    # ==========================================

    def save_governance_change(
        self,
        document_id: str,
        old_status: Optional[str],
        new_status: str,
        changed_by: str = "system",
        reason: Optional[str] = None,
    ) -> dict:
        """Record a document governance status change in the audit trail."""
        self.init_db()
        session = self.SessionFactory()
        try:
            record = GovernanceRecord(
                document_id=document_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                reason=reason,
                created_at=datetime.now(timezone.utc),
            )
            session.add(record)
            session.commit()
            return {
                "id": record.id,
                "document_id": record.document_id,
                "old_status": record.old_status,
                "new_status": record.new_status,
                "changed_by": record.changed_by,
                "reason": record.reason,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save governance change: {e}")
            raise
        finally:
            session.close()

    def get_governance_audit(self, document_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Fetch governance audit trail."""
        self.init_db()
        session = self.SessionFactory()
        try:
            query = session.query(GovernanceRecord).order_by(GovernanceRecord.id.desc())
            if document_id:
                query = query.filter(GovernanceRecord.document_id == document_id)
            results = query.limit(limit).all()
            return [
                {
                    "id": r.id,
                    "document_id": r.document_id,
                    "old_status": r.old_status,
                    "new_status": r.new_status,
                    "changed_by": r.changed_by,
                    "reason": r.reason,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in results
            ]
        finally:
            session.close()
