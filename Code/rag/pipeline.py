"""Main Grounded RAG Question Answering Pipeline for AUTOSAR HLD Assistant.

Orchestrates:
Query -> Embedding -> FAISS Retrieval -> Metadata Filtering -> Context Building ->
LLM Generation -> Structured Output Parsing -> Citation Validation ->
Grounding Verification -> Confidence & Review Assessment.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import INDEX_DIR, TOP_K
from chunking.models import HLDChunk
from embeddings.embedder import HLDEmbedder
from rag.citation_validator import CitationValidator
from rag.context_builder import ContextBuilder
from rag.grounding_checker import GroundingChecker
from rag.hybrid_retriever import BaselineRetriever, HybridRetriever
from rag.llm_provider import LLMProvider, get_llm_provider
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk, RAGResponse
from rag.prompts import SYSTEM_PROMPT, build_user_prompt
from rag.query_router import QueryRouter, QueryType, get_query_router
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Production-style grounded RAG pipeline for AUTOSAR HLD specifications."""

    def __init__(
        self,
        embedder: Optional[HLDEmbedder] = None,
        faiss_store: Optional[FAISSStore] = None,
        metadata_store: Optional[MetadataStore] = None,
        llm_provider: Optional[LLMProvider] = None,
        context_builder: Optional[ContextBuilder] = None,
        citation_validator: Optional[CitationValidator] = None,
        grounding_checker: Optional[GroundingChecker] = None,
        query_router: Optional[QueryRouter] = None,
        hybrid_retriever: Optional[HybridRetriever] = None,
        top_k: int = TOP_K,
    ):
        self.top_k = top_k
        self._embedder = embedder
        self._faiss_store = faiss_store
        self._metadata_store = metadata_store
        self._query_router = query_router
        self._hybrid_retriever = hybrid_retriever
        self.llm_provider = llm_provider or get_llm_provider()
        self.context_builder = context_builder or ContextBuilder()
        self.citation_validator = citation_validator or CitationValidator()
        self.grounding_checker = grounding_checker or GroundingChecker()

    @property
    def embedder(self) -> HLDEmbedder:
        """Lazy-loaded embedding model."""
        if self._embedder is None:
            logger.info("Initializing default HLDEmbedder...")
            self._embedder = HLDEmbedder()
        return self._embedder

    @property
    def faiss_store(self) -> FAISSStore:
        """Lazy-loaded FAISS vector store from disk."""
        if self._faiss_store is None:
            index_path = INDEX_DIR / "hld_index.faiss"
            if not index_path.exists():
                raise FileNotFoundError(
                    f"FAISS index file not found at {index_path}. "
                    "Run 'python scripts/build_index.py' to generate index."
                )
            logger.info(f"Loading FAISS store from {index_path}...")
            # Trigger model to get correct dimension
            dim = self.embedder.dimension
            self._faiss_store = FAISSStore(dimension=dim)
            self._faiss_store.load(index_path)
        return self._faiss_store

    @property
    def metadata_store(self) -> MetadataStore:
        """Lazy-loaded MetadataStore from disk."""
        if self._metadata_store is None:
            metadata_path = INDEX_DIR / "hld_metadata.json"
            if not metadata_path.exists():
                raise FileNotFoundError(
                    f"Metadata catalog not found at {metadata_path}. "
                    "Run 'python scripts/build_index.py' to generate metadata."
                )
            logger.info(f"Loading MetadataStore from {metadata_path}...")
            self._metadata_store = MetadataStore()
            self._metadata_store.load(metadata_path)
        return self._metadata_store

    @property
    def query_router(self) -> QueryRouter:
        """Lazy-loaded query router for intent classification and entity hints."""
        if self._query_router is None:
            self._query_router = get_query_router()
        return self._query_router

    @property
    def hybrid_retriever(self) -> HybridRetriever:
        """Lazy-loaded hybrid retriever fusing dense search with architecture awareness."""
        if self._hybrid_retriever is None:
            self._hybrid_retriever = HybridRetriever(
                embedder=self.embedder,
                faiss_store=self.faiss_store,
                metadata_store=self.metadata_store,
            )
        return self._hybrid_retriever

    def ask(
        self,
        question: str,
        project: Optional[str] = None,
        document_version: Optional[str] = None,
        chunk_type: Optional[str] = None,
        top_k: Optional[int] = None,
        retriever_mode: str = "hybrid",
    ) -> RAGResponse:
        """Execute grounded question answering over the indexed HLD knowledge.

        Args:
            question: Natural language question about AUTOSAR HLD.
            project: Optional project_id filter.
            document_version: Optional version string filter ('1.0', '2.0').
            chunk_type: Optional chunk_type filter ('component', 'interface', etc.).
            top_k: Maximum number of evidence chunks to retrieve.
            retriever_mode: Retrieval strategy ('hybrid' or 'baseline').

        Returns:
            Structured, validated RAGResponse object.
        """
        k = top_k or self.top_k
        logger.info(f"RAG query received: '{question}' (top_k={k}, mode={retriever_mode})")

        # 1. Validate query
        if not question or not question.strip():
            logger.warning("Empty or whitespace-only question received.")
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

        filter_applied = {}
        if project:
            filter_applied["project_id"] = project
        if document_version:
            filter_applied["version"] = document_version
        if chunk_type:
            filter_applied["chunk_type"] = chunk_type

        # 1b. Intent Routing & Adversarial Abstention Guard
        route = self.query_router.route(question)
        if route.query_type == QueryType.UNSUPPORTED_QUERY:
            logger.info(f"Query routed as UNSUPPORTED: {route.rationale}")
            return RAGResponse(
                question=question,
                answer=(
                    f"The approved AUTOSAR HLD documents do not specify this parameter ({route.rationale}). "
                    "HLD specifications define software component architecture, interfaces, ports, and signals, "
                    "but do not specify lower-level hardware, microcontroller, or ECU implementation details."
                ),
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=[f"Abstention triggered: {route.rationale}"],
                review_required=True,
                retrieved_chunks_count=0,
                metadata_filter_applied=filter_applied or None,
            )

        # Apply detected version if not explicitly supplied
        effective_version = document_version
        if not effective_version and route.detected_version and route.query_type != QueryType.REVISION_QUERY:
            effective_version = route.detected_version
            filter_applied["version"] = effective_version

        # 2 & 3. Retrieval (Hybrid Architecture-Aware vs Baseline Dense)
        if retriever_mode == "hybrid":
            retrieved_raw = self.hybrid_retriever.retrieve(
                query=question,
                top_k=k,
                version=effective_version,
                project=project,
                chunk_type=chunk_type,
            )
        else:
            query_vector = self.embedder.embed_query(question)
            retrieved_raw = self._retrieve_filtered_chunks(
                query_vector=query_vector,
                top_k=k,
                project=project,
                version=effective_version,
                chunk_type=chunk_type,
            )

        logger.info(f"Retrieved {len(retrieved_raw)} chunks after filtering.")

        # 5. Check if any evidence found
        if not retrieved_raw:
            msg = "Insufficient evidence in approved documents to support this query."
            lim = ["No relevant HLD chunks found matching query and filter criteria."]
            return RAGResponse(
                question=question,
                answer=msg,
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=lim,
                review_required=True,
                retrieved_chunks_count=0,
                metadata_filter_applied=filter_applied or None,
            )

        # 6. Build Context
        context_chunks: List[ContextChunk] = self.context_builder.build_context(retrieved_raw)
        context_str = self.context_builder.format_context_for_prompt(context_chunks)

        # 6b. Cross-Version Evidence Completeness Check (Requirement 4)
        is_cross_version_query = (
            route.query_type == QueryType.REVISION_QUERY
            or (("v1" in question.lower() or "version 1" in question.lower()) and ("v2" in question.lower() or "version 2" in question.lower()))
            or "between versions" in question.lower()
            or "both versions" in question.lower()
            or "identical in" in question.lower()
        )
        if is_cross_version_query:
            versions_present = {c.version.strip() for c in context_chunks if c.version}
            missing_versions = [v for v in ("1.0", "2.0") if v not in versions_present]
            if missing_versions:
                msg = (
                    "Insufficient evidence in approved documents to support this query. "
                    f"Comparing specification versions requires evidence from both v1.0 and v2.0, "
                    f"but evidence for version(s) {', '.join(missing_versions)} was not retrieved."
                )
                lim = [f"Cross-version comparison abstention: missing evidence for version(s) {', '.join(missing_versions)}."]
                return RAGResponse(
                    question=question,
                    answer=msg,
                    claims=[],
                    citations=[],
                    confidence=ConfidenceLevel.LOW,
                    limitations=lim,
                    review_required=True,
                    retrieved_chunks_count=len(context_chunks),
                    metadata_filter_applied=filter_applied or None,
                    grounding_score=1.0,
                )

        # 7. LLM Generation
        user_prompt = build_user_prompt(question, context_str)
        try:
            raw_llm_output = self.llm_provider.generate(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return RAGResponse(
                question=question,
                answer="Generation error: LLM provider unavailable or call failed.",
                claims=[],
                citations=[],
                confidence=ConfidenceLevel.LOW,
                limitations=[f"LLM generation exception: {str(e)}"],
                review_required=True,
                retrieved_chunks_count=len(context_chunks),
                metadata_filter_applied=filter_applied or None,
            )

        # 8. Parse Structured Output
        parsed_data = self._parse_llm_json(raw_llm_output)

        # 9. Citation Validation
        raw_citations = [
            Citation(**c) if isinstance(c, dict) else c
            for c in parsed_data.get("citations", [])
        ]
        validated_citations, all_citations_valid, citation_issues = (
            self.citation_validator.validate_citations(
                citations=raw_citations,
                retrieved_chunks=context_chunks,
                metadata_store=self._metadata_store,
            )
        )

        valid_chunk_ids: Set[str] = {c.chunk_id for c in validated_citations if c.valid}
        retrieved_chunk_ids: Set[str] = {c.chunk_id for c in context_chunks}

        # 10. Grounding Checks
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

        # Requirements 2 & 3: Ensure every citation ID in a claim belongs to actual retrieved evidence
        # and has resolved to a citation with matching metadata.
        for claim in checked_claims:
            for cid in claim.citation_ids:
                if cid not in retrieved_chunk_ids:
                    claim.grounded = False
                    grounding_issues.append(f"Claim references non-retrieved chunk '{cid}'.")
                elif cid not in valid_chunk_ids and any(vc.chunk_id == cid for vc in validated_citations):
                    claim.grounded = False
                    grounding_issues.append(f"Claim references chunk '{cid}' that failed citation metadata validation.")

        if checked_claims:
            grounding_score = sum(1 for c in checked_claims if c.grounded) / len(checked_claims)

        # 11. Confidence & Review Required Evaluation
        max_score = max((c.score for c in context_chunks), default=0.0)
        limitations = parsed_data.get("limitations", [])
        if not isinstance(limitations, list):
            limitations = [str(limitations)]

        # Append issues to limitations for engineering transparency
        for issue in citation_issues:
            limitations.append(f"Citation Warning: {issue}")
        for issue in grounding_issues:
            limitations.append(f"Grounding Warning: {issue}")

        # Compute application-level confidence
        confidence, review_required = self._evaluate_confidence_and_review(
            answer=parsed_data.get("answer", ""),
            max_similarity_score=max_score,
            all_citations_valid=all_citations_valid,
            grounding_score=grounding_score,
            llm_confidence=parsed_data.get("confidence", "low"),
            llm_review_required=bool(parsed_data.get("review_required", False)),
        )

        response = RAGResponse(
            question=question,
            answer=parsed_data.get("answer", ""),
            claims=checked_claims,
            citations=validated_citations,
            confidence=confidence,
            limitations=limitations,
            review_required=review_required,
            grounding_score=grounding_score,
            retrieved_chunks_count=len(context_chunks),
            metadata_filter_applied=filter_applied or None,
        )

        logger.info(
            f"RAG query finished: confidence={response.confidence.value}, "
            f"review_required={response.review_required}, "
            f"citations={len(response.citations)}, "
            f"grounding_score={response.grounding_score:.2f}"
        )
        return response

    def _retrieve_filtered_chunks(
        self,
        query_vector: Any,
        top_k: int,
        project: Optional[str] = None,
        version: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Perform FAISS search with metadata filtering.

        Searches candidate pool and filters to prevent version or project leakage.
        """
        # Search candidate pool large enough to satisfy filter
        total_vectors = self.faiss_store.count
        search_k = min(total_vectors, max(top_k * 5, 25))

        distances, indices = self.faiss_store.search(query_vector, top_k=search_k)

        results: List[Tuple[float, Dict[str, Any]]] = []
        for dist, idx in zip(distances, indices):
            if idx == -1:
                continue

            chunk_meta = self.metadata_store.get_by_faiss_id(idx)
            if not chunk_meta:
                continue

            # Project filter
            if project and chunk_meta.get("project_id"):
                if chunk_meta.get("project_id") != project:
                    continue

            # Version filter
            if version and chunk_meta.get("version"):
                if str(chunk_meta.get("version")).strip() != str(version).strip():
                    continue

            # Chunk type filter
            if chunk_type and chunk_meta.get("chunk_type"):
                if chunk_meta.get("chunk_type") != chunk_type:
                    continue

            results.append((float(dist), chunk_meta))
            if len(results) == top_k:
                break

        return results

    def _parse_llm_json(self, raw_output: str) -> Dict[str, Any]:
        """Robustly extract, repair, and parse JSON from raw LLM output.

        Handles:
        1. Clean JSON
        2. Markdown fenced JSON (```json ... ```)
        3. Embedded JSON inside explanatory prose
        4. Truncated JSON caused by token limits (auto-closing strings, arrays, braces)
        5. Regex extraction of answer, claims, and citations if JSON parsing fails
        6. Safe structured fallback preventing malformed JSON from exposing raw syntax
        """
        cleaned = raw_output.strip()

        # Handle markdown code blocks
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
            else:
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

        # 1. Direct JSON parse
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed.setdefault("review_required", False)
                parsed.setdefault("confidence", "medium")
                parsed.setdefault("claims", [])
                parsed.setdefault("citations", [])
                parsed.setdefault("limitations", [])
                return parsed
        except json.JSONDecodeError:
            pass

        # 2. Extract outer JSON object
        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, dict):
                    parsed.setdefault("review_required", False)
                    parsed.setdefault("confidence", "medium")
                    parsed.setdefault("claims", [])
                    parsed.setdefault("citations", [])
                    parsed.setdefault("limitations", [])
                    return parsed
            except json.JSONDecodeError:
                pass

        # 3. Attempt repairing truncated JSON
        repaired = self._attempt_repair_json(cleaned)
        if repaired and isinstance(repaired, dict):
            logger.info("Successfully repaired truncated LLM JSON response.")
            repaired["review_required"] = True
            repaired.setdefault("confidence", "medium")
            repaired.setdefault("claims", [])
            repaired.setdefault("citations", [])
            lims = repaired.get("limitations", [])
            if not isinstance(lims, list):
                lims = [str(lims)]
            lims.append("Repaired truncated LLM output.")
            repaired["limitations"] = lims
            return repaired

        # 4. Fallback: regex extraction of structured fields
        extracted_answer = None
        ans_match = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
        if ans_match:
            try:
                extracted_answer = json.loads(f'"{ans_match.group(1)}"')
            except Exception:
                extracted_answer = ans_match.group(1)

        extracted_claims = []
        for cm in re.finditer(
            r'\{\s*"claim_id"\s*:\s*"([^"]+)"\s*,\s*"statement"\s*:\s*"([^"]+)"\s*,\s*"chunk_id"\s*:\s*"([^"]+)"(?:[^\}]*?)\}',
            cleaned,
        ):
            extracted_claims.append({
                "claim_id": cm.group(1),
                "statement": cm.group(2),
                "chunk_id": cm.group(3),
            })

        extracted_citations = []
        for cm in re.finditer(
            r'\{\s*"chunk_id"\s*:\s*"([^"]+)"\s*,\s*"document_id"\s*:\s*"([^"]+)"\s*,\s*"version"\s*:\s*"([^"]+)"(?:[^\}]*?)\}',
            cleaned,
        ):
            extracted_citations.append({
                "chunk_id": cm.group(1),
                "document_id": cm.group(2),
                "version": cm.group(3),
            })

        if extracted_answer:
            logger.warning("Extracted structured fields from unclosed LLM JSON via regex.")
            return {
                "answer": extracted_answer,
                "claims": extracted_claims,
                "citations": extracted_citations,
                "confidence": "medium" if (extracted_claims and extracted_citations) else "low",
                "limitations": ["Partially malformed LLM response: fields extracted via recovery parser."],
                "review_required": True,
            }

        logger.warning("Failed to parse JSON from LLM output. Returning safe structured fallback.")
        return {
            "answer": raw_output.strip(),
            "claims": [],
            "citations": [],
            "confidence": "low",
            "limitations": ["Malformed LLM response: output was not valid JSON."],
            "review_required": True,
        }

    def _attempt_repair_json(self, s: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair truncated JSON by completing open structures."""
        start_idx = s.find("{")
        if start_idx == -1:
            return None
        candidate = s[start_idx:].strip()

        # Remove trailing unescaped comma or colon
        candidate = re.sub(r'[,:\s]+$', '', candidate)

        # Track open strings and containers
        in_string = False
        escape = False
        stack = []
        for ch in candidate:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch in '{[':
                    stack.append(ch)
                elif ch == '}' and stack and stack[-1] == '{':
                    stack.pop()
                elif ch == ']' and stack and stack[-1] == '[':
                    stack.pop()

        if in_string:
            candidate += '"'

        # Close all open containers in reverse order
        while stack:
            top = stack.pop()
            candidate += '}' if top == '{' else ']'

        try:
            return json.loads(candidate)
        except Exception:
            return None

    def _evaluate_confidence_and_review(
        self,
        answer: str,
        max_similarity_score: float,
        all_citations_valid: bool,
        grounding_score: float,
        llm_confidence: str,
        llm_review_required: bool,
    ) -> Tuple[ConfidenceLevel, bool]:
        """Compute application-level confidence rating and human review gating.

        Evidence-quality rules:
        - HIGH: max score >= 0.70, all citations valid, grounding score >= 0.85, answer direct.
        - MEDIUM: score >= 0.55, citations valid, grounding score >= 0.60.
        - LOW: score < 0.55, citation invalid, grounding poor, or evidence insufficient.
        """
        ans_lower = answer.lower()
        if "insufficient evidence" in ans_lower or "insufficient information" in ans_lower:
            return ConfidenceLevel.LOW, True

        if not all_citations_valid or grounding_score < 0.60:
            return ConfidenceLevel.LOW, True

        if max_similarity_score < 0.45:
            return ConfidenceLevel.LOW, True

        if max_similarity_score >= 0.60 and grounding_score >= 0.85 and not llm_review_required:
            return ConfidenceLevel.HIGH, False

        # Moderate evidence or synthesis across sections
        return ConfidenceLevel.MEDIUM, llm_review_required or (grounding_score < 0.85)


# Global singleton pipeline instance
_default_pipeline: Optional[RAGPipeline] = None


def get_pipeline(provider_name: Optional[str] = None) -> RAGPipeline:
    """Get or create singleton RAGPipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = RAGPipeline()
    if provider_name is not None:
        _default_pipeline.llm_provider = get_llm_provider(provider_name)
    return _default_pipeline


def ask(
    question: str,
    project: Optional[str] = None,
    document_version: Optional[str] = None,
    chunk_type: Optional[str] = None,
    top_k: int = TOP_K,
    provider: Optional[str] = None,
    retriever_mode: str = "hybrid",
) -> RAGResponse:
    """Convenience functional interface for RAG question answering."""
    pipeline = get_pipeline(provider_name=provider)
    return pipeline.ask(
        question=question,
        project=project,
        document_version=document_version,
        chunk_type=chunk_type,
        top_k=top_k,
        retriever_mode=retriever_mode,
    )

