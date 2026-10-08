"""Deterministic citation validator for AUTOSAR HLD RAG outputs.

Verifies that every citation references an actual retrieved chunk with consistent
document, version, page, and section metadata.
"""

import logging
from typing import Dict, List, Optional, Tuple
from rag.models import Citation, ContextChunk
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class CitationValidator:
    """Validates LLM-generated citations deterministically against retrieved evidence."""

    def validate_citations(
        self,
        citations: List[Citation],
        retrieved_chunks: List[ContextChunk],
        metadata_store: Optional[MetadataStore] = None,
    ) -> Tuple[List[Citation], bool, List[str]]:
        """Validate a list of citations against retrieved context chunks and metadata.

        Args:
            citations: Citations produced by LLM generation.
            retrieved_chunks: ContextChunk objects provided in the prompt.
            metadata_store: Optional MetadataStore for global ID verification.

        Returns:
            Tuple of:
            - validated_citations: Updated Citation objects with `valid` and `validation_notes`
            - is_valid: True if all citations are valid, False otherwise
            - issues: List of human-readable validation issue strings
        """
        if not citations:
            return [], True, []

        chunk_lookup: Dict[str, ContextChunk] = {c.chunk_id: c for c in retrieved_chunks}
        validated: List[Citation] = []
        issues: List[str] = []
        all_valid = True

        for cit in citations:
            chunk_id = cit.chunk_id.strip()
            
            # 1. Verify chunk_id exists in retrieved context
            if chunk_id not in chunk_lookup:
                # Check if it at least exists in the global metadata store
                global_match = metadata_store.get_by_chunk_id(chunk_id) if metadata_store else None
                if global_match:
                    issue = f"Citation references chunk '{chunk_id}' that exists in the database but was NOT retrieved in the context."
                else:
                    issue = f"Citation references unknown or fabricated chunk_id '{chunk_id}'."
                
                cit.valid = False
                cit.validation_notes = issue
                issues.append(issue)
                all_valid = False
                validated.append(cit)
                continue

            # 2. Verify metadata matches stored chunk
            actual = chunk_lookup[chunk_id]
            mismatches = []

            # Document check (allow case-insensitive or extension differences)
            cit_doc = cit.document.lower().replace(".pdf", "")
            act_doc = actual.document_id.lower().replace(".pdf", "")
            if cit_doc != act_doc and cit_doc not in act_doc and act_doc not in cit_doc:
                mismatches.append(f"document mismatch (cited: '{cit.document}', actual: '{actual.document_id}')")

            # Version check
            if cit.version.strip() != actual.version.strip():
                mismatches.append(f"version mismatch (cited: '{cit.version}', actual: '{actual.version}')")

            # Page check
            if int(cit.page) != int(actual.page_number):
                mismatches.append(f"page mismatch (cited: {cit.page}, actual: {actual.page_number})")

            # Section check (allow section number or prefix match)
            cit_sec = cit.section.strip().rstrip(".")
            act_sec = actual.section.strip().rstrip(".")
            if cit_sec and act_sec and (cit_sec != act_sec and not act_sec.startswith(cit_sec) and not cit_sec.startswith(act_sec)):
                mismatches.append(f"section mismatch (cited: '{cit.section}', actual: '{actual.section}')")

            if mismatches:
                issue = f"Metadata discrepancy for chunk '{chunk_id}': " + "; ".join(mismatches)
                cit.valid = False
                cit.validation_notes = issue
                issues.append(issue)
                all_valid = False
            else:
                cit.valid = True
                cit.validation_notes = "Verified against retrieved HLD evidence."

            validated.append(cit)

        return validated, all_valid, issues
