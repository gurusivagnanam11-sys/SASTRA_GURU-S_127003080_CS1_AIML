"""Unit tests for the RAGAS evaluation pipeline components.

Tests cover:
1. Dataset loading and format detection (JSON, JSONL).
2. Field schema validation and missing-field reporting.
3. Explicit exclusion governance for adversarial / unsupported queries.
4. Conversion to RAGAS EvaluationDataset and HuggingFace Dataset.
5. Mock judge schema conformity across RAGAS prompts.
6. Metric configuration and embedding dimension binding.
7. Serialization of evaluation summary JSON and per-sample CSV.
"""

import csv
import json
import pytest
from pathlib import Path

from evaluation_result.ragas.dataset_adapter import RagasDatasetAdapter
from evaluation_result.ragas.metrics_config import (
    CompleteMockJudge,
    ProjectRagasEmbedding,
    configure_and_get_metrics,
    get_ragas_judge,
)
from evaluation_result.ragas.evaluate_ragas import (
    save_evaluation_artifacts,
    generate_evaluation_report,
    compute_retrieval_only_metrics,
    evaluate_unsupported_suite,
)


@pytest.fixture
def sample_valid_record():
    return {
        "sample_id": "test_01",
        "query_id": "q01",
        "question": "What interface carries VehicleSpeed?",
        "user_input": "What interface carries VehicleSpeed?",
        "retrieved_contexts": [
            "Section 4.1 VehicleDataInterface: Signal VehicleSpeed float32 km/h"
        ],
        "response": "VehicleSpeed is carried by VehicleDataInterface.",
        "reference": "VehicleSpeed is carried by VehicleDataInterface between SensorManager and VehicleControl.",
        "is_unsupported": False,
        "retriever_mode": "hybrid",
    }


@pytest.fixture
def sample_adversarial_record():
    return {
        "sample_id": "test_adv_01",
        "query_id": "q_adv_01",
        "question": "Explain the LiDAR point cloud fusion pipeline.",
        "user_input": "Explain the LiDAR point cloud fusion pipeline.",
        "retrieved_contexts": [],
        "response": "No evidence found in AUTOSAR HLD.",
        "reference": "System should abstain.",
        "is_unsupported": True,
        "exclusion_reason": "UNSUPPORTED_ADVERSARIAL_QUERY",
        "retriever_mode": "hybrid",
    }


def test_dataset_adapter_validation_valid_record(sample_valid_record):
    adapter = RagasDatasetAdapter()
    report = adapter.validate([sample_valid_record])
    assert report.total_samples == 1
    assert report.valid_samples_count == 1
    assert report.excluded_samples_count == 0
    assert "faithfulness" in report.supported_metrics


def test_dataset_adapter_validation_missing_field():
    adapter = RagasDatasetAdapter()
    record = {
        "sample_id": "test_bad_01",
        "user_input": "What interface carries VehicleSpeed?",
        "retrieved_contexts": ["some context"],
        "reference": "Some ground truth",
    }
    report = adapter.validate([record])
    assert report.valid_samples_count == 0
    assert report.excluded_samples_count == 1
    assert report.excluded_samples[0]["reason"] == "MISSING_REQUIRED_FIELDS"
    assert "response" in report.excluded_samples[0]["missing_fields"]


def test_dataset_adapter_excludes_adversarial(sample_adversarial_record):
    adapter = RagasDatasetAdapter()
    report = adapter.validate([sample_adversarial_record])
    assert report.valid_samples_count == 0
    assert report.excluded_samples_count == 1
    assert report.excluded_samples[0]["reason"] == "UNSUPPORTED_ADVERSARIAL_QUERY"


def test_dataset_adapter_load_and_filter(tmp_path, sample_valid_record, sample_adversarial_record):
    dataset_file = tmp_path / "test_dataset.json"
    dataset_file.write_text(
        json.dumps([sample_valid_record, sample_adversarial_record]), encoding="utf-8"
    )

    adapter = RagasDatasetAdapter()
    records = adapter.load_records(dataset_file)
    assert len(records) == 2

    report = adapter.validate(records)
    assert report.total_samples == 2
    assert report.valid_samples_count == 1
    assert report.excluded_samples_count == 1
    assert report.excluded_samples[0]["sample_id"] == "test_adv_01"


def test_dataset_adapter_load_jsonl(tmp_path, sample_valid_record):
    jsonl_file = tmp_path / "test_dataset.jsonl"
    with open(jsonl_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(sample_valid_record) + "\n")

    adapter = RagasDatasetAdapter()
    records = adapter.load_records(jsonl_file)
    assert len(records) == 1
    report = adapter.validate(records)
    assert report.valid_samples_count == 1


