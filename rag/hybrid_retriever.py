"""Architecture-Aware Hybrid Retrieval Engine for AUTOSAR HLD specifications.

Combines:
1. FAISS dense semantic similarity (BGE embeddings)
2. Architecture Entity matching (SWCs, Ports, Signals, Interfaces)
3. Section relevance scoring (Ports -> Sec 6, Signals -> Sec 5, Deps -> Sec 7)
4. Version-aware filtering and intent alignment (v1.0 vs v2.0)
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import INDEX_DIR, TOP_K
from embeddings.embedder import HLDEmbedder
from rag.query_router import QueryRouter, QueryType, RoutingDecision, get_query_router
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class BaselineRetriever:
    """Standard dense semantic retriever using BGE embeddings and FAISS search alone."""

    def __init__(
        self,
        embedder: Optional[HLDEmbedder] = None,
        faiss_store: Optional[FAISSStore] = None,
        metadata_store: Optional[MetadataStore] = None,
    ):
        self._embedder = embedder
        self._faiss_store = faiss_store
        self._metadata_store = metadata_store

    @property
    def embedder(self) -> HLDEmbedder:
        if self._embedder is None:
            self._embedder = HLDEmbedder()
        return self._embedder

    @property
    def faiss_store(self) -> FAISSStore:
        if self._faiss_store is None:
            index_path = INDEX_DIR / "hld_index.faiss"
            self._faiss_store = FAISSStore(dimension=self.embedder.dimension)
            self._faiss_store.load(index_path)
        return self._faiss_store

    @property
    def metadata_store(self) -> MetadataStore:
        if self._metadata_store is None:
            metadata_path = INDEX_DIR / "hld_metadata.json"
            self._metadata_store = MetadataStore()
            self._metadata_store.load(metadata_path)
        return self._metadata_store

    def retrieve_chunks(
        self,
        query: str,
        version: Optional[str] = None,
        top_k: int = 5,
        project: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Retrieve top-K chunks using standard semantic vector search."""
        query_vector = self.embedder.embed_query(query)
        total_vectors = self.faiss_store.count
        search_k = min(total_vectors, max(top_k * 5, 25))

        distances, indices = self.faiss_store.search(query_vector, top_k=search_k)

        results: List[Tuple[float, Dict[str, Any]]] = []
        for dist, idx in zip(distances, indices):
            if idx == -1:
                continue
            meta = self.metadata_store.get_by_faiss_id(idx)
            if not meta:
                continue

            # Project filter
            if project and meta.get("project_id"):
                if meta.get("project_id") != project:
                    continue

            # Chunk type filter
            if chunk_type and meta.get("chunk_type"):
                if meta.get("chunk_type") != chunk_type:
                    continue

            # Version filter if explicitly requested
            if version and meta.get("version"):
                if str(meta.get("version")).strip() != str(version).strip():
                    continue

            results.append((float(dist), meta))
            if len(results) == top_k:
                break

        return results

    # Convenience alias for pipeline compatibility
    retrieve = retrieve_chunks

    def retrieve_chunk_ids(
        self,
        query: str,
        version: Optional[str] = None,
        top_k: int = 5,
    ) -> List[str]:
        """Retrieve list of chunk IDs for standard evaluation."""
        chunks = self.retrieve_chunks(query=query, version=version, top_k=top_k)
        return [c[1]["chunk_id"] for c in chunks]



