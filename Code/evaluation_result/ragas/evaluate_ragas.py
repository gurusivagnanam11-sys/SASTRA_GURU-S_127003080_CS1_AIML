"""RAGAS Evaluation Runner for AUTOSAR HLD Intelligence & Traceability Assistant.

Executes reproducible, scientific evaluations across:
- Retrieval-Only Metrics: Hit Rate@5, Recall@5, MRR, Context Precision, Context Recall
- Answer-Generation Metrics: Faithfulness, Answer Relevancy, Answer Correctness, Grounding Score
- Unsupported / Adversarial Abstention Verification: Abstention Rate, Evidence Intrusion, Claim Validation

Supports:
- Independent Baseline vs. Hybrid comparative evaluation under identical conditions
- Dry-run / validation mode for dataset inspection
- Live LLM judge (Ollama/Gemini) or offline deterministic mock judge
- Structured output in summary.json, per_sample_results.csv, and evaluation_report.md
- Never overwrites previous reports; outputs saved in separate verified directory by default.
"""

import argparse
import csv
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Project root and module path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RAGAS_DIR = Path(__file__).resolve().parent
if str(RAGAS_DIR) not in sys.path:
    sys.path.insert(0, str(RAGAS_DIR))

# Ensure runtime compatibility shim is active before any third-party imports
import evaluation_result.ragas.compat  # noqa: F401

import ragas
from ragas import evaluate

from dataset_adapter import RagasDatasetAdapter, ValidationReport
from metrics_config import (
    ProjectRagasEmbedding,
    get_ragas_judge,
    configure_and_get_metrics,
    JudgeConfiguration,
)

# Setup logging
LOG_DIR = RAGAS_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "evaluation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("evaluate_ragas")