def test_dataset_adapter_to_ragas_evaluation_dataset(sample_valid_record):
    adapter = RagasDatasetAdapter()
    eval_ds, report = adapter.to_ragas_dataset([sample_valid_record])

    assert len(eval_ds.samples) == 1
    sample = eval_ds.samples[0]
    assert sample.user_input == sample_valid_record["user_input"]
    assert sample.response == sample_valid_record["response"]
    assert sample.reference == sample_valid_record["reference"]
    assert sample.retrieved_contexts == sample_valid_record["retrieved_contexts"]


def test_dataset_adapter_to_hf_dataset(sample_valid_record):
    adapter = RagasDatasetAdapter()
    hf_ds, report = adapter.to_hf_dataset([sample_valid_record])

    assert len(hf_ds) == 1
    assert "user_input" in hf_ds.column_names
    assert "retrieved_contexts" in hf_ds.column_names
    assert "response" in hf_ds.column_names
    assert "reference" in hf_ds.column_names


def test_complete_mock_judge_schema():
    judge = CompleteMockJudge()

    # Faithfulness prompt
    res_f = judge.invoke("judge the faithfulness verdict as 1")
    parsed_f = json.loads(res_f.content)
    assert "statements" in parsed_f or "verdict" in parsed_f

    # Answer Relevancy prompt
    res_ar = judge.invoke("noncommittal response_relevance_prompt")
    parsed_ar = json.loads(res_ar.content)
    assert "question" in parsed_ar
    assert parsed_ar["noncommittal"] == 0

    # Context Precision prompt
    res_cp = judge.invoke("useful context_precision")
    parsed_cp = json.loads(res_cp.content)
    assert parsed_cp["verdict"] == 1

    # Context Recall prompt
    res_cr = judge.invoke("attributed context_recall_classification")
    parsed_cr = json.loads(res_cr.content)
    assert "classifications" in parsed_cr


def test_get_ragas_judge_fallback():
    judge_llm, config = get_ragas_judge(preference="mock")
    assert config.judge_type == "OFFLINE_MOCK_JUDGE"
    assert config.is_live is False
    assert config.warning is not None


def test_configure_metrics():
    judge_llm, _ = get_ragas_judge(preference="mock")
    ragas_emb = ProjectRagasEmbedding()
    metrics = configure_and_get_metrics(judge_llm, ragas_emb)

    assert len(metrics) == 5
    metric_names = [m.name for m in metrics]
    assert "faithfulness" in metric_names
    assert "answer_relevancy" in metric_names
    assert "context_precision" in metric_names
    assert "context_recall" in metric_names
    assert "answer_correctness" in metric_names
    assert ragas_emb._embedder.dimension == 384


def test_save_evaluation_artifacts(tmp_path):
    output_dir = tmp_path / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "timestamp": "2026-10-12 12:00:00 UTC",
        "ragas_version": "0.4.3",
        "judge_configuration": {
            "judge_type": "OFFLINE_MOCK_JUDGE",
            "model_name": "mock-judge-v1",
            "warning": "Deterministic offline test",
        },
        "metrics_summary": {
            "baseline": {"faithfulness": 1.0, "answer_relevancy": 0.95},
            "hybrid": {"faithfulness": 1.0, "answer_relevancy": 0.98},
        },
        "baseline_vs_hybrid_deltas": {"faithfulness": 0.0, "answer_relevancy": 0.03},
        "exclusions": [{"sample_id": "adv_01", "reason": "UNSUPPORTED_ADVERSARIAL_QUERY"}],
        "total_valid_samples": 1,
    }

    per_sample_rows = [
        {
            "user_input": "What interface carries VehicleSpeed?",
            "retrieved_contexts": "['context 1']",
            "response": "VehicleDataInterface",
            "reference": "VehicleDataInterface",
            "faithfulness": 1.0,
            "answer_relevancy": 0.95,
            "retriever_mode": "baseline",
            "sample_id": "test_01",
        }
    ]

    save_evaluation_artifacts(
        summary=summary,
        per_sample_rows=per_sample_rows,
        output_dir=output_dir,
        eval_baseline=True,
        eval_hybrid=True,
    )

    summary_file = output_dir / "summary.json"
    csv_file = output_dir / "per_sample_results.csv"
    report_file = output_dir / "evaluation_report.md"

    assert summary_file.exists()
    assert csv_file.exists()
    assert report_file.exists()

    loaded_summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert loaded_summary["ragas_version"] == "0.4.3"
    assert loaded_summary["total_valid_samples"] == 1

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 1
        assert reader[0]["sample_id"] == "test_01"
        assert float(reader[0]["faithfulness"]) == 1.0

    report_text = report_file.read_text(encoding="utf-8")
    assert "RAGAS Evaluation Report" in report_text
    assert "Macro-Average Scores" in report_text
    assert "Deterministic offline test" in report_text


