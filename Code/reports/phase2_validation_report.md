# Phase 2 Validation & RAG Q&A Report: AUTOSAR HLD Document Analysis Assistant

**Project:** AUTOSAR HLD Intelligence & Traceability Assistant  
**Reference Case Study:** Case Study 1 — *AUTOSAR HLD Document Analysis Assistant*  
**Phase:** Phase 2 — Grounded RAG Question Answering  
**Status:** Complete & Validated  
**Validation Date:** 2026-10-05  

---

## 1. Executive Summary

Phase 2 builds directly upon the Phase 1 retrieval foundation (71 architecture-aware chunks, `BAAI/bge-small-en-v1.5` dense embeddings, and FAISS `IndexFlatIP` vector index) by implementing a robust, grounded Question Answering (RAG) layer.

The implementation strictly satisfies all Case Study 1 requirements:
- **Natural-Language Architecture Q&A**: Answers engineering questions grounded exclusively in retrieved HLD evidence.
- **Auditable Provenance & Citations**: Every claim is mapped to explicit document, version, page number, section, and chunk ID citations.
- **Deterministic Citation Validation**: Lightweight validator verifies that every cited chunk was actually retrieved and that document, page, and section metadata are consistent with the stored corpus.
- **Deterministic Grounding Verification**: Token/vocabulary support checker verifies that claims do not introduce unsupported entities or vocabulary absent from the cited evidence.
- **Evidence-Based Confidence & HITL Gating**: Application-level confidence ratings (`HIGH`, `MEDIUM`, `LOW`) with automatic human review flags (`review_required=True`) whenever evidence is weak, ungrounded, or missing.
- **Framework Independence**: Built using pure Python, Pydantic v2, and lightweight abstractions (No LangChain, No LlamaIndex).
- **Offline / CI Reliability**: Full credential-free execution support via `MockLLMProvider`, alongside production-ready `OpenAILLMProvider` and `GeminiLLMProvider`.
- **100% Test Pass Rate**: 51/51 tests passing (28 Phase 1 + 23 Phase 2).

---

## 2. Architecture & Pipeline Implementation

### 2.1 End-to-End Pipeline Flow

```text
                     USER QUESTION
                           │
                           ▼
                  rag.pipeline.ask()
                           │
                     [1. Validate]
                           │
                     [2. Embed Query] (HLDEmbedder)
                           │
                     [3. FAISS Retrieval] (FAISSStore)
                           │
                     [4. Metadata Filtering] (Version, Project, Chunk Type)
                           │
                     [5. Context Builder] (Preserves Provenance Headers)
                           │
                     [6. LLM Generation] (OpenAI / Gemini / Mock)
                           │
                     [7. Structured JSON Parsing] (Pydantic RAGResponse)
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
  [8. Citation Validator]     [9. Grounding Checker]
  - Verifies chunk exists     - Token support ratio
  - Checks page/section       - Unmatched term audit
             │                           │
             └─────────────┬─────────────┘
                           │
              [10. Confidence & Review Gating]
                           │
                           ▼
                    FINAL RAG RESPONSE
```

### 2.2 Core Modules Created

1. **`rag/models.py`**:
   - `RAGResponse`: Top-level structured response with `answer`, `claims`, `citations`, `confidence`, `limitations`, `review_required`, `grounding_score`.
   - `Citation`: Immutable provenance pointer (`document`, `version`, `page`, `section`, `chunk_id`, `valid`, `validation_notes`).
   - `Claim`: Factual statement linked to `citation_ids` and `grounded` flag.
   - `ContextChunk`: Prompt context chunk preserving full architectural metadata.
   - `ConfidenceLevel`: Application-level enum (`HIGH`, `MEDIUM`, `LOW`).

2. **`rag/context_builder.py`**:
   - Assembles raw retrieval tuples into structured `ContextChunk` items.
   - Formats evidence for the LLM prompt with explicit `--- EVIDENCE ITEM i ---` headers, chunk IDs, page numbers, and section titles so the LLM has exact provenance cues.

3. **`rag/prompts.py`**:
   - Enforces strict engineering assistant constraints: zero hallucinations, no autonomous architecture approvals, mandatory citations, explicit handling of unknown queries with `"Insufficient evidence in approved documents to support this query."`, and structured JSON mode.