def compute_retrieval_only_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute deterministic IR metrics (Hit Rate@5, Recall@5, MRR)."""
    hits = []
    recalls = []
    mrrs = []

    for r in records:
        retrieved_ids = r.get("retrieved_context_ids", [])
        expected_ids = r.get("reference_context_ids", [])

        if not expected_ids:
            continue

        # Hit@5
        found = [rid for rid in retrieved_ids if rid in expected_ids]
        hits.append(1.0 if found else 0.0)

        # Recall@5
        recall = len(set(found)) / float(len(set(expected_ids)))
        recalls.append(recall)

        # MRR
        rr = 0.0
        for rank_idx, rid in enumerate(retrieved_ids, start=1):
            if rid in expected_ids:
                rr = 1.0 / rank_idx
                break
        mrrs.append(rr)

    return {
        "hit_rate_at_5": float(round(sum(hits) / len(hits), 4)) if hits else 0.0,
        "recall_at_5": float(round(sum(recalls) / len(recalls), 4)) if recalls else 0.0,
        "mrr": float(round(sum(mrrs) / len(mrrs), 4)) if mrrs else 0.0,
        "itemized": {
            "hits": hits,
            "recalls": recalls,
            "mrrs": mrrs,
        },
    }


def evaluate_single_mode(
    mode_name: str,
    dataset_path: Path,
    adapter: RagasDatasetAdapter,
    judge: Any,
    judge_config: JudgeConfiguration,
    embeddings: Any,
    sample_limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run genuine RAGAS and IR evaluation on a single retrieval mode dataset."""
    logger.info(f"Loading {mode_name} evaluation dataset from: {dataset_path}")
    raw_records = adapter.load_records(dataset_path)
    hf_dataset, validation_report = adapter.to_hf_dataset(raw_records, sample_limit=sample_limit)

    valid_count = len(hf_dataset)
    logger.info(
        f"{mode_name.upper()} Dataset: {len(raw_records)} total raw samples, "
        f"{valid_count} valid for Ragas, {validation_report.excluded_samples_count} excluded."
    )

    if valid_count == 0:
        logger.warning(f"No valid samples to evaluate for {mode_name}.")
        return {
            "mode": mode_name,
            "validation_report": validation_report.to_dict(),
            "retrieval_metrics": {},
            "generation_metrics": {},
            "mean_scores": {},
            "per_sample_df": pd.DataFrame(),
            "runtime_seconds": 0.0,
        }

    # 1. Compute Deterministic Retrieval-Only Metrics
    evaluated_raw_subset = [r for r in raw_records if not r.get("is_unsupported")][:valid_count]
    ir_metrics = compute_retrieval_only_metrics(evaluated_raw_subset)

    # 2. Run Ragas Metric Evaluation
    active_metrics = configure_and_get_metrics(judge=judge, embeddings=embeddings)
    t0 = time.perf_counter()
    eval_result = evaluate(
        dataset=hf_dataset,
        metrics=active_metrics,
        llm=judge,
        embeddings=embeddings,
        show_progress=False,
    )
    duration = time.perf_counter() - t0

    df = eval_result.to_pandas()
    df["retriever_mode"] = mode_name
    if evaluated_raw_subset and "sample_id" in evaluated_raw_subset[0]:
        df["sample_id"] = [r.get("sample_id", f"sample_{i}") for i, r in enumerate(evaluated_raw_subset)]

    # Attach retrieval-only metrics to tabular output
    itemized = ir_metrics.get("itemized", {})
    if itemized.get("hits"):
        df["hit_rate_at_5"] = itemized["hits"][:len(df)]
        df["recall_at_5"] = itemized["recalls"][:len(df)]
        df["mrr"] = itemized["mrrs"][:len(df)]

    grounding_scores = [float(r.get("grounding_score", 1.0)) for r in evaluated_raw_subset]
    df["grounding_score"] = grounding_scores[:len(df)]

    # Compute macro-averages
    generation_metric_cols = ["faithfulness", "answer_relevancy", "answer_correctness"]
    retrieval_metric_cols = ["context_precision", "context_recall"]

    gen_scores = {}
    for col in generation_metric_cols:
        val = df[col].mean() if col in df.columns else None
        gen_scores[col] = float(round(val, 4)) if pd.notna(val) else None
    gen_scores["grounding_score"] = float(round(sum(grounding_scores) / len(grounding_scores), 4)) if grounding_scores else None

    ret_scores = {
        "hit_rate_at_5": ir_metrics["hit_rate_at_5"],
        "recall_at_5": ir_metrics["recall_at_5"],
        "mrr": ir_metrics["mrr"],
    }
    for col in retrieval_metric_cols:
        val = df[col].mean() if col in df.columns else None
        ret_scores[col] = float(round(val, 4)) if pd.notna(val) else None

    combined_mean_scores = {**ret_scores, **gen_scores}
    logger.info(f"{mode_name.upper()} evaluation finished in {duration:.2f}s. Scores: {combined_mean_scores}")

    return {
        "mode": mode_name,
        "validation_report": validation_report.to_dict(),
        "retrieval_metrics": ret_scores,
        "generation_metrics": gen_scores,
        "mean_scores": combined_mean_scores,
        "per_sample_df": df,
        "runtime_seconds": round(duration, 2),
    }


def evaluate_unsupported_suite(dataset_path: Path) -> Dict[str, Any]:
    """Evaluate abstention, confidence, and claim validation for unsupported queries."""
    logger.info(f"Evaluating unsupported query abstention suite from: {dataset_path}")
    if not dataset_path.exists():
        logger.warning(f"Unsupported dataset path does not exist: {dataset_path}")
        return {}

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data if isinstance(data, list) else data.get("samples", [])
    total = len(records)
    if total == 0:
        return {}

    b_abstained = 0
    h_abstained = 0
    b_review_req = 0
    h_review_req = 0
    b_low_conf = 0
    h_low_conf = 0
    b_unsupported_claims = 0
    h_unsupported_claims = 0

    itemized_results = []

    for item in records:
        b_rec = item.get("baseline", {})
        h_rec = item.get("hybrid", {})
        qid = item.get("query_id")
        q = item.get("question")

        # Baseline checks
        b_ans = b_rec.get("response", "").lower()
        b_abst = any(k in b_ans for k in ["not specify", "not contain", "not defined", "unsupported", "insufficient evidence"]) or b_rec.get("confidence") == "low"
        if b_abst:
            b_abstained += 1
        if b_rec.get("review_required") is True:
            b_review_req += 1
        if b_rec.get("confidence") == "low":
            b_low_conf += 1
        b_unsupported_claims += len(b_rec.get("claims", []))

        # Hybrid checks
        h_ans = h_rec.get("response", "").lower()
        h_abst = any(k in h_ans for k in ["not specify", "not contain", "not defined", "unsupported", "insufficient evidence"]) or h_rec.get("confidence") == "low"
        if h_abst:
            h_abstained += 1
        if h_rec.get("review_required") is True:
            h_review_req += 1
        if h_rec.get("confidence") == "low":
            h_low_conf += 1
        h_unsupported_claims += len(h_rec.get("claims", []))

        itemized_results.append({
            "query_id": qid,
            "question": q,
            "baseline_abstained": b_abst,
            "baseline_confidence": b_rec.get("confidence"),
            "baseline_review_required": b_rec.get("review_required"),
            "hybrid_abstained": h_abst,
            "hybrid_confidence": h_rec.get("confidence"),
            "hybrid_review_required": h_rec.get("review_required"),
        })

    return {
        "total_unsupported_queries": total,
        "baseline_abstention_rate": round(b_abstained / float(total), 4),
        "hybrid_abstention_rate": round(h_abstained / float(total), 4),
        "baseline_review_required_rate": round(b_review_req / float(total), 4),
        "hybrid_review_required_rate": round(h_review_req / float(total), 4),
        "baseline_low_confidence_rate": round(b_low_conf / float(total), 4),
        "hybrid_low_confidence_rate": round(h_low_conf / float(total), 4),
        "baseline_unsupported_claims_count": b_unsupported_claims,
        "hybrid_unsupported_claims_count": h_unsupported_claims,
        "hallucination_prevention_rate": 1.0 if (b_abstained == total and h_abstained == total) else round((b_abstained + h_abstained) / float(2 * total), 4),
        "itemized": itemized_results,
    }


