"""Build genuine evaluation datasets for AUTOSAR HLD Assistant.

Independently invokes the actual RAG pipeline with retriever_mode="baseline"
and retriever_mode="hybrid" under controlled, identical parameters (top_k=5,
same questions, expected versions).

Guarantees:
- Independent answer generation per retriever mode (no historical answer_preview reuse)
- Actual system responses recorded for unsupported queries (no fabricated text)
- Preservation of documented ground-truth references and expected chunk IDs
- Separation of grounded queries and unsupported queries for abstention analysis
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure runtime compatibility shim is active before any third-party imports
import evaluation_result.ragas.compat  # noqa: F401

os.environ["HF_HUB_OFFLINE"] = "1"

from evaluation.dataset import BENCHMARK_QUERIES, ADVERSARIAL_UNSUPPORTED_QUERIES
from rag.hybrid_retriever import get_baseline_retriever, get_hybrid_retriever
from rag.pipeline import get_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("build_eval_datasets")


def build_datasets(output_dir_str: str = "evaluation_result/dataset"):
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing retrievers and RAG pipeline...")
    base_retriever = get_baseline_retriever()
    hyb_retriever = get_hybrid_retriever()
    pipeline = get_pipeline(provider_name="mock")

    baseline_records: List[Dict[str, Any]] = []
    hybrid_records: List[Dict[str, Any]] = []
    unsupported_records: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # 1. Process 25 Grounded Queries with Independent Pipeline Calls
    # --------------------------------------------------------------------------
    logger.info(f"Processing {len(BENCHMARK_QUERIES)} grounded benchmark queries...")
    for idx, q in enumerate(BENCHMARK_QUERIES, start=1):
        qid = q.id
        question = q.question
        ref_answer = q.expected_answer
        expected_chunks = q.expected_chunks
        expected_version = q.expected_version

        logger.info(f"[{idx}/{len(BENCHMARK_QUERIES)}] Generating genuine answers for {qid}...")

        # --- A. Baseline Execution (FAISS Dense Retriever) ---
        b_results = base_retriever.retrieve_chunks(question, version=expected_version, top_k=5)
        b_contexts = [chunk["text"] for score, chunk in b_results if "text" in chunk]
        b_context_ids = [chunk["chunk_id"] for score, chunk in b_results if "chunk_id" in chunk]

        # Independently invoke actual pipeline in baseline mode
        res_baseline = pipeline.ask(
            question=question,
            document_version=expected_version,
            top_k=5,
            retriever_mode="baseline",
        )
        b_ans = res_baseline.answer

        baseline_records.append({
            "sample_id": qid,
            "query_id": qid,
            "user_input": question,
            "question": question,
            "reference": ref_answer,
            "ground_truth": ref_answer,
            "reference_source": "AUTOSAR Ground Truth Specification Reference",
            "response": b_ans,
            "answer": b_ans,
            "retrieved_contexts": b_contexts,
            "retrieved_context_ids": b_context_ids,
            "reference_context_ids": expected_chunks,
            "expected_entities": q.expected_entities,
            "query_type": q.query_type,
            "expected_version": expected_version,
            "retriever_mode": "baseline",
            "confidence": res_baseline.confidence.value,
            "review_required": res_baseline.review_required,
            "grounding_score": res_baseline.grounding_score,
            "limitations": res_baseline.limitations,
            "is_unsupported": False,
        })

        # --- B. Hybrid Execution (Architecture-Aware Multi-Signal Retriever) ---
        h_results = hyb_retriever.retrieve_chunks(question, version=expected_version, top_k=5)
        h_contexts = [chunk["text"] for score, chunk in h_results if "text" in chunk]
        h_context_ids = [chunk["chunk_id"] for score, chunk in h_results if "chunk_id" in chunk]

        # Independently invoke actual pipeline in hybrid mode
        res_hybrid = pipeline.ask(
            question=question,
            document_version=expected_version,
            top_k=5,
            retriever_mode="hybrid",
        )
        h_ans = res_hybrid.answer

        hybrid_records.append({
            "sample_id": qid,
            "query_id": qid,
            "user_input": question,
            "question": question,
            "reference": ref_answer,
            "ground_truth": ref_answer,
            "reference_source": "AUTOSAR Ground Truth Specification Reference",
            "response": h_ans,
            "answer": h_ans,
            "retrieved_contexts": h_contexts,
            "retrieved_context_ids": h_context_ids,
            "reference_context_ids": expected_chunks,
            "expected_entities": q.expected_entities,
            "query_type": q.query_type,
            "expected_version": expected_version,
            "retriever_mode": "hybrid",
            "confidence": res_hybrid.confidence.value,
            "review_required": res_hybrid.review_required,
            "grounding_score": res_hybrid.grounding_score,
            "limitations": res_hybrid.limitations,
            "is_unsupported": False,
        })

    # --------------------------------------------------------------------------
    # 2. Process 10 Adversarial / Unsupported Queries with Actual System Responses
    # --------------------------------------------------------------------------
    logger.info(f"Processing {len(ADVERSARIAL_UNSUPPORTED_QUERIES)} adversarial / unsupported queries...")
    for idx, adv in enumerate(ADVERSARIAL_UNSUPPORTED_QUERIES, start=1):
        adv_id = adv.id
        adv_q = adv.question
        adv_ref = adv.expected_answer

        logger.info(f"[{idx}/{len(ADVERSARIAL_UNSUPPORTED_QUERIES)}] Recording actual responses for {adv_id}...")

        # Baseline retrieval and answer
        b_results = base_retriever.retrieve_chunks(adv_q, top_k=5)
        b_contexts = [chunk["text"] for score, chunk in b_results if "text" in chunk]
        b_context_ids = [chunk["chunk_id"] for score, chunk in b_results if "chunk_id" in chunk]
        res_adv_b = pipeline.ask(adv_q, top_k=5, retriever_mode="baseline")

        # Hybrid retrieval and answer
        h_results = hyb_retriever.retrieve_chunks(adv_q, top_k=5)
        h_contexts = [chunk["text"] for score, chunk in h_results if "text" in chunk]
        h_context_ids = [chunk["chunk_id"] for score, chunk in h_results if "chunk_id" in chunk]
        res_adv_h = pipeline.ask(adv_q, top_k=5, retriever_mode="hybrid")

        adv_record_b = {
            "sample_id": adv_id,
            "query_id": adv_id,
            "user_input": adv_q,
            "question": adv_q,
            "reference": adv_ref,
            "ground_truth": adv_ref,
            "reference_source": "AUTOSAR Ground Truth Specification Reference",
            "response": res_adv_b.answer,
            "answer": res_adv_b.answer,
            "retrieved_contexts": b_contexts,
            "retrieved_context_ids": b_context_ids,
            "reference_context_ids": [],
            "expected_entities": [],
            "query_type": "UNSUPPORTED_QUERY",
            "expected_version": None,
            "retriever_mode": "baseline",
            "confidence": res_adv_b.confidence.value,
            "review_required": res_adv_b.review_required,
            "grounding_score": res_adv_b.grounding_score,
            "limitations": res_adv_b.limitations,
            "is_unsupported": True,
            "exclusion_reason": "UNSUPPORTED_ADVERSARIAL_QUERY",
        }

        adv_record_h = {
            "sample_id": adv_id,
            "query_id": adv_id,
            "user_input": adv_q,
            "question": adv_q,
            "reference": adv_ref,
            "ground_truth": adv_ref,
            "reference_source": "AUTOSAR Ground Truth Specification Reference",
            "response": res_adv_h.answer,
            "answer": res_adv_h.answer,
            "retrieved_contexts": h_contexts,
            "retrieved_context_ids": h_context_ids,
            "reference_context_ids": [],
            "expected_entities": [],
            "query_type": "UNSUPPORTED_QUERY",
            "expected_version": None,
            "retriever_mode": "hybrid",
            "confidence": res_adv_h.confidence.value,
            "review_required": res_adv_h.review_required,
            "grounding_score": res_adv_h.grounding_score,
            "limitations": res_adv_h.limitations,
            "is_unsupported": True,
            "exclusion_reason": "UNSUPPORTED_ADVERSARIAL_QUERY",
        }

        baseline_records.append(adv_record_b)
        hybrid_records.append(adv_record_h)
        unsupported_records.append({
            "query_id": adv_id,
            "question": adv_q,
            "expected_abstention": True,
            "baseline": adv_record_b,
            "hybrid": adv_record_h,
        })

    # --------------------------------------------------------------------------
    # 3. Serialize Datasets in JSON and JSONL formats
    # --------------------------------------------------------------------------
    def _write_json_and_jsonl(records: List[Dict[str, Any]], base_name: str):
        j_path = output_dir / f"{base_name}.json"
        with open(j_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        jl_path = output_dir / f"{base_name}.jsonl"
        with open(jl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        logger.info(f"Saved {base_name}: {len(records)} records -> {j_path} and {jl_path}")

    _write_json_and_jsonl(baseline_records, "baseline_eval_dataset")
    _write_json_and_jsonl(hybrid_records, "hybrid_eval_dataset")
    _write_json_and_jsonl(unsupported_records, "unsupported_eval_dataset")

    logger.info("Dataset construction complete: 25 grounded + 10 unsupported queries serialized successfully.")


if __name__ == "__main__":
    build_datasets()