4. **`rag/llm_provider.py`**:
   - `LLMProvider` (ABC): Defines the clean `generate(system_prompt, user_prompt, **kwargs)` interface.
   - `OpenAILLMProvider`: Supports OpenAI chat completions with `response_format={"type": "json_object"}`.
   - `GeminiLLMProvider`: Supports Google Gemini with JSON response schema.
   - `MockLLMProvider`: Context-aware deterministic synthesizer for testing and offline CLI execution.
   - `get_llm_provider()`: Factory auto-resolving providers from environment variables (`LLM_PROVIDER`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).

5. **`rag/citation_validator.py`**:
   - Validates each citation against retrieved chunks and the global metadata store.
   - Flags non-retrieved chunks or fabricated IDs (`valid=False`, `review_required=True`).
   - Checks page number, section, and version consistency.

6. **`rag/grounding_checker.py`**:
   - Analyzes claims against cited chunk text after removing common English stopwords.
   - Computes vocabulary support ratio and flags unsupported statements for human review.

7. **`rag/pipeline.py`**:
   - Main orchestrator with functional `ask()` entrypoint.
   - Integrates query validation, FAISS search, metadata filtering, synthesis, validation, and application-level confidence rating.

8. **`scripts/ask.py`**:
   - Command-line interface for interactive engineer queries with `--version`, `--project`, `--provider`, and `--json` flags.

---

## 3. Evaluation on Canonical Phase 1 Queries

The five canonical queries from Phase 1 were evaluated using `scripts/ask.py`:

### Canonical Query 1: "What components are associated with VehicleControl?"
- **Answer:** `VehicleControl is associated with SensorManager, DiagnosticManager, and SafetyManager through component dependencies. VehicleControl depends on SensorManager for sensor data input and DiagnosticManager for health monitoring.`
- **Top Evidence:** `autosar_hld__v2.0_p08_c34` (Page 8, Section 7.1 Component Dependencies)
- **Citation Status:** `[VALID]` (Verified against retrieved HLD evidence)
- **Confidence:** `High`
- **Review Required:** `False`

### Canonical Query 2: "What interface carries VehicleSpeed?"
- **Answer:** `VehicleSpeed is carried by VehicleDataInterface (a Sender-Receiver interface between SensorManager and consuming components).`
- **Top Evidence:** `autosar_hld__v1.0_p06_c23` / `autosar_hld__v2.0_p06_c25` (Page 6, Section 4.1 VehicleDataInterface)
- **Citation Status:** `[VALID]` (Verified against retrieved HLD evidence)
- **Confidence:** `High`
- **Review Required:** `False`

### Canonical Query 3: "What ports belong to VehicleControl?"
- **Answer:** `VehicleControl contains input ports such as VehicleSpeedIn and EngineRPMIn, and output ports ControlCommandOut and VehicleStateOut.`
- **Top Evidence:** `autosar_hld__v1.0_p07_c28` / `autosar_hld__v2.0_p07_c31` (Page 7, Section 6 Port Definitions)
- **Citation Status:** `[VALID]` (Verified against retrieved HLD evidence)
- **Confidence:** `High`
- **Review Required:** `False`

### Canonical Query 4: "What signals are consumed by VehicleControl?"
- **Answer:** `VehicleControl consumes the VehicleSpeed signal from SensorManager.`
- **Top Evidence:** `autosar_hld__v1.0_p06_c23` (Page 6, Section 4.1 Signals Table)
- **Citation Status:** `[VALID]` (Verified against retrieved HLD evidence)
- **Confidence:** `High`
- **Review Required:** `False`

### Canonical Query 5: "What changed between version 1.0 and version 2.0?"
- **Answer:** `Between version 1.0 and version 2.0, Section 2.2 Component Overview shows that the system consists of four primary software components in version 1.0, while expanding to five primary software components in version 2.0 with the addition of SafetyManager.`
- **Top Evidence:** `autosar_hld__v1.0_p03_c09` (v1.0 Section 2.2) and `autosar_hld__v2.0_p03_c09` (v2.0 Section 2.2)
- **Citation Status:** `[VALID]` across both versions
- **Confidence:** `Medium` (synthesizing across document versions)
- **Review Required:** `False`

---

## 4. Citation Validation & Grounding Examples

### 4.1 Valid Citation Example
```json
{
  "document": "autosar_hld_v2.0",
  "version": "2.0",
  "page": 6,
  "section": "4.1",
  "chunk_id": "autosar_hld__v2.0_p06_c24",
  "valid": true,
  "validation_notes": "Verified against retrieved HLD evidence."
}
```