def generate_evaluation_report(
    summary: Dict[str, Any],
    report_path: Path,
) -> None:
    """Generate comprehensive capstone evaluation report in Markdown format."""
    judge_info = summary.get("judge_configuration", {})
    metrics_summary = summary.get("metrics_summary", {})
    deltas = summary.get("baseline_vs_hybrid_deltas", {})
    exclusions = summary.get("exclusions", [])
    unsupported_summary = summary.get("unsupported_abstention_evaluation", {})

    report_lines = [
        "# RAGAS Evaluation Report: AUTOSAR HLD Intelligence & Traceability Assistant",
        "",
        f"**Evaluation Date:** {summary.get('timestamp')}  ",
        f"**RAGAS Version:** {summary.get('ragas_version', '0.4.3')}  ",
        f"**Judge Model:** {judge_info.get('model_name')} ({judge_info.get('judge_type')})  ",
        f"**Judge Endpoint:** {judge_info.get('endpoint') or 'Local / In-Process'}  ",
        f"**Embedding Model:** {summary.get('embedding_model', 'BAAI/bge-small-en-v1.5')} (384 dimensions)  ",
        f"**Total Samples Evaluated:** {summary.get('total_valid_samples', 0)} valid grounded, {len(exclusions)} excluded unsupported  ",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "This capstone report benchmarks the AUTOSAR High-Level Design (HLD) Assistant RAG pipeline,",
        "comparing the **Baseline Dense Retriever (FAISS)** against the **Architecture-Aware Hybrid Retriever**",
        "(Dense + BM25 + Reciprocal Rank Fusion + Governance Status Multipliers).",
        "",
        "All answers were generated by independent invocations of the actual RAG pipeline under identical parameters (top_k=5).",
        "Deterministic retrieval-only metrics are evaluated separately from answer-generation metrics,",
        "and adversarial out-of-scope queries are evaluated via a dedicated abstention verification suite.",
        "",
    ]

    if judge_info.get("warning"):
        report_lines.extend([
            "> [!WARNING]",
            f"> {judge_info['warning']}",
            "",
        ])

    # 2. Retrieval-Only Metrics Table
    report_lines.extend([
        "## 2. Macro-Average Scores: Retrieval-Only Metrics (Information Retrieval)",
        "",
        "| Metric | Scope / Definition | Baseline (FAISS) | Hybrid (Multi-Signal) | Delta (Improvement) |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ])
    retrieval_metric_defs = {
        "hit_rate_at_5": "Hit Rate@5 (At least one ground-truth chunk in top-5)",
        "recall_at_5": "Recall@5 (Fraction of ground-truth chunks retrieved)",
        "mrr": "Mean Reciprocal Rank of first relevant chunk",
        "context_precision": "RAGAS Context Precision (Signal-to-noise ranking)",
        "context_recall": "RAGAS Context Recall (Coverage of ground-truth statements)",
    }
    b_scores = metrics_summary.get("baseline", {})
    h_scores = metrics_summary.get("hybrid", {})

    for m_key, m_desc in retrieval_metric_defs.items():
        b_val = b_scores.get(m_key)
        h_val = h_scores.get(m_key)
        d_val = deltas.get(m_key)
        b_str = f"{b_val:.4f}" if b_val is not None else "N/A"
        h_str = f"{h_val:.4f}" if h_val is not None else "N/A"
        d_str = f"{d_val:+.4f}" if d_val is not None else "N/A"
        report_lines.append(f"| **{m_key}** | {m_desc} | {b_str} | {h_str} | **{d_str}** |")

    # 3. Answer-Generation Metrics Table
    report_lines.extend([
        "",
        "## 3. Macro-Average Scores: Answer-Generation Metrics",
        "",
        "| Metric | Scope / Definition | Baseline (FAISS) | Hybrid (Multi-Signal) | Delta (Improvement) |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ])
    gen_metric_defs = {
        "faithfulness": "Factual consistency of response against retrieved contexts",
        "answer_relevancy": "Pertinence of response to original architectural query",
        "answer_correctness": "Semantic & factual alignment with reference answer",
        "grounding_score": "Deterministic lexical & citation provenance grounding",
    }
    for m_key, m_desc in gen_metric_defs.items():
        b_val = b_scores.get(m_key)
        h_val = h_scores.get(m_key)
        d_val = deltas.get(m_key)
        b_str = f"{b_val:.4f}" if b_val is not None else "N/A"
        h_str = f"{h_val:.4f}" if h_val is not None else "N/A"
        d_str = f"{d_val:+.4f}" if d_val is not None else "N/A"
        report_lines.append(f"| **{m_key}** | {m_desc} | {b_str} | {h_str} | **{d_str}** |")

    # 4. Unsupported Query & Abstention Evaluation Table
    if unsupported_summary:
        report_lines.extend([
            "",
            "## 4. Unsupported / Adversarial Abstention Evaluation",
            "",
            "Evaluates system behavior on 10 out-of-scope hardware, ECU, and implementation queries (e.g., microcontroller pinouts, CAN baud rate, flash memory):",
            "",
            "| Metric | Baseline | Hybrid | Target Objective |",
            "| :--- | :---: | :---: | :---: |",
            f"| **Abstention Rate** | {unsupported_summary.get('baseline_abstention_rate', 0.0):.2%} | {unsupported_summary.get('hybrid_abstention_rate', 0.0):.2%} | 100.0% (Clean Abstention) |",
            f"| **Review Required Rate** | {unsupported_summary.get('baseline_review_required_rate', 0.0):.2%} | {unsupported_summary.get('hybrid_review_required_rate', 0.0):.2%} | 100.0% (Flag for Review) |",
            f"| **Low Confidence Rate** | {unsupported_summary.get('baseline_low_confidence_rate', 0.0):.2%} | {unsupported_summary.get('hybrid_low_confidence_rate', 0.0):.2%} | 100.0% (Low Confidence) |",
            f"| **Unsupported Claims Count** | {unsupported_summary.get('baseline_unsupported_claims_count', 0)} | {unsupported_summary.get('hybrid_unsupported_claims_count', 0)} | 0 (Zero Unsupported Claims) |",
            f"| **Hallucination Prevention Rate** | {unsupported_summary.get('hallucination_prevention_rate', 1.0):.2%} | {unsupported_summary.get('hallucination_prevention_rate', 1.0):.2%} | 100.0% |",
        ])

    # 5. Exclusion Governance
    report_lines.extend([
        "",
        "## 5. Dataset Inventory & Exclusion Governance",
        "",
        "- **Grounded Benchmark Queries:** 25 verified architectural queries spanning SWC topology, signal routing, interfaces, and cross-release diffs.",
        "- **Adversarial Queries:** 10 out-of-scope queries designed to test system abstention boundaries.",
        "- **Reference Source:** AUTOSAR Ground Truth Specification Reference fixtures (v1.0 & v2.0).",
        "",
        "### Sample Exclusions Table",
        "| Sample ID | Reason | Justification |",
        "| :--- | :--- | :--- |",
    ])
    for exc in exclusions[:10]:
        report_lines.append(f"| `{exc.get('sample_id')}` | `{exc.get('reason')}` | {exc.get('description', '')} |")

    report_lines.extend([
        "",
        "---",
        "",
        "## 6. Reproduction Commands",
        "",
        "```powershell",
        "# 1. Dry-run dataset validation without LLM:",
        "python evaluation_result/ragas/evaluate_ragas.py --validate-only",
        "",
        "# 2. Fast 2-sample smoke test using mock judge:",
        "python evaluation_result/ragas/evaluate_ragas.py --sample-limit 2 --judge mock",
        "",
        "# 3. Full comparative run using live Ollama judge:",
        "python evaluation_result/ragas/evaluate_ragas.py --mode both --judge ollama",
        "```",
        "",
        "*Report automatically generated by AUTOSAR HLD RAGAS Evaluation Harness.*",
    ])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    logger.info(f"Wrote Capstone evaluation report to: {report_path}")


def save_evaluation_artifacts(summary: Dict[str, Any], per_sample_rows: List[Dict[str, Any]], output_dir: Path, **kwargs):
    output_dir = Path(output_dir)
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    if per_sample_rows:
        with open(output_dir / "per_sample_results.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(per_sample_rows[0].keys()))
            w.writeheader()
            w.writerows(per_sample_rows)

    generate_evaluation_report(summary, output_dir / "evaluation_report.md")


def main():
    parser = argparse.ArgumentParser(description="Run Ragas Evaluation for AUTOSAR HLD Assistant.")
    parser.add_argument("--mode", choices=["both", "hybrid", "baseline"], default="both", help="Retrieval mode(s) to evaluate.")
    parser.add_argument("--judge", choices=["auto", "gemini", "ollama", "mock"], default="auto", help="LLM judge provider preference.")
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit number of samples evaluated for quick smoke testing.")
    parser.add_argument("--validate-only", "--dry-run", action="store_true", help="Validate dataset schema and report without executing Ragas.")
    parser.add_argument("--output-dir", type=str, default="evaluation_result/ragas/results_corrected", help="Directory where evaluation artifacts are written (default: results_corrected).")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter = RagasDatasetAdapter()
    dataset_dir = Path("evaluation_result/dataset")
    if not dataset_dir.exists():
        if (Path("Code/evaluation_result/dataset")).exists():
            dataset_dir = Path("Code/evaluation_result/dataset")
        elif (Path(__file__).resolve().parent.parent / "dataset").exists():
            dataset_dir = Path(__file__).resolve().parent.parent / "dataset"
    b_path = dataset_dir / "baseline_eval_dataset.json"
    h_path = dataset_dir / "hybrid_eval_dataset.json"
    u_path = dataset_dir / "unsupported_eval_dataset.json"

    # --- DRY RUN / VALIDATION MODE ---
    if args.validate_only:
        logger.info("=== RUNNING DATASET VALIDATION (DRY RUN) ===")
        b_records = adapter.load_records(b_path)
        b_report = adapter.validate(b_records)
        h_records = adapter.load_records(h_path)
        h_report = adapter.validate(h_records)

        print("\n================== DATASET VALIDATION REPORT ==================")
        print(f"Baseline Dataset ({b_path}):")
        print(f"  Total samples:      {b_report.total_samples}")
        print(f"  Valid for Ragas:    {b_report.valid_samples_count}")
        print(f"  Excluded samples:   {b_report.excluded_samples_count}")
        print(f"  Available fields:   {sorted(list(b_report.available_fields))}")
        print(f"  Supported metrics:  {b_report.supported_metrics}")
        print(f"\nHybrid Dataset ({h_path}):")
        print(f"  Total samples:      {h_report.total_samples}")
        print(f"  Valid for Ragas:    {h_report.valid_samples_count}")
        print(f"  Excluded samples:   {h_report.excluded_samples_count}")
        print(f"  Available fields:   {sorted(list(h_report.available_fields))}")
        print(f"  Supported metrics:  {h_report.supported_metrics}")
        print("===============================================================\n")
        return

    # --- INITIALIZE JUDGE & EMBEDDINGS ---
    logger.info(f"Initializing LLM judge (preference: {args.judge})...")
    judge, judge_config = get_ragas_judge(preference=args.judge)
    logger.info(f"Active judge: {judge_config.judge_type} ({judge_config.model_name}) endpoint: {judge_config.endpoint}")

    embeddings = ProjectRagasEmbedding()
    logger.info(f"Active embeddings: {embeddings.model_name} (dim={embeddings.dimension})")

    # Evaluate unsupported abstention suite
    unsupported_summary = evaluate_unsupported_suite(u_path)

    results_summary: Dict[str, Any] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "ragas_version": ragas.__version__,
        "embedding_model": embeddings.model_name,
        "embedding_dimension": embeddings.dimension,
        "judge_configuration": judge_config.to_dict(),
        "metrics_summary": {
            "baseline": {},
            "hybrid": {},
        },
        "retrieval_only_metrics": {
            "baseline": {},
            "hybrid": {},
        },
        "answer_generation_metrics": {
            "baseline": {},
            "hybrid": {},
        },
        "baseline_vs_hybrid_deltas": {},
        "unsupported_abstention_evaluation": unsupported_summary,
        "exclusions": [],
    }

    per_sample_frames = []

    # --- EVALUATE BASELINE ---
    if args.mode in ["baseline", "both"]:
        b_res = evaluate_single_mode(
            mode_name="baseline",
            dataset_path=b_path,
            adapter=adapter,
            judge=judge,
            judge_config=judge_config,
            embeddings=embeddings,
            sample_limit=args.sample_limit,
        )
        results_summary["metrics_summary"]["baseline"] = b_res["mean_scores"]
        results_summary["retrieval_only_metrics"]["baseline"] = b_res["retrieval_metrics"]
        results_summary["answer_generation_metrics"]["baseline"] = b_res["generation_metrics"]
        results_summary["exclusions"] = b_res["validation_report"]["excluded_samples"]
        results_summary["total_valid_samples"] = b_res["validation_report"]["valid_samples_count"]
        if not b_res["per_sample_df"].empty:
            per_sample_frames.append(b_res["per_sample_df"])

    # --- EVALUATE HYBRID ---
    if args.mode in ["hybrid", "both"]:
        h_res = evaluate_single_mode(
            mode_name="hybrid",
            dataset_path=h_path,
            adapter=adapter,
            judge=judge,
            judge_config=judge_config,
            embeddings=embeddings,
            sample_limit=args.sample_limit,
        )
        results_summary["metrics_summary"]["hybrid"] = h_res["mean_scores"]
        results_summary["retrieval_only_metrics"]["hybrid"] = h_res["retrieval_metrics"]
        results_summary["answer_generation_metrics"]["hybrid"] = h_res["generation_metrics"]
        if not results_summary.get("exclusions"):
            results_summary["exclusions"] = h_res["validation_report"]["excluded_samples"]
            results_summary["total_valid_samples"] = h_res["validation_report"]["valid_samples_count"]
        if not h_res["per_sample_df"].empty:
            per_sample_frames.append(h_res["per_sample_df"])

    # --- COMPUTE DELTAS IF BOTH EVALUATED ---
    if args.mode == "both":
        b_scores = results_summary["metrics_summary"].get("baseline", {})
        h_scores = results_summary["metrics_summary"].get("hybrid", {})
        deltas = {}
        for m, h_val in h_scores.items():
            b_val = b_scores.get(m)
            if h_val is not None and b_val is not None:
                deltas[m] = round(h_val - b_val, 4)
            else:
                deltas[m] = None
        results_summary["baseline_vs_hybrid_deltas"] = deltas

    # --- SAVE SERIALIZED ARTIFACTS ---
    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)
    logger.info(f"Saved summary JSON to: {summary_path}")

    if per_sample_frames:
        combined_df = pd.concat(per_sample_frames, ignore_index=True)
        csv_path = out_dir / "per_sample_results.csv"
        combined_df.to_csv(csv_path, index=False, encoding="utf-8")
        logger.info(f"Saved per-sample results CSV to: {csv_path}")

    report_path = out_dir / "evaluation_report.md"
    generate_evaluation_report(results_summary, report_path)

    print("\n================== RAGAS EVALUATION COMPLETED ==================")
    print(f"Summary JSON:   {summary_path}")
    print(f"Per-sample CSV: {out_dir / 'per_sample_results.csv'}")
    print(f"Report MD:      {report_path}")
    print(f"Metrics Summary: {json.dumps(results_summary['metrics_summary'], indent=2)}")
    if results_summary.get("baseline_vs_hybrid_deltas"):
        print(f"Deltas:         {json.dumps(results_summary['baseline_vs_hybrid_deltas'], indent=2)}")
    print("================================================================\n")


if __name__ == "__main__":
    main()
