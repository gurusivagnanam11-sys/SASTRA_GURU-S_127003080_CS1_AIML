"""Structured data models for RAG question answering in AUTOSAR HLD Assistant.

Preserves full provenance, claims-to-citation mapping, grounding verification,
and human review gating.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Application-level confidence rating based on evidence quality."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContextChunk(BaseModel):
    """Structured representation of an HLD evidence chunk for context construction."""
    chunk_id: str
    document_id: str
    project_id: str = ""
    version: str
    page_number: int
    section: str
    section_title: str
    chunk_type: str
    entity_hint: str = ""
    text: str
    score: float = 0.0


class Citation(BaseModel):
    """Structured provenance citation linked to an HLD source chunk."""
    document: str
    version: str
    page: int
    section: str
    chunk_id: str
    valid: Optional[bool] = None
    validation_notes: Optional[str] = None


class Claim(BaseModel):
    """Individual factual statement extracted from the answer with citation links."""
    text: str
    citation_ids: List[str] = Field(default_factory=list)
    grounded: Optional[bool] = None


class RAGResponse(BaseModel):
    """Structured, grounded response for an AUTOSAR HLD query."""
    question: str
    answer: str
    claims: List[Claim] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    limitations: List[str] = Field(default_factory=list)
    review_required: bool = False
    grounding_score: Optional[float] = None
    retrieved_chunks_count: int = 0
    metadata_filter_applied: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    """Incoming query parameters for RAG retrieval and answering."""
    question: str
    project: Optional[str] = None
    document_version: Optional[str] = None
    chunk_type: Optional[str] = None
    top_k: int = 5
