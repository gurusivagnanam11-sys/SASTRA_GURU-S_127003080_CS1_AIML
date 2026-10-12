"""Comprehensive unit and integration tests for Phase 2 Grounded RAG Q&A.

Validates:
A. Query embedding integration
B. Retrieval integration
C. Context construction & formatting
D. Metadata preservation
E. Structured response parsing (clean JSON, markdown JSON, malformed)
F. Citation validation (valid citations)
G. Missing citation handling (claims without citation IDs)
H. Invalid citation handling (fabricated chunk_id, metadata mismatch)
I. Insufficient evidence handling (zero matches, unknown query)
J. Metadata filtering (version and project isolation)
K. End-to-end RAG pipeline across canonical queries using MockLLMProvider
L. Provider abstraction and error handling
"""

import json
from pathlib import Path
import pytest
import numpy as np

from app.config import INDEX_DIR
from embeddings.embedder import HLDEmbedder
from rag.citation_validator import CitationValidator
from rag.context_builder import ContextBuilder
from rag.grounding_checker import GroundingChecker
from rag.llm_provider import MockLLMProvider, OpenAILLMProvider, get_llm_provider
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk, RAGResponse
from rag.pipeline import RAGPipeline
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore


@pytest.fixture
def test_context_chunks():
    """Sample ContextChunk objects with authentic HLD metadata."""
    return [
        ContextChunk(
            chunk_id="autosar_hld__v2.0_p06_c24",
            document_id="autosar_hld_v2.0",
            project_id="demo_project",
            version="2.0",
            page_number=6,
            section="4.1",
            section_title="VehicleDataInterface",
            chunk_type="interface",
            entity_hint="VehicleDataInterface",
            text="4.1 VehicleDataInterface\nType: Sender-Receiver Interface\nVehicleDataInterface is a Sender-Receiver interface that carries vehicle sensor data between SensorManager and consuming components. Signals include VehicleSpeed (float64), EngineRPM (uint16), and EngineTemperature (float32).",
            score=0.85,
        ),
        ContextChunk(
            chunk_id="autosar_hld__v2.0_p04_c17",
            document_id="autosar_hld_v2.0",
            project_id="demo_project",
            version="2.0",
            page_number=4,
            section="3.1",
            section_title="VehicleControl",
            chunk_type="component",
            entity_hint="VehicleControl",
            text="3.1 VehicleControl\nVehicleControl is the central application software component responsible for processing sensor data and generating vehicle control commands. Input Ports: VehicleSpeedIn, EngineRPMIn, SafetyStatusIn. Output Ports: ControlCommandOut, VehicleStateOut.",
            score=0.82,
        ),
    ]


@pytest.fixture
def loaded_stores():
    """Load existing validated FAISS store and Metadata store from disk."""
    faiss_path = INDEX_DIR / "hld_index.faiss"
    metadata_path = INDEX_DIR / "hld_metadata.json"

    if not faiss_path.exists() or not metadata_path.exists():
        pytest.skip("Index files missing. Run 'python scripts/build_index.py' first.")

    meta_store = MetadataStore()
    meta_store.load(metadata_path)

    # Use dimension from metadata or embedder
    embedder = HLDEmbedder()
    faiss_store = FAISSStore(dimension=embedder.dimension)
    faiss_store.load(faiss_path)

    return embedder, faiss_store, meta_store


# =========================================================================
# A. Query Embedding Integration
# =========================================================================

def test_query_embedding_integration(loaded_stores):
    embedder, _, _ = loaded_stores
    query = "What interface carries VehicleSpeed?"
    vec = embedder.embed_query(query)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (embedder.dimension,)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-3)


# =========================================================================
# B. Retrieval Integration
# =========================================================================

