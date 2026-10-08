"""Benchmark runner and evaluation harness for AUTOSAR HLD Intelligence Assistant.

Executes scientific, un-fabricated evaluations across:
1. Information Retrieval: Baseline (Dense FAISS) vs Architecture-Aware Hybrid Retriever
   - Metrics: Precision@1,3,5; Recall@1,3,5; HitRate@1,3,5; MRR; nDCG@5
2. Answer Quality & Groundedness:
   - Claim grounding breakdown (Supported, Partially Supported, Unsupported)
   - Architectural entity recall and precision
3. Citation Rigor:
   - Citation coverage, citation precision, metadata alignment
4. Adversarial & Hallucination Resistance (Abstention):
   - 10 adversarial queries where the system must abstain
5. Latency & Execution Timings:
   - Embedding, retrieval, reranking, generation, and total latency
6. Provider Performance:
   - Mock, Ollama (if available), Gemini (if configured)
"""

import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import INDEX_DIR
from evaluation.answer_metrics import (
    evaluate_abstention_batch,
    evaluate_answer_grounding,
    evaluate_citations,
    extract_architectural_entities,
)
from evaluation.dataset import (
    ADVERSARIAL_UNSUPPORTED_QUERIES,
    BENCHMARK_DATASET,
    EvaluationQuery,
    UnsupportedQuery,
)
from evaluation.retrieval_metrics import (
    compute_hit_rate_at_k,
    compute_ndcg_at_k,
    compute_precision_at_k,
    compute_recall_at_k,
    compute_reciprocal_rank,
    evaluate_retrieval_batch,
)
from rag.hybrid_retriever import BaselineRetriever, HybridRetriever
from rag.llm_provider import get_llm_provider
from rag.models import ConfidenceLevel, RAGResponse
from rag.pipeline import RAGPipeline, get_pipeline
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)

RESULTS_FILE = Path(__file__).resolve().parent / "benchmark_results.json"


