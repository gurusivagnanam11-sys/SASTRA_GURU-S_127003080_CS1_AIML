"""Context builder for assembling retrieved HLD evidence into LLM-ready context.

Preserves full provenance (chunk_id, document, version, page, section, type, entity_hint)
without stripping any architectural metadata.
"""

import logging
from typing import Any, Dict, List, Tuple, Union
from chunking.models import HLDChunk
from rag.models import ContextChunk

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Assembles and formats retrieved HLD chunks for LLM prompt context."""

    def build_context(
        self, retrieved_items: List[Tuple[float, Union[Dict[str, Any], HLDChunk]]]
    ) -> List[ContextChunk]:
        """Convert raw retrieval tuples into structured ContextChunk objects.

        Args:
            retrieved_items: List of (similarity_score, chunk_metadata_dict_or_HLDChunk)

        Returns:
            List of ContextChunk objects with full provenance.
        """
        context_chunks: List[ContextChunk] = []

        for score, item in retrieved_items:
            if isinstance(item, dict):
                chunk = ContextChunk(
                    chunk_id=item.get("chunk_id", ""),
                    document_id=item.get("document_id", ""),
                    project_id=item.get("project_id", ""),
                    version=str(item.get("version", "")),
                    page_number=int(item.get("page_number", 1)),
                    section=str(item.get("section", "")),
                    section_title=str(item.get("section_title", "")),
                    chunk_type=str(item.get("chunk_type", "general")),
                    entity_hint=str(item.get("entity_hint", "")),
                    text=item.get("text", ""),
                    score=float(score),
                )
            elif isinstance(item, HLDChunk):
                chunk = ContextChunk(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    project_id=getattr(item, "project_id", ""),
                    version=str(item.version),
                    page_number=int(item.page_number),
                    section=str(item.section),
                    section_title=str(item.section_title),
                    chunk_type=str(item.chunk_type),
                    entity_hint=str(item.entity_hint),
                    text=item.text,
                    score=float(score),
                )
            else:
                logger.warning(f"Unrecognized retrieved item type: {type(item)}")
                continue

            context_chunks.append(chunk)

        return context_chunks

    def format_context_for_prompt(self, chunks: List[ContextChunk]) -> str:
        """Format a list of ContextChunks into an LLM prompt context block.

        Preserves clear provenance headers per chunk so the LLM can reference
        exact chunk_ids, pages, and sections when citing evidence.

        Args:
            chunks: List of ContextChunk objects.

        Returns:
            Formatted string of evidence chunks.
        """
        if not chunks:
            return "No relevant HLD evidence retrieved."

        blocks = []
        for i, chunk in enumerate(chunks, 1):
            block = (
                f"--- EVIDENCE ITEM {i} ---\n"
                f"Chunk ID: {chunk.chunk_id}\n"
                f"Document: {chunk.document_id}\n"
                f"Version: {chunk.version}\n"
                f"Page: {chunk.page_number}\n"
                f"Section: {chunk.section} ({chunk.section_title})\n"
                f"Chunk Type: {chunk.chunk_type}\n"
                f"Entity Hint: {chunk.entity_hint or 'None'}\n"
                f"Relevance Score: {chunk.score:.4f}\n"
                f"Content:\n{chunk.text.strip()}\n"
            )
            blocks.append(block)

        return "\n".join(blocks)