### 4.2 Fabricated / Missing Citation Example
When a fabricated chunk ID (`fabricated_chunk_id_999`) is introduced:
- **Validator Output:** `valid = False`
- **Validation Note:** `"Citation references unknown or fabricated chunk_id 'fabricated_chunk_id_999'."`
- **System Action:** `review_required = True`, warning appended to limitations.

### 4.3 Metadata Discrepancy Example
When a chunk ID is retrieved on Page 6, but the LLM claims Page 10:
- **Validator Output:** `valid = False`
- **Validation Note:** `"Metadata discrepancy for chunk '...': page mismatch (cited: 10, actual: 6)"`
- **System Action:** `review_required = True`, discrepancy logged.

### 4.4 Unsupported Claim Example
When a claim mentions entities completely absent from the cited chunk:
- **Checker Output:** `grounded = False`, `grounding_score < 0.60`
- **Warning:** `"Claim has low textual support (0%) in cited chunks: unmatched terms: [...]"`
- **System Action:** `confidence = Low`, `review_required = True`.

---

## 5. Test Suite Verification

### 5.1 Test Execution Command
```bash
pytest tests/ -v
```

### 5.2 Test Results
```text
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-8.3.2, pluggy-1.6.0
rootdir: C:\Users\guru2\Downloads\techpulsde\autosar_hld_assistant
collected 51 items

tests/test_chunker.py::test_chunk_document_returns_chunks PASSED         [  1%]
tests/test_chunker.py::test_at_least_10_chunks_generated PASSED          [  3%]
tests/test_chunker.py::test_all_chunk_ids_unique PASSED                  [  5%]
tests/test_chunker.py::test_chunk_metadata_present PASSED                [  7%]
tests/test_chunker.py::test_chunk_types_include_architecture_types PASSED [  9%]
tests/test_chunker.py::test_section_and_entity_hints PASSED              [ 11%]
tests/test_embeddings.py::test_embedder_initializes PASSED               [ 13%]
tests/test_embeddings.py::test_embed_documents PASSED                    [ 15%]
tests/test_embeddings.py::test_embed_query PASSED                        [ 17%]
tests/test_embeddings.py::test_empty_input PASSED                        [ 19%]
tests/test_faiss.py::test_faiss_store_build_and_count PASSED             [ 21%]
tests/test_faiss.py::test_faiss_search PASSED                            [ 23%]
tests/test_faiss.py::test_save_and_load_roundtrip PASSED                 [ 25%]
tests/test_faiss.py::test_validate PASSED                                [ 27%]
tests/test_faiss.py::test_dimension_mismatch PASSED                      [ 29%]
tests/test_metadata.py::test_generate_document_id PASSED                 [ 31%]
tests/test_metadata.py::test_document_metadata_fields PASSED             [ 33%]
tests/test_metadata.py::test_save_and_load_processed_document PASSED     [ 35%]
tests/test_parser.py::test_parse_pdf_returns_document_data PASSED        [ 37%]
tests/test_parser.py::test_page_count_greater_than_zero PASSED           [ 39%]
tests/test_parser.py::test_page_numbers_are_one_indexed PASSED           [ 41%]
tests/test_parser.py::test_pages_have_non_empty_raw_text PASSED          [ 43%]
tests/test_parser.py::test_document_id_and_version_set PASSED            [ 45%]
tests/test_parser.py::test_headings_detected PASSED                      [ 47%]
tests/test_parser.py::test_text_contains_autosar_keywords PASSED         [ 49%]
tests/test_parser.py::test_missing_file_raises_error PASSED              [ 50%]
tests/test_rag.py::test_query_embedding_integration PASSED               [ 52%]
tests/test_rag.py::test_retrieval_integration PASSED                     [ 54%]
tests/test_rag.py::test_context_construction PASSED                      [ 56%]
tests/test_rag.py::test_empty_context_construction PASSED                [ 58%]
tests/test_rag.py::test_metadata_preservation PASSED                     [ 60%]
tests/test_rag.py::test_parse_clean_json PASSED                          [ 62%]
tests/test_rag.py::test_parse_markdown_wrapped_json PASSED               [ 64%]
tests/test_rag.py::test_parse_malformed_json_fallback PASSED             [ 66%]
tests/test_rag.py::test_citation_validation_valid PASSED                 [ 68%]
tests/test_rag.py::test_missing_citation_in_claim PASSED                 [ 70%]
tests/test_rag.py::test_invalid_citation_nonexistent_chunk PASSED        [ 72%]
tests/test_rag.py::test_invalid_citation_metadata_discrepancy PASSED     [ 74%]
tests/test_rag.py::test_insufficient_evidence_when_filtered_out PASSED   [ 76%]
tests/test_rag.py::test_empty_query_handling PASSED                      [ 78%]
tests/test_rag.py::test_metadata_filtering_version PASSED                [ 80%]
tests/test_rag.py::test_canonical_query_1_components PASSED              [ 82%]
tests/test_rag.py::test_canonical_query_2_interface PASSED               [ 84%]
tests/test_rag.py::test_canonical_query_3_ports PASSED                   [ 86%]
tests/test_rag.py::test_canonical_query_4_signals PASSED                 [ 88%]
tests/test_rag.py::test_canonical_query_5_version_delta PASSED           [ 90%]
tests/test_rag.py::test_llm_provider_factory PASSED                      [ 92%]
tests/test_rag.py::test_openai_provider_missing_key_raises PASSED        [ 94%]
tests/test_rag.py::test_pipeline_llm_failure_handled PASSED              [ 96%]
tests/test_retrieval.py::test_retrieval_pipeline PASSED                  [ 98%]
tests/test_retrieval.py::test_metadata_filter PASSED                     [100%]

======================= 51 passed, 3 warnings in 50.58s =======================
```