def test_dataset_construction_independence():
    """Verify Baseline and Hybrid datasets contain genuine independent records."""
    adapter = RagasDatasetAdapter()
    b_records = adapter.load_records("evaluation_result/dataset/baseline_eval_dataset.json")
    h_records = adapter.load_records("evaluation_result/dataset/hybrid_eval_dataset.json")

    assert len(b_records) == 35
    assert len(h_records) == 35

    # Check grounded samples have genuine responses and preserve ground truth
    grounded_b = [r for r in b_records if not r.get("is_unsupported")]
    grounded_h = [r for r in h_records if not r.get("is_unsupported")]
    assert len(grounded_b) == 25
    assert len(grounded_h) == 25

    for b, h in zip(grounded_b, grounded_h):
        assert b["sample_id"] == h["sample_id"]
        assert b["question"] == h["question"]
        assert b["reference"] == h["reference"]
        assert b["reference_source"] == "AUTOSAR Ground Truth Specification Reference"
        assert len(b["reference_context_ids"]) > 0
        assert len(h["reference_context_ids"]) > 0
        assert len(b["response"]) > 0
        assert len(h["response"]) > 0


def test_unsupported_query_genuine_abstention_recording():
    """Verify unsupported queries recorded actual system abstention without fabricated text."""
    adapter = RagasDatasetAdapter()
    u_records = adapter.load_records("evaluation_result/dataset/unsupported_eval_dataset.json")
    assert len(u_records) == 10

    for item in u_records:
        b_rec = item.get("baseline", {})
        h_rec = item.get("hybrid", {})

        # Must record actual low confidence and review required
        assert b_rec.get("confidence") == "low"
        assert b_rec.get("review_required") is True
        assert h_rec.get("confidence") == "low"
        assert h_rec.get("review_required") is True

        # Must contain genuine pipeline abstention phrasing
        b_ans = b_rec.get("response", "").lower()
        h_ans = h_rec.get("response", "").lower()
        assert any(k in b_ans for k in ["does not specify", "insufficient evidence", "not defined", "unsupported"])
        assert any(k in h_ans for k in ["does not specify", "insufficient evidence", "not defined", "unsupported"])


def test_compute_retrieval_only_metrics():
    """Verify retrieval-only metrics compute Hit Rate@5, Recall@5, and MRR accurately."""
    sample_records = [
        {
            "retrieved_context_ids": ["chunk_01", "chunk_02", "chunk_03"],
            "reference_context_ids": ["chunk_01", "chunk_04"],
        },
        {
            "retrieved_context_ids": ["chunk_10", "chunk_11", "chunk_12"],
            "reference_context_ids": ["chunk_20"],
        },
    ]
    ir_metrics = compute_retrieval_only_metrics(sample_records)
    # First sample: hit=1.0, recall=0.5, mrr=1.0
    # Second sample: hit=0.0, recall=0.0, mrr=0.0
    assert ir_metrics["hit_rate_at_5"] == 0.5
    assert ir_metrics["recall_at_5"] == 0.25
    assert ir_metrics["mrr"] == 0.5


def test_unsupported_suite_evaluation(tmp_path):
    """Verify evaluate_unsupported_suite evaluates abstention rates accurately."""
    u_file = tmp_path / "unsupported_test.json"
    u_data = [
        {
            "query_id": "u01",
            "question": "What is the physical pinout?",
            "baseline": {
                "response": "The approved AUTOSAR HLD documents do not specify this parameter.",
                "confidence": "low",
                "review_required": True,
                "claims": [],
            },
            "hybrid": {
                "response": "The approved AUTOSAR HLD documents do not specify this parameter.",
                "confidence": "low",
                "review_required": True,
                "claims": [],
            },
        }
    ]
    u_file.write_text(json.dumps(u_data), encoding="utf-8")
    summary = evaluate_unsupported_suite(u_file)
    assert summary["total_unsupported_queries"] == 1
    assert summary["baseline_abstention_rate"] == 1.0
    assert summary["hybrid_abstention_rate"] == 1.0
    assert summary["hallucination_prevention_rate"] == 1.0