class HybridRetriever:
    """Architecture-aware hybrid retriever combining semantic similarity, entity matching, and section scoring."""

    def __init__(
        self,
        embedder: Optional[HLDEmbedder] = None,
        faiss_store: Optional[FAISSStore] = None,
        metadata_store: Optional[MetadataStore] = None,
        router: Optional[QueryRouter] = None,
        weight_semantic: float = 0.50,
        weight_entity: float = 0.30,
        weight_section: float = 0.20,
    ):
        self._embedder = embedder
        self._faiss_store = faiss_store
        self._metadata_store = metadata_store
        self._router = router or get_query_router()
        self.w_semantic = weight_semantic
        self.w_entity = weight_entity
        self.w_section = weight_section

    @property
    def embedder(self) -> HLDEmbedder:
        if self._embedder is None:
            self._embedder = HLDEmbedder()
        return self._embedder

    @property
    def faiss_store(self) -> FAISSStore:
        if self._faiss_store is None:
            index_path = INDEX_DIR / "hld_index.faiss"
            self._faiss_store = FAISSStore(dimension=self.embedder.dimension)
            self._faiss_store.load(index_path)
        return self._faiss_store

    @property
    def metadata_store(self) -> MetadataStore:
        if self._metadata_store is None:
            metadata_path = INDEX_DIR / "hld_metadata.json"
            self._metadata_store = MetadataStore()
            self._metadata_store.load(metadata_path)
        return self._metadata_store

    def retrieve_chunks(
        self,
        query: str,
        version: Optional[str] = None,
        top_k: int = 5,
        project: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Perform architecture-aware hybrid retrieval with multi-signal scoring."""
        # 1. Route query and detect architectural intent
        routing: RoutingDecision = self._router.route(query)
        effective_version = version or routing.detected_version

        # 2. Dense semantic candidate pool
        query_vector = self.embedder.embed_query(query)
        total_vectors = self.faiss_store.count
        candidate_pool_size = min(total_vectors, max(top_k * 6, 30))

        distances, indices = self.faiss_store.search(query_vector, top_k=candidate_pool_size)

        scored_candidates: List[Dict[str, Any]] = []

        for dist, idx in zip(distances, indices):
            if idx == -1:
                continue
            meta = self.metadata_store.get_by_faiss_id(idx)
            if not meta:
                continue

            # Project filter
            if project and meta.get("project_id"):
                if meta.get("project_id") != project:
                    continue

            # Chunk type filter
            if chunk_type and meta.get("chunk_type"):
                if meta.get("chunk_type") != chunk_type:
                    continue

            chunk_ver = str(meta.get("version", "")).strip()

            # Strict version filtering when effective_version is specified
            if effective_version and chunk_ver:
                if chunk_ver != effective_version.strip():
                    continue

            # Compute semantic score (cosine similarity bounded to [0, 1])
            semantic_score = max(0.0, min(1.0, float(dist)))


            # Compute entity match score
            entity_score = 0.0
            chunk_text = meta.get("text", "")
            chunk_hint = meta.get("entity_hint", "")
            chunk_title = meta.get("section_title", "")

            if routing.target_entities:
                matched_count = 0
                for ent in routing.target_entities:
                    if ent.lower() == chunk_hint.lower() or ent.lower() in chunk_title.lower():
                        matched_count += 2  # Strong signal: chunk is specifically about this entity
                    elif ent.lower() in chunk_text.lower():
                        matched_count += 1

                max_possible = len(routing.target_entities) * 2
                entity_score = min(1.0, matched_count / float(max_possible)) if max_possible > 0 else 0.0

            # Compute section relevance score
            section_score = 0.0
            chunk_sec = meta.get("section", "")
            chunk_type = meta.get("chunk_type", "")

            if routing.target_section_hint:
                if chunk_sec.startswith(routing.target_section_hint) or routing.target_section_hint in chunk_sec:
                    section_score = 1.0
                elif routing.target_chunk_type_hint and routing.target_chunk_type_hint == chunk_type:
                    section_score = 0.8
                elif routing.target_section_hint == "6." and "port" in chunk_title.lower():
                    section_score = 1.0
                elif routing.target_section_hint == "5." and "signal" in chunk_title.lower():
                    section_score = 1.0

            # Composite hybrid score
            final_score = (
                self.w_semantic * semantic_score
                + self.w_entity * entity_score
                + self.w_section * section_score
            )

            candidate_entry = dict(meta)
            candidate_entry["_scores"] = {
                "final_score": round(final_score, 4),
                "semantic_score": round(semantic_score, 4),
                "entity_score": round(entity_score, 4),
                "section_score": round(section_score, 4),
                "routing_type": routing.query_type.value,
            }
            scored_candidates.append(candidate_entry)

        # Sort by final hybrid score descending
        scored_candidates.sort(key=lambda x: x["_scores"]["final_score"], reverse=True)

        results = [(c["_scores"]["final_score"], c) for c in scored_candidates[:top_k]]
        return results

    # Convenience alias for pipeline compatibility
    retrieve = retrieve_chunks

    def retrieve_chunk_ids(
        self,
        query: str,
        version: Optional[str] = None,
        top_k: int = 5,
    ) -> List[str]:
        """Retrieve list of chunk IDs using hybrid architecture-aware ranking."""
        chunks = self.retrieve_chunks(query=query, version=version, top_k=top_k)
        return [c[1]["chunk_id"] for c in chunks]


# Singleton instances
_baseline_retriever_instance: Optional[BaselineRetriever] = None
_hybrid_retriever_instance: Optional[HybridRetriever] = None


def get_baseline_retriever() -> BaselineRetriever:
    """Get singleton BaselineRetriever."""
    global _baseline_retriever_instance
    if _baseline_retriever_instance is None:
        _baseline_retriever_instance = BaselineRetriever()
    return _baseline_retriever_instance


def get_hybrid_retriever() -> HybridRetriever:
    """Get singleton HybridRetriever."""
    global _hybrid_retriever_instance
    if _hybrid_retriever_instance is None:
        _hybrid_retriever_instance = HybridRetriever()
    return _hybrid_retriever_instance
