"""Data models for document ingestion.

These models represent the structured output of PDF parsing,
preserving page boundaries and document metadata for traceability.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PageData:
    """Represents a single parsed page from an HLD document."""
    page_number: int
    raw_text: str
    headings: List[str] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)  # textual table representations
    section: Optional[str] = None
    section_title: Optional[str] = None
    extraction_method: str = "text"


@dataclass
class DocumentMetadata:
    """Metadata for an ingested HLD document."""
    document_id: str
    filename: str
    project_id: str
    document_type: str
    version: str
    source: str
    ingestion_timestamp: str
    page_count: int


@dataclass
class DocumentData:
    """Complete parsed document with page-level structure."""
    document_id: str
    filename: str
    project_id: str
    version: str
    pages: List[PageData] = field(default_factory=list)
    metadata: Optional[DocumentMetadata] = None