class BenchmarkRunner:
    """End-to-end benchmark execution engine."""

    def __init__(
        self,
        pipeline: Optional[RAGPipeline] = None,
        results_path: Path = RESULTS_FILE,
    ):
        self.pipeline = pipeline or get_pipeline()
        self.results_path = results_path
        self.baseline_retriever = BaselineRetriever(
            embedder=self.pipeline.embedder,
            faiss_store=self.pipeline.faiss_store,
            metadata_store=self.pipeline.metadata_store,
        )
        self.hybrid_retriever = HybridRetriever(
            embedder=self.pipeline.embedder,
            faiss_store=self.pipeline.faiss_store,
            metadata_store=self.pipeline.metadata_store,
        )

    def run_retrieval_benchmark(
        self,
        queries: Optional[List[EvaluationQuery]] = None,
    ) -> Dict[str, Any]:
        """Compare Baseline vs Hybrid retriever on the benchmark dataset."""
        if queries is None:
            queries = BENCHMARK_DATASET

        logger.info(f"Running retrieval benchmark on {len(queries)} queries...")

        def baseline_fn(q_text: str, ver: Optional[str]) -> List[str]:
            return self.baseline_retriever.retrieve_chunk_ids(q_text, top_k=5, version=ver)

        def hybrid_fn(q_text: str, ver: Optional[str]) -> List[str]:
            return self.hybrid_retriever.retrieve_chunk_ids(q_text, top_k=5, version=ver)

        # Baseline evaluation
        t0 = time.perf_counter()
        baseline_results = evaluate_retrieval_batch(baseline_fn, queries, k_values=[1, 3, 5])
        baseline_time_ms = (time.perf_counter() - t0) * 1000.0 / max(len(queries), 1)

        # Hybrid evaluation
        t0 = time.perf_counter()
        hybrid_results = evaluate_retrieval_batch(hybrid_fn, queries, k_values=[1, 3, 5])
        hybrid_time_ms = (time.perf_counter() - t0) * 1000.0 / max(len(queries), 1)

        # Compute delta improvements
        b_avg = baseline_results.get("macro_averages", baseline_results.get("macro_metrics", {}))
        h_avg = hybrid_results.get("macro_averages", hybrid_results.get("macro_metrics", {}))


        deltas = {
            "hit_rate_at_1_delta": round(h_avg["hit_rate_at_1"] - b_avg["hit_rate_at_1"], 4),
            "hit_rate_at_3_delta": round(h_avg["hit_rate_at_3"] - b_avg["hit_rate_at_3"], 4),
            "hit_rate_at_5_delta": round(h_avg["hit_rate_at_5"] - b_avg["hit_rate_at_5"], 4),
            "precision_at_1_delta": round(h_avg["precision_at_1"] - b_avg["precision_at_1"], 4),
            "precision_at_3_delta": round(h_avg["precision_at_3"] - b_avg["precision_at_3"], 4),
            "precision_at_5_delta": round(h_avg["precision_at_5"] - b_avg["precision_at_5"], 4),
            "recall_at_1_delta": round(h_avg["recall_at_1"] - b_avg["recall_at_1"], 4),
            "recall_at_3_delta": round(h_avg["recall_at_3"] - b_avg["recall_at_3"], 4),
            "recall_at_5_delta": round(h_avg["recall_at_5"] - b_avg["recall_at_5"], 4),
            "mrr_delta": round(h_avg["mrr"] - b_avg["mrr"], 4),
            "ndcg_at_5_delta": round(h_avg["ndcg_at_5"] - b_avg["ndcg_at_5"], 4),
        }

        # Category breakdown
        categories: Dict[str, Dict[str, Any]] = {}
        for item in hybrid_results["itemized"]:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = {"baseline_mrr": [], "hybrid_mrr": [], "count": 0}
            categories[cat]["hybrid_mrr"].append(item["mrr"])
            categories[cat]["count"] += 1

        for item in baseline_results["itemized"]:
            cat = item["category"]
            if cat in categories:
                categories[cat]["baseline_mrr"].append(item["mrr"])

        category_summary = {}
        for cat, data in categories.items():
            b_mrr = sum(data["baseline_mrr"]) / len(data["baseline_mrr"]) if data["baseline_mrr"] else 0.0
            h_mrr = sum(data["hybrid_mrr"]) / len(data["hybrid_mrr"]) if data["hybrid_mrr"] else 0.0
            category_summary[cat] = {
                "query_count": data["count"],
                "baseline_mrr": round(b_mrr, 4),
                "hybrid_mrr": round(h_mrr, 4),
                "mrr_improvement": round(h_mrr - b_mrr, 4),
            }

        return {
            "query_count": len(queries),
            "baseline": {
                "macro_averages": b_avg,
                "latency_per_query_ms": round(baseline_time_ms, 2),
            },
            "hybrid": {
                "macro_averages": h_avg,
                "latency_per_query_ms": round(hybrid_time_ms, 2),
            },
            "deltas": deltas,
            "category_breakdown": category_summary,
            "itemized_comparison": [
                {
                    "query_id": b["query_id"],
                    "query": b["query"],
                    "category": b["category"],
                    "expected_chunks": b["expected_chunks"],
                    "baseline_retrieved": b["retrieved_chunks"],
                    "baseline_mrr": b["mrr"],
                    "baseline_ndcg5": b["ndcg_at_5"],
                    "hybrid_retrieved": h["retrieved_chunks"],
                    "hybrid_mrr": h["mrr"],
                    "hybrid_ndcg5": h["ndcg_at_5"],
                }
                for b, h in zip(baseline_results["itemized"], hybrid_results["itemized"])
            ],
        }

    def run_generation_benchmark(
        self,
        queries: Optional[List[EvaluationQuery]] = None,
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate generation quality, citation validity, and claim grounding on benchmark queries."""
        if queries is None:
            queries = BENCHMARK_DATASET

        target_provider = provider_name or os.getenv("LLM_PROVIDER", "mock")
        logger.info(f"Running generation benchmark with provider '{target_provider}' on {len(queries)} queries...")

        provider = get_llm_provider(target_provider)
        old_provider = self.pipeline.llm_provider
        self.pipeline.llm_provider = provider

        itemized: List[Dict[str, Any]] = []
        total_gen_time_ms = 0.0
        total_grounding_score = 0.0
        total_citation_precision = 0.0
        total_citation_coverage = 0.0
        total_supported_claims = 0
        total_partially_supported_claims = 0
        total_unsupported_claims = 0
        total_claims_count = 0

        try:
            for q in queries:
                t0 = time.perf_counter()
                response = self.pipeline.ask(
                    question=q.query,
                    document_version=q.expected_version,
                    top_k=5,
                    retriever_mode="hybrid",
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                total_gen_time_ms += latency_ms

                # Build context chunks for evaluation using hybrid retriever
                raw_retrieved = self.pipeline.hybrid_retriever.retrieve(
                    query=q.query,
                    top_k=5,
                    version=q.expected_version,
                )
                context_chunks = self.pipeline.context_builder.build_context(raw_retrieved)

                # Evaluate citations
                citation_metrics = evaluate_citations(
                    citations=response.citations,
                    retrieved_chunks=context_chunks,
                    claims=response.claims,
                )

                # Evaluate fine-grained grounding
                grounding_res = evaluate_answer_grounding(
                    answer=response.answer,
                    claims=response.claims,
                    retrieved_chunks=context_chunks,
                )

                # Entity overlap
                extracted_entities = extract_architectural_entities(response.answer)
                expected_entities = set(q.expected_entities)
                found_entities = set(extracted_entities)
                overlap = len(found_entities.intersection(expected_entities))
                entity_recall = overlap / float(len(expected_entities)) if expected_entities else 1.0

                item_eval = {
                    "query_id": q.query_id,
                    "query": q.query,
                    "category": q.category,
                    "answer_preview": response.answer[:120] + "..." if len(response.answer) > 120 else response.answer,
                    "confidence": response.confidence.value,
                    "review_required": response.review_required,
                    "citation_count": len(response.citations),
                    "citation_precision": citation_metrics["citation_precision"],
                    "citation_coverage": citation_metrics["citation_coverage"],
                    "grounding_score": grounding_res["grounding_score"],
                    "supported_claims": grounding_res["supported_claims"],
                    "partially_supported_claims": grounding_res["partially_supported_claims"],
                    "unsupported_claims": grounding_res["unsupported_claims"],
                    "expected_entities": q.expected_entities,
                    "found_entities": list(found_entities),
                    "entity_recall": round(entity_recall, 4),
                    "latency_ms": round(latency_ms, 2),
                }
                itemized.append(item_eval)

                total_grounding_score += grounding_res["grounding_score"]
                total_citation_precision += citation_metrics["citation_precision"]
                total_citation_coverage += citation_metrics["citation_coverage"]
                total_supported_claims += grounding_res["supported_claims"]
                total_partially_supported_claims += grounding_res["partially_supported_claims"]
                total_unsupported_claims += grounding_res["unsupported_claims"]
                total_claims_count += grounding_res["total_claims"]

        finally:
            self.pipeline.llm_provider = old_provider

        q_len = max(len(queries), 1)
        return {
            "provider": target_provider,
            "query_count": len(queries),
            "macro_averages": {
                "mean_grounding_score": round(total_grounding_score / q_len, 4),
                "mean_citation_precision": round(total_citation_precision / q_len, 4),
                "mean_citation_coverage": round(total_citation_coverage / q_len, 4),
                "total_claims": total_claims_count,
                "supported_claims_ratio": round(total_supported_claims / max(total_claims_count, 1), 4),
                "partially_supported_claims_ratio": round(total_partially_supported_claims / max(total_claims_count, 1), 4),
                "unsupported_claims_ratio": round(total_unsupported_claims / max(total_claims_count, 1), 4),
                "average_latency_ms": round(total_gen_time_ms / q_len, 2),
            },
            "itemized": itemized,
        }

    def run_abstention_benchmark(
        self,
        queries: Optional[List[UnsupportedQuery]] = None,
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate hallucination resistance and abstention behavior on adversarial queries."""
        if queries is None:
            queries = ADVERSARIAL_UNSUPPORTED_QUERIES

        target_provider = provider_name or os.getenv("LLM_PROVIDER", "mock")
        logger.info(f"Running abstention benchmark with provider '{target_provider}' on {len(queries)} adversarial queries...")

        provider = get_llm_provider(target_provider)
        old_provider = self.pipeline.llm_provider
        self.pipeline.llm_provider = provider

        def query_runner(q_text: str) -> Tuple[str, List[str], ConfidenceLevel, bool]:
            res = self.pipeline.ask(q_text, top_k=5)
            cite_ids = [c.chunk_id for c in res.citations]
            return (res.answer, cite_ids, res.confidence, res.review_required)

        try:
            return evaluate_abstention_batch(query_runner, queries)
        finally:
            self.pipeline.llm_provider = old_provider

    def measure_component_latencies(self) -> Dict[str, Any]:
        """Measure real micro-latencies of each RAG pipeline phase."""
        sample_query = "What components are associated with VehicleControl?"
        
        # 1. Embedding latency
        embed_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            vec = self.pipeline.embedder.embed_query(sample_query)
            embed_times.append((time.perf_counter() - t0) * 1000.0)

        # 2. Baseline retrieval latency
        baseline_retrieval_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = self.baseline_retriever.retrieve_chunk_ids(sample_query, top_k=5)
            baseline_retrieval_times.append((time.perf_counter() - t0) * 1000.0)

        # 3. Hybrid retrieval latency
        hybrid_retrieval_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = self.hybrid_retriever.retrieve(sample_query, top_k=5)
            hybrid_retrieval_times.append((time.perf_counter() - t0) * 1000.0)

        # 4. Mock generation latency
        mock_prov = get_llm_provider("mock")
        gen_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            _ = mock_prov.generate("system prompt", "user query context")
            gen_times.append((time.perf_counter() - t0) * 1000.0)

        # 5. Full pipeline latency (with mock)
        pipeline_times = []
        old_provider = self.pipeline.llm_provider
        self.pipeline.llm_provider = mock_prov
        try:
            for _ in range(5):
                t0 = time.perf_counter()
                _ = self.pipeline.ask(sample_query, top_k=5)
                pipeline_times.append((time.perf_counter() - t0) * 1000.0)
        finally:
            self.pipeline.llm_provider = old_provider

        def avg(lst: List[float]) -> float:
            return round(sum(lst) / len(lst), 2) if lst else 0.0

        return {
            "embedding_latency_ms": avg(embed_times),
            "baseline_retrieval_latency_ms": avg(baseline_retrieval_times),
            "hybrid_retrieval_latency_ms": avg(hybrid_retrieval_times),
            "rerank_overhead_ms": round(max(0.0, avg(hybrid_retrieval_times) - avg(baseline_retrieval_times)), 2),
            "mock_generation_latency_ms": avg(gen_times),
            "full_mock_pipeline_latency_ms": avg(pipeline_times),
        }

    def run_full_benchmark(self, save_results: bool = True) -> Dict[str, Any]:
        """Execute complete benchmark suite and persist un-fabricated metrics."""
        t_start = time.time()
        logger.info("Starting Full Phase 4 Evaluation Benchmark...")

        retrieval_eval = self.run_retrieval_benchmark()
        generation_eval = self.run_generation_benchmark()
        abstention_eval = self.run_abstention_benchmark()
        latency_eval = self.measure_component_latencies()

        duration = round(time.time() - t_start, 2)
        logger.info(f"Full Benchmark completed in {duration}s.")

        benchmark_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "total_benchmark_duration_seconds": duration,
            "dataset": {
                "grounded_queries_count": len(BENCHMARK_DATASET),
                "unsupported_queries_count": len(ADVERSARIAL_UNSUPPORTED_QUERIES),
                "total_queries_evaluated": len(BENCHMARK_DATASET) + len(ADVERSARIAL_UNSUPPORTED_QUERIES),
            },
            "retrieval_evaluation": retrieval_eval,
            "generation_evaluation": generation_eval,
            "abstention_evaluation": abstention_eval,
            "latency_benchmarks": latency_eval,
            "key_metrics_summary": {
                "baseline_mrr": retrieval_eval["baseline"]["macro_averages"]["mrr"],
                "hybrid_mrr": retrieval_eval["hybrid"]["macro_averages"]["mrr"],
                "mrr_improvement": retrieval_eval["deltas"]["mrr_delta"],
                "baseline_ndcg5": retrieval_eval["baseline"]["macro_averages"]["ndcg_at_5"],
                "hybrid_ndcg5": retrieval_eval["hybrid"]["macro_averages"]["ndcg_at_5"],
                "ndcg5_improvement": retrieval_eval["deltas"]["ndcg_at_5_delta"],
                "baseline_hit_rate_at_1": retrieval_eval["baseline"]["macro_averages"]["hit_rate_at_1"],
                "hybrid_hit_rate_at_1": retrieval_eval["hybrid"]["macro_averages"]["hit_rate_at_1"],
                "citation_precision": generation_eval["macro_averages"]["mean_citation_precision"],
                "citation_coverage": generation_eval["macro_averages"]["mean_citation_coverage"],
                "supported_claims_ratio": generation_eval["macro_averages"]["supported_claims_ratio"],
                "adversarial_abstention_accuracy": abstention_eval["abstention_accuracy"],
                "hallucination_rate": abstention_eval["hallucination_rate"],
            },
        }

        if save_results:
            self.results_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.results_path, "w", encoding="utf-8") as f:
                json.dump(benchmark_summary, f, indent=2)
            logger.info(f"Benchmark results successfully saved to {self.results_path}")

        return benchmark_summary


