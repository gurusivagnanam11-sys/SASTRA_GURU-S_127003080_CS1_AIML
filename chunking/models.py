"""Data models for architecture-aware chunks.

Each chunk preserves full provenance: document, version, page, section,
and entity context, enabling traceable retrieval.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HLDChunk:
    """A single architecture-aware chunk from an HLD document.

    Attributes:
        chunk_id: Unique identifier (e.g., 'hld_v1_p04_c02')
        document_id: Parent document identifier
        project_id: Project this document belongs to
        version: Document version string
        page_number: Source page number (1-indexed)
        section: Section number (e.g., '3.1') or 'unknown'
        section_title: Section heading text or 'unknown'
        chunk_type: Architecture type classification
            (general/component/interface/port/signal/dependency/flow/table/architecture/unknown)
        entity_hint: Primary AUTOSAR entity name referenced, or empty string
        text: The actual chunk text content
        extraction_method: Method used to extract content ('text' or 'ocr')
        content_type: Content type ('text', 'table', 'ocr', 'heading', 'metadata')
    """
    chunk_id: str
    document_id: str
    project_id: str
    version: str
    page_number: int
    section: str
    section_title: str
    chunk_type: str
    entity_hint: str
    text: str
    extraction_method: str = "text"
    content_type: str = "text"
