# Test Execution Evidence & Regression Verification

This document logs the test execution evidence across all automated test suites in the AUTOSAR HLD Intelligence & Traceability Assistant codebase.

---

## 1. Test Suite Summary

Execution Environment: Python 3.12.3, Pytest 9.1.1, Windows 11.
Total Tests Executed: **43**
Passed: **43**
Failed: **0**
Skipped: **0**

| Test Module | Test Count | Status | Scope |
| :--- | :---: | :---: | :--- |
| `tests/test_ragas_evaluation.py` | 15 | **PASSED** | RAGAS pipeline adapters, field validation, exclusion governance, IR metrics, mock judge schema, serialization. |
| `tests/test_validation_and_retrieval_fixes.py` | 13 | **PASSED** | Architecture validation diagnostics, interface extraction provenance, cross-version isolation, citation grounding. |
| `tests/test_architecture_regression.py` | 15 | **PASSED** | Architecture query routing, entity normalization, reciprocal rank fusion, JSON parser recovery and repair. |
| **Total** | **43** | **PASSED (100%)** | Full system regression and quality validation. |

---

## 2. Test Execution Details

### 2.1 RAGAS Evaluation Pipeline Unit Tests (`tests/test_ragas_evaluation.py`)
- `test_dataset_adapter_validation_valid_record`: PASSED
- `test_dataset_adapter_validation_missing_field`: PASSED
- `test_dataset_adapter_excludes_adversarial`: PASSED
- `test_dataset_adapter_load_and_filter`: PASSED
- `test_dataset_adapter_load_jsonl`: PASSED
- `test_dataset_adapter_to_ragas_evaluation_dataset`: PASSED
- `test_dataset_adapter_to_hf_dataset`: PASSED
- `test_complete_mock_judge_schema`: PASSED
- `test_get_ragas_judge_fallback`: PASSED
- `test_configure_metrics`: PASSED
- `test_save_evaluation_artifacts`: PASSED
- `test_dataset_construction_independence`: PASSED
- `test_unsupported_query_genuine_abstention_recording`: PASSED
- `test_compute_retrieval_only_metrics`: PASSED
- `test_unsupported_suite_evaluation`: PASSED

### 2.2 Validation & Retrieval Fixes (`tests/test_validation_and_retrieval_fixes.py`)
- `test_v1_architecture_validation_findings`: PASSED
- `test_v2_architecture_validation_findings`: PASSED
- `test_interface_extraction_provenance_accuracy`: PASSED
- `test_vehiclespeed_eval01_retrieval_all_versions`: PASSED
- `test_vehiclespeed_specific_version_isolation`: PASSED
- `test_governance_penalizes_draft_and_unapproved_documents`: PASSED
- `test_ground_truth_chunks_reflect_real_content`: PASSED
- `test_missing_and_non_retrieved_citations`: PASSED
- `test_valid_citation_does_not_mean_grounded_claim`: PASSED
- `test_vehiclecontrol_heading_and_metadata_grounding`: PASSED
- `test_cross_version_balanced_retrieval`: PASSED
- `test_cross_version_comparison_abstains_when_version_missing`: PASSED
- `test_true_false_evaluation_distinction`: PASSED

### 2.3 Architecture Regression Suite (`tests/test_architecture_regression.py`)
- `test_canonical_architecture_queries_routed_to_dependencies` (4 variants): PASSED
- `test_spaced_and_lowercase_entity_normalization`: PASSED
- `test_hyphenated_and_title_case_entity`: PASSED
- `test_dependency_evidence_retrieved_in_top_chunks` (4 variants): PASSED
- `test_governance_prioritizes_approved_hld_specifications`: PASSED
- `test_parses_clean_json`: PASSED
- `test_repairs_truncated_json`: PASSED
- `test_regex_recovery_from_unclosed_quotes`: PASSED
- `test_graceful_fallback_for_completely_invalid_output`: PASSED
