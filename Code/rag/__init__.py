"""RAG (Retrieval-Augmented Generation) package for AUTOSAR HLD Assistant.

Phase 2 implementation providing grounded question answering with citations,
confidence evaluation, and human review gating.
"""

from rag.export import export_response_to_json, export_response_to_markdown
from rag.langchain_rag import (
    HLD_PROMPT_TEMPLATE,
    HLDRetriever,
    LangChainRAGChain,
    create_hld_rag_chain,
    format_documents_to_context,
    to_langchain_documents,
)
from rag.models import (
    Citation,
    Claim,
    ConfidenceLevel,
    ContextChunk,
    QueryRequest,
    RAGResponse,
)
from rag.pipeline import RAGPipeline, ask, get_pipeline

__all__ = [
    "Citation",
    "Claim",
    "ConfidenceLevel",
    "ContextChunk",
    "QueryRequest",
    "RAGResponse",
    "RAGPipeline",
    "ask",
    "get_pipeline",
    "to_langchain_documents",
    "format_documents_to_context",
    "HLDRetriever",
    "HLD_PROMPT_TEMPLATE",
    "LangChainRAGChain",
    "create_hld_rag_chain",
    "export_response_to_json",
    "export_response_to_markdown",
]