def test_retrieval_integration(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    query = "VehicleDataInterface"
    vec = embedder.embed_query(query)

    scores, indices = faiss_store.search(vec, top_k=5)
    assert len(scores) == 5
    assert len(indices) == 5
    assert indices[0] != -1

    top_chunk = meta_store.get_by_faiss_id(indices[0])
    assert "chunk_id" in top_chunk
    assert "text" in top_chunk
    assert top_chunk["page_number"] >= 1


# =========================================================================
# C. Context Construction & Formatting
# =========================================================================

def test_context_construction(test_context_chunks):
    builder = ContextBuilder()
    formatted = builder.format_context_for_prompt(test_context_chunks)

    assert "--- EVIDENCE ITEM 1 ---" in formatted
    assert "Chunk ID: autosar_hld__v2.0_p06_c24" in formatted
    assert "Document: autosar_hld_v2.0" in formatted
    assert "Version: 2.0" in formatted
    assert "Page: 6" in formatted
    assert "Section: 4.1" in formatted
    assert "VehicleDataInterface" in formatted
    assert "Relevance Score: 0.8500" in formatted


def test_empty_context_construction():
    builder = ContextBuilder()
    formatted = builder.format_context_for_prompt([])
    assert formatted == "No relevant HLD evidence retrieved."


# =========================================================================
# D. Metadata Preservation
# =========================================================================

def test_metadata_preservation():
    builder = ContextBuilder()
    raw_item = {
        "chunk_id": "autosar_hld__v1.0_p06_c23",
        "document_id": "autosar_hld_v1.0",
        "project_id": "demo_project",
        "version": "1.0",
        "page_number": 6,
        "section": "4.1",
        "section_title": "VehicleDataInterface",
        "chunk_type": "interface",
        "entity_hint": "VehicleDataInterface",
        "text": "Interface details...",
    }

    chunks = builder.build_context([(0.78, raw_item)])
    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == "autosar_hld__v1.0_p06_c23"
    assert c.document_id == "autosar_hld_v1.0"
    assert c.project_id == "demo_project"
    assert c.version == "1.0"
    assert c.page_number == 6
    assert c.section == "4.1"
    assert c.section_title == "VehicleDataInterface"
    assert c.chunk_type == "interface"
    assert c.entity_hint == "VehicleDataInterface"
    assert c.score == 0.78


# =========================================================================
# E. Structured Response Parsing
# =========================================================================

def test_parse_clean_json():
    pipeline = RAGPipeline(llm_provider=MockLLMProvider())
    raw = json.dumps({
        "answer": "Test answer",
        "claims": [{"text": "Claim 1", "citation_ids": ["c1"]}],
        "citations": [{"document": "doc1", "version": "1.0", "page": 1, "section": "1", "chunk_id": "c1"}],
        "confidence": "high",
        "limitations": [],
        "review_required": False
    })
    parsed = pipeline._parse_llm_json(raw)
    assert parsed["answer"] == "Test answer"
    assert len(parsed["claims"]) == 1


def test_parse_markdown_wrapped_json():
    pipeline = RAGPipeline(llm_provider=MockLLMProvider())
    raw = "```json\n" + json.dumps({
        "answer": "Wrapped answer",
        "claims": [],
        "citations": [],
        "confidence": "medium",
        "limitations": [],
        "review_required": False
    }) + "\n```"
    parsed = pipeline._parse_llm_json(raw)
    assert parsed["answer"] == "Wrapped answer"


def test_parse_malformed_json_fallback():
    pipeline = RAGPipeline(llm_provider=MockLLMProvider())
    raw = "This is not valid JSON at all."
    parsed = pipeline._parse_llm_json(raw)
    assert parsed["answer"] == raw
    assert parsed["confidence"] == "low"
    assert parsed["review_required"] is True
    assert "Malformed LLM response" in parsed["limitations"][0]


# =========================================================================
# F. Citation Validation (Valid Citations)
# =========================================================================

def test_citation_validation_valid(test_context_chunks):
    validator = CitationValidator()
    citations = [
        Citation(
            document="autosar_hld_v2.0",
            version="2.0",
            page=6,
            section="4.1",
            chunk_id="autosar_hld__v2.0_p06_c24",
        )
    ]
    validated, all_valid, issues = validator.validate_citations(citations, test_context_chunks)
    assert all_valid is True
    assert len(issues) == 0
    assert validated[0].valid is True
    assert "Verified against" in validated[0].validation_notes


# =========================================================================
# G. Missing Citation in Claim Handling
# =========================================================================

def test_missing_citation_in_claim(test_context_chunks):
    checker = GroundingChecker()
    claims = [
        Claim(text="VehicleControl regulates speed.", citation_ids=[]),
    ]
    checked, score, issues = checker.check_grounding("VehicleControl regulates speed.", claims, test_context_chunks)
    assert checked[0].grounded is False
    assert score == 0.0
    assert any("lacks citations" in issue for issue in issues)


# =========================================================================
# H. Invalid Citation Handling
# =========================================================================

def test_invalid_citation_nonexistent_chunk(test_context_chunks):
    validator = CitationValidator()
    citations = [
        Citation(
            document="autosar_hld_v2.0",
            version="2.0",
            page=12,
            section="9.9",
            chunk_id="fabricated_chunk_id_999",
        )
    ]
    validated, all_valid, issues = validator.validate_citations(citations, test_context_chunks)
    assert all_valid is False
    assert len(issues) == 1
    assert validated[0].valid is False
    assert "fabricated chunk_id" in issues[0] or "not in retrieved context" in issues[0]


def test_invalid_citation_metadata_discrepancy(test_context_chunks):
    validator = CitationValidator()
    # Chunk exists, but citation claims page 10 instead of 6
    citations = [
        Citation(
            document="autosar_hld_v2.0",
            version="2.0",
            page=10,  # Wrong page!
            section="4.1",
            chunk_id="autosar_hld__v2.0_p06_c24",
        )
    ]
    validated, all_valid, issues = validator.validate_citations(citations, test_context_chunks)
    assert all_valid is False
    assert validated[0].valid is False
    assert "page mismatch" in issues[0]


# =========================================================================
# I. Insufficient Evidence Handling
# =========================================================================

def test_insufficient_evidence_when_filtered_out(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )

    # Filter by non-existent version 99.0
    response = pipeline.ask(
        question="What components are associated with VehicleControl?",
        document_version="99.0",
    )

    assert "Insufficient evidence" in response.answer
    assert response.confidence == ConfidenceLevel.LOW
    assert response.review_required is True
    assert response.retrieved_chunks_count == 0


def test_empty_query_handling(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )

    response = pipeline.ask("   ")
    assert response.confidence == ConfidenceLevel.LOW
    assert response.review_required is True
    assert "Empty query" in response.limitations[0]


# =========================================================================
# J. Metadata Filtering (Version Isolation)
# =========================================================================

def test_metadata_filtering_version(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )

    resp_v1 = pipeline.ask("What interface carries VehicleSpeed?", document_version="1.0")
    for cit in resp_v1.citations:
        assert cit.version == "1.0"

    resp_v2 = pipeline.ask("What interface carries VehicleSpeed?", document_version="2.0")
    for cit in resp_v2.citations:
        assert cit.version == "2.0"


# =========================================================================
# K. End-to-End Canonical Evaluation Queries (Mocked LLM)
# =========================================================================

def test_canonical_query_1_components(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )
    res = pipeline.ask("What components are associated with VehicleControl?")
    assert "VehicleControl" in res.answer
    assert len(res.citations) > 0
    assert all(c.valid for c in res.citations)
    assert res.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


def test_canonical_query_2_interface(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )
    res = pipeline.ask("What interface carries VehicleSpeed?")
    assert "VehicleDataInterface" in res.answer
    assert len(res.citations) > 0
    assert any(c.page in (6, 7) for c in res.citations)
    assert all(c.valid for c in res.citations)
    assert res.confidence == ConfidenceLevel.HIGH
    assert res.review_required is False


def test_canonical_query_3_ports(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )
    res = pipeline.ask("What ports belong to VehicleControl?")
    assert "VehicleSpeedIn" in res.answer or "ControlCommandOut" in res.answer
    assert len(res.citations) > 0
    assert all(c.valid for c in res.citations)


def test_canonical_query_4_signals(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )
    res = pipeline.ask("What signals are consumed by VehicleControl?")
    assert "VehicleSpeed" in res.answer or "EngineRPM" in res.answer
    assert len(res.citations) > 0
    assert all(c.valid for c in res.citations)


def test_canonical_query_5_version_delta(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores
    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=MockLLMProvider(),
    )
    res = pipeline.ask("What changed between version 1.0 and version 2.0?")
    assert "SafetyManager" in res.answer or "five" in res.answer
    assert len(res.citations) > 0
    assert all(c.valid for c in res.citations)


# =========================================================================
# L. Provider Abstraction & Error Handling
# =========================================================================

def test_llm_provider_factory():
    p_mock = get_llm_provider("mock")
    assert isinstance(p_mock, MockLLMProvider)


def test_openai_provider_missing_key_raises():
    with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
        OpenAILLMProvider(api_key="")


def test_pipeline_llm_failure_handled(loaded_stores):
    embedder, faiss_store, meta_store = loaded_stores

    class BrokenLLM(MockLLMProvider):
        def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
            raise ConnectionError("Simulated LLM connection timeout.")

    pipeline = RAGPipeline(
        embedder=embedder,
        faiss_store=faiss_store,
        metadata_store=meta_store,
        llm_provider=BrokenLLM(),
    )

    res = pipeline.ask("What interface carries VehicleSpeed?")
    assert res.confidence == ConfidenceLevel.LOW
    assert res.review_required is True
    assert "Generation error" in res.answer
    assert any("Simulated LLM connection timeout" in lim for lim in res.limitations)
