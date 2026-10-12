"""Information Retrieval (IR) evaluation metrics for AUTOSAR HLD RAG retrieval.

Implements standard ranking and retrieval metrics:
- Precision@K (K=1, 3, 5)
- Recall@K (K=1, 3, 5)
- Hit Rate@K (K=1, 3, 5)
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (nDCG@K)
"""

import math
from typing import Any, Callable, Dict, List, Optional, Set
from evaluation.dataset import EvaluationQuery


def compute_precision_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    """Compute Precision@K: proportion of top-K retrieved items that are relevant."""
    if k <= 0:
        return 0.0
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0
    expected_set = set(expected)
    relevant_in_k = sum(1 for item in retrieved_k if item in expected_set)
    return relevant_in_k / float(k)


def compute_recall_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    """Compute Recall@K: proportion of relevant items retrieved in top-K."""
    if not expected:
        return 1.0
    retrieved_k = retrieved[:k]
    expected_set = set(expected)
    relevant_in_k = sum(1 for item in retrieved_k if item in expected_set)
    return relevant_in_k / float(len(expected_set))


def compute_hit_rate_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    """Compute Hit Rate@K (Success@K): 1.0 if at least one relevant item in top-K, else 0.0."""
    retrieved_k = retrieved[:k]
    expected_set = set(expected)
    for item in retrieved_k:
        if item in expected_set:
            return 1.0
    return 0.0


def compute_reciprocal_rank(retrieved: List[str], expected: List[str]) -> float:
    """Compute Reciprocal Rank (RR): 1 / rank of the first relevant retrieved item."""
    expected_set = set(expected)
    for rank_idx, item in enumerate(retrieved, start=1):
        if item in expected_set:
            return 1.0 / float(rank_idx)
    return 0.0


def compute_ndcg_at_k(retrieved: List[str], expected: List[str], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG@K) with binary relevance."""
    if k <= 0 or not expected:
        return 0.0

    retrieved_k = retrieved[:k]
    expected_set = set(expected)

    # Discounted Cumulative Gain (DCG)
    dcg = 0.0
    for idx, item in enumerate(retrieved_k, start=1):
        rel = 1.0 if item in expected_set else 0.0
        dcg += rel / math.log2(idx + 1)

    # Ideal Discounted Cumulative Gain (IDCG)
    idcg = 0.0
    ideal_hits = min(k, len(expected_set))
    for idx in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def evaluate_retrieval_batch(
    retriever_fn: Callable[[str, Optional[str]], List[str]],
    dataset: List[EvaluationQuery],
    k_values: List[int] = None,
) -> Dict[str, Any]:
    """Evaluate a retriever function across a benchmark dataset.

    Args:
        retriever_fn: Callable taking (query_text, expected_version) -> List[chunk_id]
        dataset: List of EvaluationQuery benchmark items
        k_values: List of cutoffs (defaults to [1, 3, 5])

    Returns:
        Dictionary with macro averages and itemized results per query.
    """
    if k_values is None:
        k_values = [1, 3, 5]

    itemized_results: List[Dict[str, Any]] = []

    p_at_k_accum: Dict[int, List[float]] = {k: [] for k in k_values}
    r_at_k_accum: Dict[int, List[float]] = {k: [] for k in k_values}
    hit_at_k_accum: Dict[int, List[float]] = {k: [] for k in k_values}
    rr_accum: List[float] = []
    ndcg_at_5_accum: List[float] = []

    for q in dataset:
        if q.is_unsupported:
            continue

        retrieved_ids = retriever_fn(q.question, q.expected_version)

        q_res: Dict[str, Any] = {
            "query_id": q.id,
            "query": q.query,
            "question": q.question,
            "category": q.category,
            "query_type": q.query_type,
            "expected_version": q.expected_version,
            "expected_chunks": q.expected_chunks,
            "retrieved_chunks": retrieved_ids,
            "relevant_retrieved": [c for c in retrieved_ids if c in set(q.expected_chunks)],
        }

        rr = compute_reciprocal_rank(retrieved_ids, q.expected_chunks)
        rr_accum.append(rr)
        q_res["reciprocal_rank"] = round(rr, 4)
        q_res["mrr"] = round(rr, 4)

        ndcg_5 = compute_ndcg_at_k(retrieved_ids, q.expected_chunks, k=5)
        ndcg_at_5_accum.append(ndcg_5)
        q_res["ndcg_at_5"] = round(ndcg_5, 4)
        q_res["ndcg5"] = round(ndcg_5, 4)

        for k in k_values:
            p_k = compute_precision_at_k(retrieved_ids, q.expected_chunks, k=k)
            r_k = compute_recall_at_k(retrieved_ids, q.expected_chunks, k=k)
            h_k = compute_hit_rate_at_k(retrieved_ids, q.expected_chunks, k=k)

            p_at_k_accum[k].append(p_k)
            r_at_k_accum[k].append(r_k)
            hit_at_k_accum[k].append(h_k)

            q_res[f"precision_at_{k}"] = round(p_k, 4)
            q_res[f"recall_at_{k}"] = round(r_k, 4)
            q_res[f"hit_rate_at_{k}"] = round(h_k, 4)

        itemized_results.append(q_res)

    total_queries = len(itemized_results)
    if total_queries == 0:
        return {"total_queries": 0, "macro_metrics": {}, "macro_averages": {}, "itemized": []}

    macro_metrics = {
        "total_queries": total_queries,
        "mrr": round(sum(rr_accum) / total_queries, 4),
        "ndcg_at_5": round(sum(ndcg_at_5_accum) / total_queries, 4),
    }

    for k in k_values:
        macro_metrics[f"precision_at_{k}"] = round(sum(p_at_k_accum[k]) / total_queries, 4)
        macro_metrics[f"recall_at_{k}"] = round(sum(r_at_k_accum[k]) / total_queries, 4)
        macro_metrics[f"hit_rate_at_{k}"] = round(sum(hit_at_k_accum[k]) / total_queries, 4)

    return {
        "macro_metrics": macro_metrics,
        "macro_averages": macro_metrics,
        "itemized": itemized_results,
    }


# Convenient function aliases
precision_at_k = compute_precision_at_k
recall_at_k = compute_recall_at_k
hit_rate_at_k = compute_hit_rate_at_k
mean_reciprocal_rank = compute_reciprocal_rank
ndcg_at_k = compute_ndcg_at_k

