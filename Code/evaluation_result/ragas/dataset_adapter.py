"""Dataset adapter and schema validator for RAGAS evaluation.

Converts AUTOSAR HLD Assistant evaluation artifacts into Ragas-compatible
EvaluationDataset and SingleTurnSample schemas while validating required fields,
tracking exclusions with explicit reason codes, and preserving metadata.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import evaluation_result.ragas.compat  # noqa: F401

from datasets import Dataset
from ragas import EvaluationDataset, SingleTurnSample

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Detailed summary of dataset validation and field completeness."""
    total_samples: int = 0
    valid_samples_count: int = 0
    excluded_samples_count: int = 0
    excluded_samples: List[Dict[str, Any]] = field(default_factory=list)
    available_fields: Set[str] = field(default_factory=set)
    supported_metrics: List[str] = field(default_factory=list)
    unsupported_metrics: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "valid_samples_count": self.valid_samples_count,
            "excluded_samples_count": self.excluded_samples_count,
            "excluded_samples": self.excluded_samples,
            "available_fields": sorted(list(self.available_fields)),
            "supported_metrics": self.supported_metrics,
            "unsupported_metrics": self.unsupported_metrics,
        }


class RagasDatasetAdapter:
    """Adapts raw evaluation JSON / JSONL artifacts into Ragas EvaluationDataset."""

    REQUIRED_EVALUATION_FIELDS = {
        "user_input": ["user_input", "question", "query"],
        "retrieved_contexts": ["retrieved_contexts", "contexts"],
        "response": ["response", "answer"],
        "reference": ["reference", "ground_truth", "expected_answer"],
    }

    def __init__(self, exclude_adversarial: bool = True):
        self.exclude_adversarial = exclude_adversarial

    def load_records(self, source_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Load evaluation records from a JSON array or JSONL file."""
        path = Path(source_path)
        if not path.exists():
            candidate1 = Path(__file__).resolve().parent.parent / "dataset" / path.name
            candidate2 = Path("Code") / path
            if candidate1.exists():
                path = candidate1
            elif candidate2.exists():
                path = candidate2
            else:
                raise FileNotFoundError(f"Evaluation dataset path does not exist: {path}")

        records = []
        if path.suffix.lower() == ".jsonl":
            with open(path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        if isinstance(record, dict):
                            records.append(record)
                    except json.JSONDecodeError as exc:
                        logger.warning(f"Skipping malformed JSONL line {line_idx+1} in {path}: {exc}")
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    # Handle possible top-level wrappers
                    if "samples" in data and isinstance(data["samples"], list):
                        records = data["samples"]
                    elif "queries" in data and isinstance(data["queries"], list):
                        records = data["queries"]
                    else:
                        records = [data]
                else:
                    raise ValueError(f"Unexpected JSON data type in {path}: {type(data)}")

        return records

    def _resolve_field(self, record: Dict[str, Any], candidate_keys: List[str]) -> Optional[Any]:
        """Resolve a field value by checking multiple candidate keys in order."""
        for key in candidate_keys:
            if key in record and record[key] is not None:
                val = record[key]
                if isinstance(val, str) and not val.strip():
                    continue
                if isinstance(val, list) and not val:
                    continue
                return val
        return None

    def validate(self, records: List[Dict[str, Any]]) -> ValidationReport:
        """Validate input records and return field coverage and exclusion reasons."""
        report = ValidationReport(total_samples=len(records))

        seen_fields: Set[str] = set()
        valid_count = 0

        for idx, rec in enumerate(records):
            seen_fields.update(rec.keys())
            sample_id = rec.get("sample_id") or rec.get("query_id") or f"sample_{idx}"

            # Check if this is an explicit adversarial query
            if rec.get("is_unsupported") and self.exclude_adversarial:
                report.excluded_samples.append({
                    "sample_id": sample_id,
                    "reason": "UNSUPPORTED_ADVERSARIAL_QUERY",
                    "description": "Adversarial query designed for system abstention; lacks positive ground-truth evidence chunk context.",
                })
                continue

            # Check for required fields
            missing = []
            user_input = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["user_input"])
            if not user_input:
                missing.append("user_input")

            contexts = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["retrieved_contexts"])
            if not contexts or not isinstance(contexts, list):
                missing.append("retrieved_contexts")

            response = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["response"])
            if not response:
                missing.append("response")

            reference = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["reference"])
            if not reference:
                missing.append("reference")

            if missing:
                report.excluded_samples.append({
                    "sample_id": sample_id,
                    "reason": "MISSING_REQUIRED_FIELDS",
                    "missing_fields": missing,
                    "description": f"Record is missing required evaluation fields: {', '.join(missing)}",
                })
            else:
                valid_count += 1

        report.valid_samples_count = valid_count
        report.excluded_samples_count = len(report.excluded_samples)
        report.available_fields = seen_fields

        # Determine metric feasibility based on available fields in the valid subset
        if valid_count > 0:
            report.supported_metrics = [
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
                "answer_correctness",
            ]
        else:
            report.supported_metrics = []
            report.unsupported_metrics["all_metrics"] = "Zero valid samples available in dataset."

        return report

    def to_ragas_dataset(
        self,
        records: List[Dict[str, Any]],
        sample_limit: Optional[int] = None
    ) -> Tuple[EvaluationDataset, ValidationReport]:
        """Convert valid raw records into Ragas EvaluationDataset of SingleTurnSample items."""
        report = self.validate(records)
        samples: List[SingleTurnSample] = []

        for idx, rec in enumerate(records):
            if sample_limit is not None and len(samples) >= sample_limit:
                break

            sample_id = rec.get("sample_id") or rec.get("query_id") or f"sample_{idx}"
            if rec.get("is_unsupported") and self.exclude_adversarial:
                continue

            user_input = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["user_input"])
            contexts = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["retrieved_contexts"])
            response = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["response"])
            reference = self._resolve_field(rec, self.REQUIRED_EVALUATION_FIELDS["reference"])

            if not (user_input and contexts and response and reference):
                continue

            # Ensure contexts is a list of strings
            cleaned_contexts = [str(c) for c in contexts if str(c).strip()]
            if not cleaned_contexts:
                continue

            sample = SingleTurnSample(
                user_input=str(user_input),
                retrieved_contexts=cleaned_contexts,
                response=str(response),
                reference=str(reference),
                retrieved_context_ids=rec.get("retrieved_context_ids"),
                reference_context_ids=rec.get("reference_context_ids"),
            )
            samples.append(sample)

        ragas_ds = EvaluationDataset(samples=samples)
        return ragas_ds, report

    def to_hf_dataset(
        self,
        records: List[Dict[str, Any]],
        sample_limit: Optional[int] = None
    ) -> Tuple[Dataset, ValidationReport]:
        """Convert valid raw records into HuggingFace Dataset format."""
        ragas_ds, report = self.to_ragas_dataset(records, sample_limit=sample_limit)
        dict_data = {
            "user_input": [s.user_input for s in ragas_ds.samples],
            "retrieved_contexts": [s.retrieved_contexts for s in ragas_ds.samples],
            "response": [s.response for s in ragas_ds.samples],
            "reference": [s.reference for s in ragas_ds.samples],
        }
        return Dataset.from_dict(dict_data), report
