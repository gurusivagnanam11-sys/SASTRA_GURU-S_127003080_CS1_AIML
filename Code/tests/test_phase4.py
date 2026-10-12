"""Comprehensive test suite for Phase 4: Advanced RAG + Engineering Evaluation.

Validates:
1. Dataset Integrity (25 Grounded Queries + 10 Adversarial Unsupported Queries)
2. Retrieval Metrics (Precision@K, Recall@K, HitRate@K, MRR, nDCG@K)
3. Answer & Claim Grounding Metrics (Citation precision/coverage, NLI-style claim classification)
4. Query Intent Router (Classification, Version detection, Adversarial interception)
5. Architecture-Aware Hybrid Retriever (Multi-signal scoring, entity overlap, section weighting)
6. Pipeline Integration & Adversarial Clean Abstention
7. Phase 4 Benchmark Runner & Results Cache Integrity
8. Phase 4 FastAPI Evaluation Endpoints (/evaluation/*)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from evaluation.answer_metrics import (
    evaluate_abstention,
    evaluate_abstention_batch,
    evaluate_answer_entities,
    evaluate_answer_grounding,
    evaluate_citation_correctness,
    evaluate_citations,
    evaluate_groundedness,
    extract_architectural_entities,
    extract_content_words,
)
from evaluation.benchmark import (
    BenchmarkRunner,
    get_or_run_benchmark,
    load_benchmark_results,
)
from evaluation.dataset import (
    ADVERSARIAL_UNSUPPORTED_QUERIES,
    BENCHMARK_DATASET,
    BenchmarkQuery,
    get_benchmark_dataset,
    get_unsupported_dataset,
)
from evaluation.retrieval_metrics import (
    evaluate_retrieval_batch,
    hit_rate_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from rag.hybrid_retriever import BaselineRetriever, HybridRetriever, get_hybrid_retriever
from rag.langchain_rag import LangChainRAGChain
from rag.llm_provider import MockLLMProvider
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk, RAGResponse
from rag.pipeline import RAGPipeline, get_pipeline
from rag.query_router import QueryRouter, QueryType, RoutingDecision, get_query_router


@pytest.fixture
def client():
    """TestClient fixture for FastAPI."""
    return TestClient(app)


@pytest.fixture
def pipeline():
    """RAG pipeline fixture."""
    pipe = get_pipeline()
    pipe.llm_provider = MockLLMProvider()
    return pipe


@pytest.fixture
def router():
    """QueryRouter fixture."""
    return get_query_router()


@pytest.fixture
def hybrid_retriever(pipeline):
    """HybridRetriever fixture."""
    return HybridRetriever(
        embedder=pipeline.embedder,
        faiss_store=pipeline.faiss_store,
        metadata_store=pipeline.metadata_store,
    )


# ============================================================================
# 1. Dataset Integrity Tests
# ============================================================================


def test_benchmark_dataset_count_and_types():
    """Ensure benchmark dataset contains exactly 25 grounded architectural queries."""
    queries = get_benchmark_dataset()
    assert len(queries) == 25
    ids = [q.query_id for q in queries]
    assert len(set(ids)) == 25, "All query IDs must be unique"

    for q in queries:
        assert q.query_id.startswith("eval_")
        assert len(q.query.strip()) > 5
        assert q.category in {
            "ARCHITECTURE_QUERY",
            "REVISION_QUERY",
            "IMPACT_QUERY",
            "DOCUMENT_QA",
        }
        assert len(q.expected_chunks) >= 1
        assert len(q.expected_entities) >= 1
        assert len(q.expected_answer.strip()) > 0


def test_adversarial_dataset_count_and_types():
    """Ensure adversarial dataset contains exactly 10 unsupported automotive queries."""
    adv_queries = get_unsupported_dataset()
    assert len(adv_queries) == 10
    ids = [q.query_id for q in adv_queries]
    assert len(set(ids)) == 10, "All adversarial query IDs must be unique"

    for q in adv_queries:
        assert q.query_id.startswith("eval_unsupported_")
        assert len(q.query.strip()) > 5
        assert q.category == "UNSUPPORTED_QUERY"
        assert len(q.unsupported_topic.strip()) > 0


def test_ground_truth_chunks_exist_in_metadata(pipeline):
    """Verify that expected chunks in the dataset exist in the metadata store."""
    all_chunk_ids = {entry.get("chunk_id") for entry in pipeline.metadata_store.entries}
    assert len(all_chunk_ids) > 0, "Metadata store must not be empty"

    dataset = get_benchmark_dataset()
    found_any = False
    for q in dataset:
        for expected in q.expected_chunks:
            if expected in all_chunk_ids:
                found_any = True
                break
    assert found_any, "At least some expected ground-truth chunks must match stored chunks"


# ============================================================================
# 2. Retrieval Metrics Unit Tests
# ============================================================================


def test_precision_at_k():
    """Validate Precision@K calculation across various hit patterns."""
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    expected = {"c1", "c3"}

    # At K=1: c1 is in expected -> 1/1 = 1.0
    assert precision_at_k(retrieved, expected, k=1) == 1.0
    # At K=2: c1 hit, c2 miss -> 1/2 = 0.5
    assert precision_at_k(retrieved, expected, k=2) == 0.5
    # At K=3: c1 hit, c2 miss, c3 hit -> 2/3 ≈ 0.6667
    assert pytest.approx(precision_at_k(retrieved, expected, k=3), 0.001) == 0.6667
    # At K=5: 2 hits out of 5 -> 2/5 = 0.4
    assert precision_at_k(retrieved, expected, k=5) == 0.4

    # Empty retrieved or expected
    assert precision_at_k([], expected, k=5) == 0.0
    assert precision_at_k(retrieved, set(), k=5) == 0.0


def test_recall_at_k():
    """Validate Recall@K calculation."""
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    expected = {"c1", "c3", "c9"}  # 3 expected total

    # At K=1: 1 hit out of 3 -> 1/3 ≈ 0.3333
    assert pytest.approx(recall_at_k(retrieved, expected, k=1), 0.001) == 0.3333
    # At K=3: 2 hits out of 3 -> 2/3 ≈ 0.6667
    assert pytest.approx(recall_at_k(retrieved, expected, k=3), 0.001) == 0.6667
    # Empty expected returns 1.0 (nothing missed)
    assert recall_at_k(retrieved, set(), k=5) == 1.0


def test_hit_rate_at_k():
    """Validate binary HitRate@K calculation."""
    retrieved = ["c1", "c2", "c3", "c4", "c5"]
    expected = {"c3"}

    assert hit_rate_at_k(retrieved, expected, k=1) == 0.0
    assert hit_rate_at_k(retrieved, expected, k=2) == 0.0
    assert hit_rate_at_k(retrieved, expected, k=3) == 1.0
    assert hit_rate_at_k(retrieved, expected, k=5) == 1.0


def test_mean_reciprocal_rank():
    """Validate MRR for first rank, subsequent rank, and complete miss."""
    retrieved = ["c1", "c2", "c3", "c4", "c5"]

    # First rank match -> 1/1 = 1.0
    assert mean_reciprocal_rank(retrieved, {"c1"}) == 1.0
    # Second rank match -> 1/2 = 0.5
    assert mean_reciprocal_rank(retrieved, {"c2"}) == 0.5
    # Third rank match -> 1/3 ≈ 0.3333
    assert pytest.approx(mean_reciprocal_rank(retrieved, {"c3"}), 0.001) == 0.3333
    # Miss -> 0.0
    assert mean_reciprocal_rank(retrieved, {"c99"}) == 0.0


def test_ndcg_at_k():
    """Validate Normalized Discounted Cumulative Gain at K."""
    retrieved_ideal = ["c1", "c2", "c3", "c4", "c5"]
    expected = {"c1", "c2"}

    # Ideal ranking: items at rank 1 and 2 -> nDCG = 1.0
    assert ndcg_at_k(retrieved_ideal, expected, k=5) == 1.0

    # Displaced ranking: items at rank 4 and 5
    retrieved_suboptimal = ["c9", "c8", "c7", "c1", "c2"]
    sub_score = ndcg_at_k(retrieved_suboptimal, expected, k=5)
    assert 0.0 < sub_score < 1.0

    # Complete miss -> 0.0
    assert ndcg_at_k(["x", "y", "z"], expected, k=5) == 0.0


def test_evaluate_retrieval_batch():
    """Validate batch macro-average retrieval calculation."""
    queries = [
        BenchmarkQuery(
            id="Q1",
            question="What is X?",
            query_type="ARCHITECTURE_QUERY",
            expected_answer="Ans 1",
            expected_chunks=["c1"],
        ),
        BenchmarkQuery(
            id="Q2",
            question="What is Y?",
            query_type="ARCHITECTURE_QUERY",
            expected_answer="Ans 2",
            expected_chunks=["c2"],
        ),
    ]

    def mock_retriever(q_text, v=None):
        if "X" in q_text:
            return ["c1", "c2", "c3"]
        return ["c9", "c2", "c3"]

    batch_res = evaluate_retrieval_batch(mock_retriever, queries)
    macro = batch_res["macro_averages"]
    # Q1 MRR=1.0, Q2 MRR=0.5 -> average = 0.75
    assert macro["mrr"] == 0.75
    # Q1 HitRate@1=1.0, Q2 HitRate@1=0.0 -> average = 0.5
    assert macro["hit_rate_at_1"] == 0.5


# ============================================================================
# 3. Answer & Claim Grounding Metrics Unit Tests
# ============================================================================


def test_citation_metrics():
    """Validate citation precision and coverage calculation."""
    chunks = [
        ContextChunk(
            chunk_id="chunk_1",
            document_id="doc1",
            project_id="p1",
            version="1.0",
            page_number=1,
            section="1.0",
            section_title="Intro",
            chunk_type="general",
            entity_hint="",
            text="VehicleControl manages speed.",
            score=0.9,
        )
    ]
    claims = [
        Claim(text="VehicleControl handles speed.", citation_ids=["chunk_1"]),
        Claim(text="SafetyManager monitors faults.", citation_ids=[]),
    ]
    citations = [
        Citation(chunk_id="chunk_1", document="doc1", version="1.0", page=1, section="1.0", valid=True)
    ]

    res = evaluate_citation_correctness(citations=citations, retrieved_chunks=chunks, claims=claims)
    assert res["citation_precision"] == 1.0  # 1 cited chunk, exists in context
    assert res["citation_coverage"] == 0.5   # 1 out of 2 claims has citations
    assert res["valid_citations"] == 1


def test_grounding_evaluation():
    """Validate claim-level classification into SUPPORTED, PARTIALLY_SUPPORTED, and UNSUPPORTED."""
    context = [
        ContextChunk(
            chunk_id="chunk_1",
            document_id="doc1",
            project_id="p1",
            version="1.0",
            page_number=1,
            section="4.1",
            section_title="Architecture",
            chunk_type="architecture",
            entity_hint="VehicleControl",
            text="VehicleControl component interacts with BrakeController and SafetyManager through CAN.",
            score=0.95,
        )
    ]

    # Exactly supported claim
    supp_claim = Claim(
        text="VehicleControl component interacts with BrakeController and SafetyManager.",
        citation_ids=["chunk_1"],
    )
    # Unsupported claim
    unsupp_claim = Claim(
        text="The quantum laser propulsion subsystem operates at cryogenic temperatures.",
        citation_ids=[],
    )

    res = evaluate_groundedness(
        answer="VehicleControl component interacts with BrakeController and SafetyManager.",
        claims=[supp_claim, unsupp_claim],
        retrieved_chunks=context,
    )
    assert res["total_claims"] == 2
    assert res["supported"] == 1
    assert res["unsupported"] == 1
    assert 0.0 < res["grounding_score"] < 1.0
    statuses = [b["status"] for b in res["classification_breakdown"]]
    assert "SUPPORTED" in statuses
    assert "UNSUPPORTED" in statuses


def test_extract_architectural_entities():
    """Validate extraction of AUTOSAR architectural entities from natural language."""
    text = "VehicleControl receives VehicleSpeed over VehicleDataInterface via SpeedIn port."
    entities = extract_architectural_entities(text)
    assert "VehicleControl" in entities
    assert "VehicleSpeed" in entities
    assert "VehicleDataInterface" in entities
    assert "SpeedIn" in entities


def test_abstention_evaluation():
    """Validate detection of clean abstention vs hallucination on adversarial prompts."""
    # Correct abstention on unsupported query
    res_clean = evaluate_abstention(
        answer="The High-Level Design specification does not specify CAN transceiver pinout details.",
        is_unsupported=True,
    )
    assert res_clean["abstained"] is True
    assert res_clean["correct"] is True

    # Hallucination on unsupported query
    res_halluc = evaluate_abstention(
        answer="SafetyManager flash memory starts at address 0x08000000 and is mapped to bank 1.",
        is_unsupported=True,
    )
    assert res_halluc["abstained"] is False
    assert res_halluc["correct"] is False


def test_answer_entities_evaluation():
    """Validate entity recall, precision, and F1 scoring in answers."""
    ans = "VehicleControl connects to SafetyManager via VehicleDataInterface."
    res = evaluate_answer_entities(ans, ["VehicleControl", "SafetyManager", "EngineController"])
    assert res["expected_count"] == 3
    assert res["found_count"] == 2
    assert "EngineController" in res["missing_entities"]
    assert pytest.approx(res["recall"], 0.01) == 0.67


# ============================================================================
# 4. Query Intent Router Tests
# ============================================================================


def test_query_router_intent_classification(router):
    """Validate intent routing across all 5 query types."""
    # Architecture Query
    d_arch = router.route("What ports and interfaces belong to VehicleControl?")
    assert d_arch.intent == QueryType.ARCHITECTURE_QUERY
    assert "VehicleControl" in d_arch.entity_hints

    # Revision Query
    d_rev = router.route("What changed between version 1.0 and version 2.0?")
    assert d_rev.intent == QueryType.REVISION_QUERY

    # Impact Query
    d_imp = router.route("What is the impact of changing VehicleSpeed data type?")
    assert d_imp.intent == QueryType.IMPACT_QUERY
    assert "VehicleSpeed" in d_imp.entity_hints

    # General Document QA
    d_doc = router.route("Explain the overview and scope of the AUTOSAR HLD document.")
    assert d_doc.intent == QueryType.DOCUMENT_QA

    # Adversarial / Unsupported Query
    d_unsupp = router.route("What is the physical pinout of the ECU connector?")
    assert d_unsupp.intent == QueryType.UNSUPPORTED_QUERY
    assert d_unsupp.is_supported is False


def test_query_router_version_detection(router):
    """Validate extraction of target HLD version."""
    d_v1 = router.route("What components are defined in version 1.0?")
    assert d_v1.detected_version == "1.0"

    d_v2 = router.route("Show me the SafetyManager interface in v2.0")
    assert d_v2.detected_version == "2.0"

    d_none = router.route("What components exist in the system?")
    assert d_none.detected_version is None


# ============================================================================
# 5. Hybrid Retriever Tests
# ============================================================================


def test_baseline_retriever_returns_results(pipeline):
    """Validate BaselineRetriever retrieves dense FAISS candidates."""
    baseline = BaselineRetriever(
        embedder=pipeline.embedder,
        faiss_store=pipeline.faiss_store,
        metadata_store=pipeline.metadata_store,
    )
    chunks = baseline.retrieve_chunks("VehicleControl", top_k=3)
    assert len(chunks) == 3
    for score, chunk in chunks:
        assert isinstance(score, float)
        assert "chunk_id" in chunk
        assert "text" in chunk


def test_hybrid_retriever_boosts_relevant_sections(hybrid_retriever):
    """Validate HybridRetriever retrieves candidates with multi-signal fusion."""
    chunks = hybrid_retriever.retrieve_chunks("What ports belong to VehicleControl?", top_k=5)
    assert len(chunks) >= 4

    # Check that retrieved items have score and chunk dict
    top_score, top_chunk = chunks[0]
    assert isinstance(top_score, float)
    assert "chunk_id" in top_chunk
    # Check that alias retrieve() works identically
    alias_chunks = hybrid_retriever.retrieve("What ports belong to VehicleControl?", top_k=5)
    assert len(alias_chunks) >= 4


def test_hybrid_retriever_version_filter(hybrid_retriever):
    """Validate version filtering in HybridRetriever."""
    v1_chunks = hybrid_retriever.retrieve_chunks("VehicleControl", version="1.0", top_k=5)
    for _, ch in v1_chunks:
        assert ch.get("version") == "1.0"

    v2_chunks = hybrid_retriever.retrieve_chunks("SafetyManager", version="2.0", top_k=5)
    for _, ch in v2_chunks:
        assert ch.get("version") == "2.0"


# ============================================================================
# 6. RAG Pipeline Integration & Adversarial Abstention Tests
# ============================================================================


def test_rag_pipeline_hybrid_mode(pipeline):
    """Validate RAGPipeline execution with retriever_mode='hybrid'."""
    response = pipeline.ask(
        question="What components are associated with VehicleControl?",
        retriever_mode="hybrid",
        top_k=5,
    )
    assert isinstance(response, RAGResponse)
    assert len(response.answer) > 20
    assert response.retrieved_chunks_count > 0


def test_rag_pipeline_adversarial_abstention(pipeline):
    """Validate that unsupported hardware/adversarial queries trigger clean abstention."""
    response = pipeline.ask(
        question="What is the CAN transceiver physical pinout for VehicleControl?",
        top_k=5,
    )
    assert isinstance(response, RAGResponse)
    assert response.confidence == ConfidenceLevel.LOW
    assert response.review_required is True
    assert "out of scope" in response.answer.lower() or "do not specify" in response.answer.lower() or "not documented" in response.answer.lower()


def test_langchain_rag_hybrid_mode(pipeline):
    """Validate LangChain orchestration with hybrid retrieval mode."""
    chain = LangChainRAGChain(pipeline=pipeline, llm_provider=MockLLMProvider())
    response = chain.query(
        question="What interface carries VehicleSpeed?",
        retriever_mode="hybrid",
        top_k=3,
    )
    assert isinstance(response, RAGResponse)
    assert len(response.answer) > 10


# ============================================================================
# 7. Phase 4 Benchmark Results & Cache Integrity Tests
# ============================================================================


def test_benchmark_results_file_exists():
    """Ensure benchmark_results.json exists on disk and loads valid JSON."""
    results = load_benchmark_results()
    assert results is not None, "benchmark_results.json must exist"
    assert "timestamp" in results
    assert "key_metrics_summary" in results
    assert "retrieval_evaluation" in results
    assert "generation_evaluation" in results
    assert "abstention_evaluation" in results
    assert "latency_benchmarks" in results


def test_benchmark_metrics_validity():
    """Verify that benchmark results contain realistic, non-fabricated metrics."""
    results = load_benchmark_results()
    km = results["key_metrics_summary"]

    # Retrieval MRR & improvement
    assert 0.0 < km["baseline_mrr"] <= 1.0
    assert 0.0 < km["hybrid_mrr"] <= 1.0
    assert km["mrr_improvement"] >= 0.0, "Hybrid retriever must improve or match baseline MRR"

    # Hit Rate @ 1
    assert 0.0 < km["baseline_hit_rate_at_1"] <= 1.0
    assert 0.0 < km["hybrid_hit_rate_at_1"] <= 1.0
    assert km["hybrid_hit_rate_at_1"] >= km["baseline_hit_rate_at_1"]

    # Grounding & Citations
    assert km["citation_precision"] == 1.0
    assert km["citation_coverage"] == 1.0
    assert km["supported_claims_ratio"] > 0.5

    # Abstention on adversarial queries
    assert km["adversarial_abstention_accuracy"] == 1.0
    assert km["hallucination_rate"] == 0.0


def test_benchmark_latencies_measured():
    """Verify that all pipeline component micro-latencies are measured and positive."""
    results = load_benchmark_results()
    lats = results["latency_benchmarks"]

    assert lats["embedding_latency_ms"] > 0.0
    assert lats["baseline_retrieval_latency_ms"] > 0.0
    assert lats["hybrid_retrieval_latency_ms"] > 0.0
    assert lats["full_mock_pipeline_latency_ms"] > 0.0


# ============================================================================
# 8. FastAPI Phase 4 Evaluation Endpoints Tests
# ============================================================================


def test_api_evaluation_summary(client):
    """GET /evaluation/summary returns executive KPI metrics."""
    res = client.get("/evaluation/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "key_metrics" in data
    assert "dataset_stats" in data
    assert "latencies" in data
    assert data["key_metrics"]["citation_precision"] == 1.0


def test_api_evaluation_retrieval(client):
    """GET /evaluation/retrieval returns Baseline vs Hybrid metrics."""
    res = client.get("/evaluation/retrieval")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "baseline" in data
    assert "hybrid" in data
    assert "deltas" in data
    assert "category_breakdown" in data
    assert len(data["itemized"]) == 25


def test_api_evaluation_grounding(client):
    """GET /evaluation/grounding returns claim support breakdown."""
    res = client.get("/evaluation/grounding")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "macro_averages" in data
    assert "supported_claims_ratio" in data["macro_averages"]
    assert len(data["itemized"]) == 25


def test_api_evaluation_citations(client):
    """GET /evaluation/citations returns citation precision and coverage."""
    res = client.get("/evaluation/citations")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["citation_precision"] == 1.0
    assert data["citation_coverage"] == 1.0
    assert len(data["itemized"]) == 25


def test_api_evaluation_abstention(client):
    """GET /evaluation/abstention returns 10 adversarial query evaluations."""
    res = client.get("/evaluation/abstention")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["abstention_accuracy"] == 1.0
    assert data["hallucination_rate"] == 0.0
    assert data["total_evaluated"] == 10
    assert len(data["adversarial_results"]) == 10


def test_api_evaluation_benchmark(client):
    """GET /evaluation/benchmark returns complete raw benchmark dictionary."""
    res = client.get("/evaluation/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert "timestamp" in data
    assert "retrieval_evaluation" in data
    assert "generation_evaluation" in data
    assert "abstention_evaluation" in data


def test_api_evaluation_providers(client):
    """GET /evaluation/providers returns technical profile of supported LLMs."""
    res = client.get("/evaluation/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    providers = data["providers"]
    assert "ollama" in providers
    assert "gemini" in providers
    assert "mock" in providers
    assert "PRIMARY private/local LLM" in providers["ollama"]["role"]
    assert "OPTIONAL" in providers["gemini"]["role"]
    assert "DETERMINISTIC" in providers["mock"]["role"]