**Total Pass Rate:** 51 passed / 51 total (100%).

---

## 6. Definition of Done (DoD) Checklist

| DoD Criterion | Status | Verification Evidence |
| :--- | :---: | :--- |
| Existing Phase 1 tests still pass | **DONE** | All 28 Phase 1 tests pass untouched. |
| Query embedding uses existing embedder | **DONE** | Uses `HLDEmbedder` from Phase 1. |
| Retrieval uses existing FAISS index | **DONE** | Uses `FAISSStore` and `MetadataStore` from Phase 1. |
| Retrieved provenance is preserved | **DONE** | `ContextChunk` retains `chunk_id`, `version`, `page`, `section`, `entity_hint`. |
| Context builder works | **DONE** | `ContextBuilder.build_context()` & `format_context_for_prompt()`. |
| LLM provider abstraction exists | **DONE** | `LLMProvider` ABC with OpenAI, Gemini, and Mock implementations. |
| RAG prompt exists | **DONE** | `rag/prompts.py` enforces grounding and JSON output. |
| Structured response schema exists | **DONE** | `RAGResponse`, `Citation`, `Claim` models via Pydantic v2. |
| Citations are returned | **DONE** | Every claim links to valid citations. |
| Citations are deterministically validated | **DONE** | `CitationValidator` checks existence and metadata consistency. |
| Insufficient evidence is handled | **DONE** | Returns low confidence, `review_required=True`, explicit message. |
| Confidence/limitations are returned | **DONE** | Evaluated on evidence quality (`HIGH`, `MEDIUM`, `LOW`). |
| Mocked end-to-end RAG tests pass | **DONE** | Canonical queries 1–5 pass in `test_rag.py`. |
| CLI query flow works | **DONE** | `python scripts/ask.py` verified with multiple flags. |
| Documentation is updated | **DONE** | `README.md`, `AGENTS.md`, and this report synchronized. |
| No secrets committed | **DONE** | Zero API keys or sensitive files committed. |
| No Phase 3/4 scope creep | **DONE** | Stopped cleanly before UI, Neo4j, or revision engine. |

---

## 7. Known Limitations & Grounding Notes

1. **Lightweight Token Matching in Grounding Checker:**
   - The grounding checker currently uses token-level and vocabulary overlap filtering against stopwords. While highly effective at catching hallucinated entity names, complex paraphrasing may trigger review flags.
2. **Offline Embedder Hub Caching:**
   - The embedder is configured to default to local caching (`HF_HUB_OFFLINE=1`) to prevent SSL timeouts in restricted environments. Setting `HF_HUB_ONLINE=1` allows fresh model downloads if required.
3. **Cross-Version Diffing Scope:**
   - Cross-version queries currently synthesize retrieved overviews. Comprehensive tabular diffing across every port and signal belongs to the Phase 6 revision comparison engine.

---

## 8. Exact Phase 3 Starting Point

Phase 2 is fully complete. The repository is ready for **Phase 3: Architecture Entity Extraction**:
- **Target:** Extract structured AUTOSAR Software Components (SWCs), Ports (P-Ports, R-Ports), Interfaces (Sender-Receiver, Client-Server), and Signals into relational database models (`db/models.py`).
- **Input:** The existing 71 ingested chunks and parsed text in `data/processed/`.
- **Outcome:** Populated relational entity tables with provenance pointers linking back to exact chunk and page IDs.
