# AUTOSAR HLD Intelligence Assistant - Evaluation Results

This directory contains the verified benchmark results, RAGAS evaluation artifacts, and comparison reports for the **AUTOSAR High-Level Design (HLD) Intelligence & Traceability Assistant**.

---

## 1. Directory Structure

| File | Purpose | Active Evaluator / Methodology |
| :--- | :--- | :--- |
| [`baseline_vs_hybrid_comparison.md`](baseline_vs_hybrid_comparison.md) | Comprehensive comparative benchmark report between Baseline Dense (FAISS) and Architecture-Aware Hybrid (Dense + BM25 + RRF). | Verified benchmark results with itemized deltas. |
| [`retrieval_metrics.json`](retrieval_metrics.json) | Deterministic Information Retrieval (IR) metrics: Hit Rate@5, Recall@5, and Mean Reciprocal Rank (MRR). | Top-5 retrieved chunks vs. documented ground-truth chunk IDs. |
| [`ragas_summary.json`](ragas_summary.json) | Machine-readable RAGAS metric summary, execution metadata, judge configuration, and deltas. | Evaluator configuration logged (`judge_type`, `model`, timestamp). |
| [`per_sample_results.csv`](per_sample_results.csv) | Granular sample-by-sample scores across evaluated queries. | Per-query metric values and retrieval indices. |
| [`unsupported_query_abstention_report.json`](unsupported_query_abstention_report.json) | Abstention, confidence calibration, and review-required flagging for 10 adversarial/unsupported queries. | Real pipeline execution (`retriever_mode="baseline"` and `"hybrid"`). |
| [`test_execution_evidence.md`](test_execution_evidence.md) | Test suite verification evidence across unit tests, regression suites, and architecture validation. | Full test execution logs (43 tests passed). |

---

## 2. Evaluation Methodology & Metric Separation

To maintain rigorous scientific standards, evaluation metrics are strictly separated into three categories:

### 2.1 Retrieval-Only Metrics (Chunk ID Verification)
Evaluated directly on the top-5 retrieved chunks against documented HLD specification ground-truth chunk IDs:
- **Hit Rate@5:** Proportion of queries where at least one expected chunk ID was retrieved.
- **Recall@5:** Proportion of expected chunk IDs retrieved in the top 5 results.
- **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first relevant evidence chunk.

### 2.2 Answer Generation Metrics (RAGAS)
Evaluated across five generative dimensions:
- **Faithfulness:** Response consistency against retrieved context.
- **Answer Relevancy:** Relevance of generated answer to user prompt.
- **Context Precision:** Signal-to-noise ratio in retrieved context.
- **Context Recall:** Context completeness relative to reference answer.
- **Answer Correctness:** Factual and semantic alignment with reference answer.

### 2.3 Adversarial & Unsupported Query Abstention
Evaluated on 10 out-of-scope automotive queries (e.g., physical CAN baud rates, microcontroller clock speeds, brake hydraulic pressure curves) where the specification does not provide evidence:
- **Abstention Rate:** System states evidence is absent (100% achieved).
- **Confidence Calibration:** System assigns `confidence="low"` (100% achieved).
- **Review Required:** System flags `review_required=True` (100% achieved).
- **Unsupported Claims:** System avoids citing non-existent evidence (0 hallucinated claims).

---

## 3. Evaluator Transparency: Mock vs. Live Judge

> [!IMPORTANT]
> **Evaluator Mode Disclosure:**
> - **Smoke Tests & Schema Validation:** Use `--judge mock` (`OFFLINE_MOCK_JUDGE`). The mock judge verifies pipeline data-flow and Pydantic schemas. Its scores are clearly marked as offline/non-live and are never presented as genuine quality measurements.
> - **Live Quality Evaluation:** Uses `--judge ollama --model qwen2.5:3b` or approved cloud LLMs. Evaluator model, endpoint, valid sample counts, and any failed metric computations are logged. Evaluator failures or timeouts are recorded as `null` and are **never** substituted with default perfect (1.0) scores.

---

## 4. Key Verified Findings

| Metric | Baseline Dense (FAISS) | Architecture-Aware Hybrid | Delta ($\Delta$) | Impact |
| :--- | :---: | :---: | :---: | :---: |
| **Hit Rate@5** | 1.0000 | 1.0000 | 0.0000 | Parity |
| **Recall@5** | 0.5833 | 0.8333 | **+0.2500** | +25% evidence chunks captured |
| **MRR** | 0.7500 | 1.0000 | **+0.2500** | Primary definition placed at Rank 1 |
| **Abstention Rate** | 100% | 100% | 0.0000 | Zero hallucinations on unsupported queries |

---

## 5. Reproduction

Evaluation scripts and dataset builders are located in [`Code/evaluation_result/`](../Code/evaluation_result):

```powershell
# From the Code/ directory:
cd Code

# 1. Validate dataset schema (dry-run):
python evaluation_result/ragas/evaluate_ragas.py --validate-only

# 2. Smoke test with mock judge (verifies execution pipeline):
python evaluation_result/ragas/evaluate_ragas.py --sample-limit 2 --judge mock --output-dir evaluation_result/ragas/results_corrected

# 3. Live LLM judge evaluation (requires local Ollama running):
python evaluation_result/ragas/evaluate_ragas.py --mode both --judge ollama --model qwen2.5:3b --output-dir evaluation_result/ragas/results_corrected
```
