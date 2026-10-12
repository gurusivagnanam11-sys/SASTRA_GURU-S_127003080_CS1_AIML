"""LangChain RAG Orchestration for AUTOSAR HLD Assistant.

Provides:
- Document conversion maintaining full AUTOSAR provenance (chunk_id, document, version, page, section).
- HLDRetriever wrapping Phase 1 FAISS + BGE retrieval with metadata filtering.
- ChatPromptTemplate and PromptTemplate integration.
- Runnable RAG chain producing validated RAGResponse objects.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from rag.citation_validator import CitationValidator
from rag.context_builder import ContextBuilder
from rag.grounding_checker import GroundingChecker
from rag.llm_provider import LLMProvider, get_llm_provider
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk, RAGResponse
from rag.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


def to_langchain_documents(
    items: List[Union[ContextChunk, Tuple[float, Dict[str, Any]], Dict[str, Any], Document]]
) -> List[Document]:
    """Convert raw retrieved chunks or ContextChunk items to LangChain Documents.

    Guarantees preservation of full architectural provenance in metadata:
    chunk_id, document, version, page, section, section_title, chunk_type, score.
    """
    documents: List[Document] = []
    for item in items:
        if isinstance(item, Document):
            # Ensure metadata consistency
            meta = dict(item.metadata)
            if "chunk_id" not in meta and "id" in meta:
                meta["chunk_id"] = meta["id"]
            if "page" not in meta and "page_number" in meta:
                meta["page"] = meta["page_number"]
            if "document" not in meta and "document_id" in meta:
                meta["document"] = meta["document_id"]
            documents.append(Document(page_content=item.page_content, metadata=meta))
        elif isinstance(item, ContextChunk):
            meta = {
                "chunk_id": item.chunk_id,
                "document": item.document_id,
                "document_id": item.document_id,
                "project_id": item.project_id,
                "version": item.version,
                "page": item.page_number,
                "page_number": item.page_number,
                "section": item.section,
                "section_title": item.section_title,
                "chunk_type": item.chunk_type,
                "entity_hint": item.entity_hint,
                "score": float(item.score),
            }
            documents.append(Document(page_content=item.text, metadata=meta))
        elif isinstance(item, tuple) and len(item) == 2:
            score, chunk_dict = item
            meta = {
                "chunk_id": chunk_dict.get("chunk_id", ""),
                "document": chunk_dict.get("document_id", ""),
                "document_id": chunk_dict.get("document_id", ""),
                "project_id": chunk_dict.get("project_id", ""),
                "version": chunk_dict.get("version", ""),
                "page": chunk_dict.get("page_number", 1),
                "page_number": chunk_dict.get("page_number", 1),
                "section": chunk_dict.get("section", ""),
                "section_title": chunk_dict.get("section_title", ""),
                "chunk_type": chunk_dict.get("chunk_type", "general"),
                "entity_hint": chunk_dict.get("entity_hint", ""),
                "score": float(score),
            }
            documents.append(Document(page_content=chunk_dict.get("text", ""), metadata=meta))
        elif isinstance(item, dict):
            meta = {
                "chunk_id": item.get("chunk_id", ""),
                "document": item.get("document_id", item.get("document", "")),
                "document_id": item.get("document_id", item.get("document", "")),
                "project_id": item.get("project_id", ""),
                "version": item.get("version", ""),
                "page": item.get("page_number", item.get("page", 1)),
                "page_number": item.get("page_number", item.get("page", 1)),
                "section": item.get("section", ""),
                "section_title": item.get("section_title", ""),
                "chunk_type": item.get("chunk_type", "general"),
                "entity_hint": item.get("entity_hint", ""),
                "score": float(item.get("score", 0.0)),
            }
            documents.append(Document(page_content=item.get("text", item.get("content", "")), metadata=meta))
    return documents


def format_documents_to_context(documents: List[Document]) -> str:
    """Format LangChain documents into the standardized HLD prompt context block."""
    if not documents:
        return "No relevant HLD evidence retrieved."

    blocks = []
    for i, doc in enumerate(documents, start=1):
        meta = doc.metadata
        chunk_id = meta.get("chunk_id", f"chunk_{i}")
        doc_id = meta.get("document", meta.get("document_id", "unknown"))
        version = meta.get("version", "unknown")
        page = meta.get("page", meta.get("page_number", 1))
        section = meta.get("section", "")
        section_title = meta.get("section_title", "")
        score = meta.get("score", 0.0)

        header = (
            f"--- EVIDENCE ITEM {i} ---\n"
            f"Chunk ID: {chunk_id}\n"
            f"Document: {doc_id} (Version: {version})\n"
            f"Page: {page} | Section: {section} ({section_title})\n"
            f"Relevance Score: {score:.4f}\n"
            f"Content:\n{doc.page_content.strip()}"
        )
        blocks.append(header)

    return "\n\n".join(blocks)


class HLDRetriever(BaseRetriever):
    """LangChain-compatible Retriever wrapping the Phase 1 FAISS + BGE vector store."""

    pipeline: Any = None
    top_k: int = 5
    project: Optional[str] = None
    version: Optional[str] = None
    chunk_type: Optional[str] = None
    retriever_mode: str = "hybrid"

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve relevant HLD chunks and convert them to LangChain Documents."""
        from rag.pipeline import get_pipeline

        pipe = self.pipeline or get_pipeline()
        if getattr(self, "retriever_mode", "hybrid") == "hybrid" and hasattr(pipe, "hybrid_retriever"):
            retrieved_raw = pipe.hybrid_retriever.retrieve_chunks(
                query=query,
                version=self.version,
                top_k=self.top_k,
                project=self.project,
                chunk_type=self.chunk_type,
            )
        else:
            query_vector = pipe.embedder.embed_query(query)
            retrieved_raw = pipe._retrieve_filtered_chunks(
                query_vector=query_vector,
                top_k=self.top_k,
                project=self.project,
                version=self.version,
                chunk_type=self.chunk_type,
            )
        return to_langchain_documents(retrieved_raw)