def load_benchmark_results(results_path: Path = RESULTS_FILE) -> Optional[Dict[str, Any]]:
    """Load cached benchmark results if available on disk."""
    if not results_path.exists():
        return None
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load benchmark results from {results_path}: {e}")
        return None


def get_or_run_benchmark(force_recompute: bool = False) -> Dict[str, Any]:
    """Return existing benchmark results or execute fresh evaluation."""
    if not force_recompute:
        cached = load_benchmark_results()
        if cached:
            return cached

    runner = BenchmarkRunner()
    return runner.run_full_benchmark(save_results=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("Executing Phase 4 Benchmark Harness...")
    runner = BenchmarkRunner()
    results = runner.run_full_benchmark(save_results=True)
    km = results["key_metrics_summary"]
    print("\n" + "=" * 60)
    print("PHASE 4 BENCHMARK EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Retrieval MRR:        Baseline = {km['baseline_mrr']:.4f} -> Hybrid = {km['hybrid_mrr']:.4f} (diff: {km['mrr_improvement']:+.4f})")
    print(f"Retrieval nDCG@5:     Baseline = {km['baseline_ndcg5']:.4f} -> Hybrid = {km['hybrid_ndcg5']:.4f} (diff: {km['ndcg5_improvement']:+.4f})")
    print(f"Hit Rate @ 1:         Baseline = {km['baseline_hit_rate_at_1']:.4f} -> Hybrid = {km['hybrid_hit_rate_at_1']:.4f}")
    print(f"Citation Precision:   {km['citation_precision']:.2%}")
    print(f"Citation Coverage:    {km['citation_coverage']:.2%}")
    print(f"Supported Claims %:   {km['supported_claims_ratio']:.2%}")
    print(f"Abstention Accuracy:  {km['adversarial_abstention_accuracy']:.2%}")
    print(f"Hallucination Rate:   {km['hallucination_rate']:.2%}")
    print("=" * 60)
