# Grounding & Citation Validation Specification — AUTOSAR HLD Assistant

## 1. Grounding Architecture: Deterministic Python Implementation

> [!IMPORTANT]
> **Deterministic Python Grounding — No LLM Prompt Used**
> In the **AUTOSAR HLD Intelligence & Traceability Assistant**, grounding and citation verification are **implemented deterministically in Python**, rather than via an LLM evaluation prompt or LLM-as-a-judge call.

### Architectural Rationale
1. **Elimination of Self-Evaluation Bias**: LLM models frequently evaluate their own outputs leniently or hallucinate that an ungrounded claim was supported. Deterministic Python logic enforces strict mathematical verification.
2. **Deterministic Compliance Verification**: Automotive functional safety and traceability workflows require reproducible, auditable verification algorithms. A deterministic algorithm guarantees that identical inputs always yield identical grounding scores.
3. **Zero Additional Latency & Cost**: Evaluating grounding in pure Python avoids a secondary LLM round-trip, keeping local CPU inference responsive on resource-constrained development machines.
4. **Exact Metadata Binding**: Python directly queries the active in-memory [`MetadataStore`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/vectorstore/metadata_store.py) catalog to ensure that cited chunks, page numbers, sections, and document versions are genuine.

---

## 2. Core Grounding Modules & Verification Pipeline

The grounding verification architecture consists of two cooperating Python modules:

```
                  [Raw LLM JSON Response]
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │ 1. Citation Validation (rag/citation_validator.py)     │
  │    • Validates chunk_id exists in retrieved context    │
  │    • Resolves truncated or legacy chunk_id prefixes    │
  │    • Matches document_id, version, page, section with  │
  │      MetadataStore entries                             │
  │    • Flags invalid or fabricated citations             │
  └──────────────────────────┬─────────────────────────────┘
                             │ Validated Citations
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. Claim Grounding Verification                        │
  │    (rag/grounding_checker.py)                          │
  │    • Per-chunk Factual Contradiction Check             │
  │      (check_claim_contradictions: Signal Data Types)   │
  │    • Cross-Version Alignment Check                     │
  │      (prevents citing v1.0 chunks for v2.0 claims)     │
  │    • Alphanumeric Token Overlap Analysis               │
  │      (Requires >= 60% content word support ratio)      │
  └──────────────────────────┬─────────────────────────────┘
                             │ Checked Claims & Grounding Score
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. Confidence Rating & Review Gating                   │
  │    (rag/pipeline.py :: _evaluate_confidence_and_review)│
  │    • HIGH / MEDIUM / LOW confidence classification     │
  │    • review_required flag set to true if contradictions│
  │      found, citations invalid, or score < 0.85         │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Verification Mechanics

### 3.1. Citation Validation (`rag/citation_validator.py`)
- **Class**: `CitationValidator`
- **Method**: `validate_citations(citations: List[Citation], retrieved_chunks: List[ContextChunk], metadata_store: Optional[MetadataStore]) -> Tuple[List[Citation], bool, List[str]]`
- **Verification Criteria**:
  1. **Presence**: The cited `chunk_id` must match a chunk in the retrieved candidate pool (`retrieved_chunk_ids`).
  2. **Prefix Resolution**: If the LLM generates a slightly abbreviated prefix (e.g. `autosar_hld__v2.0_p08`), `resolve_chunk_id()` resolves it to the full ID (e.g. `autosar_hld__v2.0_p08_c34`) only if unambiguous.
  3. **Metadata Consistency**: If `MetadataStore` is supplied, the cited `document_id`, `version`, `page`, and `section` must match the catalog's indexed values. Discrepancies set `citation.valid = False` and log an issue.

### 3.2. Claim Grounding Verification (`rag/grounding_checker.py`)
- **Class**: `GroundingChecker`
- **Method**: `check_grounding(answer: str, claims: List[Claim], retrieved_chunks: List[ContextChunk]) -> Tuple[List[Claim], float, List[str]]`
- **Three-Stage Verification**:

#### A. Per-Chunk Factual Contradiction Detection
- **Function**: `check_claim_contradictions(claim_text: str, chunk: ContextChunk) -> Optional[str]`
- **Signal Type Binding**: `extract_signal_type_bindings(text)` extracts `(signal_name, data_type)` tuples using regex across known automotive types (`float32`, `float64`, `uint8`, `uint16`, `uint32`, `int8`, `int16`, `int32`, `boolean`, `bool`, `enum`, `struct`).
- **Contradiction Detection**: If a claim states that `VehicleSpeed` is `float32` in version 2.0, but cited chunk `autosar_hld__v2.0_p06_c28` binds `VehicleSpeed` to `float64`, the contradiction check fails:
  ```python
  return "Factual Contradiction: Claim asserts VehicleSpeed is float32 for version 2.0, but cited chunk defines float64."
  ```

#### B. Cross-Version Alignment Check
Verifies that claims referencing a specific HLD release do not cite chunks from an incompatible release:
- Claims referencing version 2.0 must cite `version == "2.0"` chunks.
- Claims referencing version 1.0 must cite `version == "1.0"` chunks.
- Cross-version claims (referencing both versions) must cite chunks from each respective version separately.

#### C. Token Support Ratio
1. Stopwords from `COMMON_STOPWORDS` (English syntax) and `REPORTING_STOPWORDS` (meta-discourse terms like "defined", "table", "section", "hld", "specifies") are filtered out.
2. Content words (alphanumeric tokens with length >= 3) are extracted.
3. Each token is evaluated with inflection handling (plurals, stems via `_token_matches_text()`).
4. **Support Threshold**: Requires **>= 60%** of content words to appear in the combined text of cited chunks. Claims below 60% support are marked `grounded = False`.

---

## 4. Confidence Rating & Human Review Gating

Defined in [`rag/pipeline.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/pipeline.py) (`_evaluate_confidence_and_review`):

| Rating | Conditions Required | Review Required Flag |
| :--- | :--- | :--- |
| **HIGH** | Max cosine similarity >= 0.60, all citations valid, grounding score >= 0.85, no factual contradictions, LLM `review_required == false`. | `review_required = false` |
| **MEDIUM** | Max similarity >= 0.45, all citations valid, grounding score >= 0.60. Represents cross-section synthesis or moderate similarity. | `review_required = true` (if grounding < 0.85) |
| **LOW** | Similarity < 0.45, any citation invalid, grounding score < 0.60, answer declares insufficient evidence, or factual contradiction detected. | `review_required = true` |

---

## 5. Verification Test Suite

The deterministic grounding engine is verified by comprehensive test suites in [`tests/`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/tests):

```powershell
# 1. Cross-version grounding and signal datatype contradiction tests (8 tests)
& .venv/Scripts/python.exe -m pytest tests/test_vehiclespeed_cross_version.py -v

# 2. Retrieval, citation, and regression grounding fixes (13 tests)
& .venv/Scripts/python.exe -m pytest tests/test_validation_and_retrieval_fixes.py -v

# 3. Citation validation and malformed citation tests
& .venv/Scripts/python.exe -m pytest tests/test_rag.py -k "citation" -v
```