# LangChain Prompt Templates for AUTOSAR HLD
HLD_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=SYSTEM_PROMPT),
        (
            "human",
            "USER QUESTION:\n{question}\n\nRETRIEVED HLD EVIDENCE CONTEXT:\n{context}\n\n"
            "Please analyze the evidence above and provide your response as a valid JSON object matching the requested schema. "
            "Remember to cite only chunks present in the evidence above.",
        ),
    ]
)


class LangChainRAGChain:
    """End-to-end LangChain RAG pipeline preserving AUTOSAR verification and citation rigor."""

    def __init__(
        self,
        pipeline: Optional[Any] = None,
        retriever: Optional[HLDRetriever] = None,
        llm_provider: Optional[LLMProvider] = None,
        prompt_template: Optional[ChatPromptTemplate] = None,
        citation_validator: Optional[CitationValidator] = None,
        grounding_checker: Optional[GroundingChecker] = None,
    ):
        from rag.pipeline import get_pipeline

        self.pipeline = pipeline or get_pipeline()
        self.retriever = retriever or HLDRetriever(pipeline=self.pipeline, top_k=self.pipeline.top_k)
        self.llm_provider = llm_provider or self.pipeline.llm_provider
        self.prompt_template = prompt_template or HLD_PROMPT_TEMPLATE
        self.citation_validator = citation_validator or self.pipeline.citation_validator
        self.grounding_checker = grounding_checker or self.pipeline.grounding_checker

    def query(
        self,
        question: str,
        project: Optional[str] = None,
        version: Optional[str] = None,
        chunk_type: Optional[str] = None,
        top_k: Optional[int] = None,
        retriever_mode: str = "hybrid",
    ) -> RAGResponse:
        """Execute the LangChain-orchestrated RAG query."""
        if not question or not question.strip():
            return RAGResponse(
                question=question or "",
                answer="No question was provided. Please supply an architectural question.",
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=["Empty query submitted."],
                review_required=True,
                retrieved_chunks_count=0,
            )

        # Configure retriever dynamically for this query
        k = top_k or self.retriever.top_k
        query_retriever = HLDRetriever(
            pipeline=self.pipeline,
            top_k=k,
            project=project or self.retriever.project,
            version=version or self.retriever.version,
            chunk_type=chunk_type or self.retriever.chunk_type,
            retriever_mode=retriever_mode,
        )

        # 1. Retrieve LangChain Documents
        docs: List[Document] = query_retriever.invoke(question)

        filter_applied = {}
        if project:
            filter_applied["project_id"] = project
        if version:
            filter_applied["version"] = version
        if chunk_type:
            filter_applied["chunk_type"] = chunk_type

        if not docs:
            return RAGResponse(
                question=question,
                answer="Insufficient evidence in approved documents to support this query.",
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=["No relevant HLD chunks found matching query and filter criteria."],
                review_required=True,
                retrieved_chunks_count=0,
                metadata_filter_applied=filter_applied or None,
            )

        # 2. Format Context
        context_str = format_documents_to_context(docs)

        # 3. Format Prompt
        prompt_value = self.prompt_template.format_messages(
            question=question,
            context=context_str,
        )
        system_text = prompt_value[0].content
        user_text = prompt_value[1].content

        # 4. Generate with LLM Provider
        try:
            raw_output = self.llm_provider.generate(
                system_prompt=system_text,
                user_prompt=user_text,
            )
        except Exception as e:
            logger.error(f"LangChain generation failed: {e}")
            return RAGResponse(
                question=question,
                answer="Generation error: LLM provider unavailable or call failed.",
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=[f"LLM generation exception: {str(e)}"],
                review_required=True,
                retrieved_chunks_count=len(docs),
                metadata_filter_applied=filter_applied or None,
            )

        # 5. Parse and Validate
        parsed_data = self.pipeline._parse_llm_json(raw_output)

        # Convert LangChain docs to ContextChunks for existing validators
        context_chunks: List[ContextChunk] = [
            ContextChunk(
                chunk_id=doc.metadata.get("chunk_id", ""),
                document_id=doc.metadata.get("document", ""),
                project_id=doc.metadata.get("project_id", ""),
                version=doc.metadata.get("version", ""),
                page_number=doc.metadata.get("page", 1),
                section=doc.metadata.get("section", ""),
                section_title=doc.metadata.get("section_title", ""),
                chunk_type=doc.metadata.get("chunk_type", "general"),
                entity_hint=doc.metadata.get("entity_hint", ""),
                text=doc.page_content,
                score=doc.metadata.get("score", 0.0),
            )
            for doc in docs
        ]

        raw_citations = [
            Citation(**c) if isinstance(c, dict) else c
            for c in parsed_data.get("citations", [])
        ]
        validated_citations, all_citations_valid, citation_issues = (
            self.citation_validator.validate_citations(
                citations=raw_citations,
                retrieved_chunks=context_chunks,
                metadata_store=self.pipeline._metadata_store,
            )
        )

        raw_claims = [
            Claim(**c) if isinstance(c, dict) else c
            for c in parsed_data.get("claims", [])
        ]
        checked_claims, grounding_score, grounding_issues = (
            self.grounding_checker.check_grounding(
                answer=parsed_data.get("answer", ""),
                claims=raw_claims,
                retrieved_chunks=context_chunks,
            )
        )

        max_score = max((c.score for c in context_chunks), default=0.0)
        limitations = parsed_data.get("limitations", [])
        if not isinstance(limitations, list):
            limitations = [str(limitations)]

        for issue in citation_issues:
            limitations.append(f"Citation Warning: {issue}")
        for issue in grounding_issues:
            limitations.append(f"Grounding Warning: {issue}")

        confidence, review_required = self.pipeline._evaluate_confidence_and_review(
            answer=parsed_data.get("answer", ""),
            max_similarity_score=max_score,
            all_citations_valid=all_citations_valid,
            grounding_score=grounding_score,
            llm_confidence=parsed_data.get("confidence", "low"),
            llm_review_required=bool(parsed_data.get("review_required", False)),
        )

        return RAGResponse(
            question=question,
            answer=parsed_data.get("answer", ""),
            claims=checked_claims,
            citations=validated_citations,
            confidence=confidence,
            limitations=limitations,
            review_required=review_required,
            grounding_score=grounding_score,
            retrieved_chunks_count=len(docs),
            metadata_filter_applied=filter_applied or None,
        )


def create_hld_rag_chain(
    pipeline: Optional[Any] = None,
    llm_provider: Optional[LLMProvider] = None,
    top_k: int = 5,
) -> LangChainRAGChain:
    """Convenience factory function to create a LangChainRAGChain."""
    from rag.pipeline import get_pipeline

    pipe = pipeline or get_pipeline()
    retriever = HLDRetriever(pipeline=pipe, top_k=top_k)
    return LangChainRAGChain(
        retriever=retriever,
        llm_provider=llm_provider or pipe.llm_provider,
    )
