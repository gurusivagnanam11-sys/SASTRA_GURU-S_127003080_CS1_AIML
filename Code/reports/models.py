"""Engineering reports, governance models, and structured export for Phase 8.

Provides:
- DocumentGovernance model (status tracking for source documents)
- ComponentReport (structured component engineering report with provenance)
- EngineeringReview (enhanced review workflow: PENDING → APPROVED/CORRECTED/REJECTED)
- Report export helpers (JSON, Markdown, CSV)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================
# Source Governance
# ==============================

class DocumentStatus(str, Enum):
    APPROVED = "APPROVED"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"


class DocumentGovernance(BaseModel):
    """Source document governance metadata."""
    document_id: str
    document_name: str
    version: str
    status: DocumentStatus = DocumentStatus.DRAFT
    ingestion_timestamp: Optional[str] = None
    source_type: str = "HLD Specification"
    last_status_change: Optional[str] = None
    changed_by: Optional[str] = None


# ==============================
# Citation / Evidence
# ==============================

class EvidenceCitation(BaseModel):
    """Standard provenance citation for a single engineering fact."""
    document_name: str
    version: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None

    def format(self) -> str:
        parts = [self.document_name]
        if self.version:
            parts[0] += f" v{self.version}"
        if self.page is not None:
            parts.append(f"p.{self.page}")
        if self.section:
            parts.append(f"Section {self.section}")
        return f"[{', '.join(parts)}]"


# ==============================
# Fact Classification
# ==============================

class FactType(str, Enum):
    EXTRACTED = "extracted_fact"
    DERIVED = "derived_analysis"
    VALIDATION = "validation_finding"


class EngineeringFact(BaseModel):
    """A single engineering fact with classification and provenance."""
    fact_type: FactType
    description: str
    citation: Optional[EvidenceCitation] = None


# ==============================
# Component Report
# ==============================

class ComponentReport(BaseModel):
    """Structured engineering report for a single AUTOSAR SWC."""
    report_type: str = "component_report"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component_name: str
    description: str = "Not available in extracted source."
    source_document: str = "Not available in extracted source."
    source_version: str = "Not available in extracted source."
    source_status: str = "Not available in extracted source."
    interfaces: List[str] = Field(default_factory=list)
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    functional_flows: List[Dict[str, Any]] = Field(default_factory=list)
    related_components: List[str] = Field(default_factory=list)
    validation_findings: List[Dict[str, Any]] = Field(default_factory=list)
    revision_changes: List[Dict[str, Any]] = Field(default_factory=list)
    impact_information: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[EngineeringFact] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ==============================
# Validation Report
# ==============================

class ValidationReport(BaseModel):
    """Structured validation report reusing Phase 7 validator results."""
    report_type: str = "validation_report"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    document_id: str
    version: str
    status: str  # PASS, WARNING, ERROR
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ==============================
# Revision Report
# ==============================

class RevisionReport(BaseModel):
    """Structured revision comparison report reusing Phase 3 diff engine."""
    report_type: str = "revision_report"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_version: str
    target_version: str
    total_changes: int = 0
    added_entities: List[Dict[str, Any]] = Field(default_factory=list)
    removed_entities: List[Dict[str, Any]] = Field(default_factory=list)
    modified_entities: List[Dict[str, Any]] = Field(default_factory=list)
    renamed_entities: List[Dict[str, Any]] = Field(default_factory=list)
    summary_statistics: Dict[str, int] = Field(default_factory=dict)
    important_changes: List[str] = Field(default_factory=list)
    all_intentional_detected: bool = False
    limitations: List[str] = Field(default_factory=list)


# ==============================
# Impact Report
# ==============================

class ImpactReport(BaseModel):
    """Structured impact analysis report reusing Phase 3 impact engine."""
    report_type: str = "impact_report"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    base_version: str
    target_version: str
    total_impacts: int = 0
    changes_analyzed: int = 0
    impacts: List[Dict[str, Any]] = Field(default_factory=list)
    critical_risk_areas: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# ==============================
# Review Workflow
# ==============================

class ReviewDecision(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ENGINEER_APPROVED = "ENGINEER_APPROVED"
    ENGINEER_CORRECTED = "ENGINEER_CORRECTED"
    ENGINEER_REJECTED = "ENGINEER_REJECTED"


class EngineeringReview(BaseModel):
    """Enhanced engineering review record."""
    review_id: Optional[int] = None
    report_type: str = "general"
    report_identifier: str = ""
    reviewer: str = "Engineering Reviewer"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decision: ReviewDecision
    comment: Optional[str] = None
    correction: Optional[str] = None
    source_document: Optional[str] = None
    source_version: Optional[str] = None
    original_result_summary: Optional[str] = None
    final_reviewed_result: Optional[str] = None


# ==============================
# Report Catalog
# ==============================

class ReportCatalog(BaseModel):
    """Summary of available report types and capabilities."""
    available_reports: List[str] = [
        "component_report",
        "validation_report",
        "revision_report",
        "impact_report",
    ]
    export_formats: List[str] = ["json", "markdown", "csv"]
    governance_statuses: List[str] = ["APPROVED", "DRAFT", "ARCHIVED"]
    review_decisions: List[str] = [
        "PENDING_REVIEW",
        "ENGINEER_APPROVED",
        "ENGINEER_CORRECTED",
        "ENGINEER_REJECTED",
    ]
