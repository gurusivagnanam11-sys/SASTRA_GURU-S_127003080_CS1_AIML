# Technical Model Configuration & Architecture Reference

## 1. Project Overview & Operational Purpose

- **Project Name**: AUTOSAR HLD Intelligence & Traceability Assistant
- **Primary Purpose**: An engineering-grade assistant designed for automotive software architects. It performs grounded question answering, cross-version traceability analysis (v1.0 vs v2.0), structural architecture consistency validation, and impact analysis over AUTOSAR High-Level Design (HLD) specifications.
- **Compliance Boundary**: Designed strictly as an engineering analysis and review-acceleration tool. It **does not claim** formal ISO 26262 functional safety compliance certification or official AUTOSAR Consortium approval. Human engineer review is mandatory for all architectural decisions.

---

## 2. LLM Provider & Generation Configuration

Configured in [`app/config.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/config.py) and instantiated via [`rag/llm_provider.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/llm_provider.py):

| Attribute | Local Default Setting | Cloud Development Path | Test / CI Setting |
| :--- | :--- | :--- | :--- |
| **Provider Name** | `ollama` (`OLLAMA_MODEL`) | `gemini` (`GEMINI_MODEL`) | `mock` (`MockLLMProvider`) |
| **Active Model** | `qwen2.5:3b` | `gemini-3.7-flash` | Deterministic context synthesis |
| **Endpoint / SDK** | `http://localhost:11434` (host)<br>`http://host.docker.internal:11434` (Docker) | Official `google-genai` SDK (`google.genai.Client`)<br>Fallback: `google.generativeai` | In-memory Python class |
| **503 Resiliency** | N/A | Auto-retries on `gemini-3.1-flash-lite` if 503 spike occurs | N/A |
| **Temperature** | `0.1` (`LLM_TEMPERATURE`) | `0.1` | Deterministic |
| **Max Tokens** | `2000` (`LLM_MAX_OUTPUT_TOKENS`) | `2000` (Docker default: `500` or `2048`) | Variable |
| **Timeout** | `180` seconds (`LLM_TIMEOUT_SECONDS`) | `180` seconds | Immediate |
| **Response Format** | `application/json` (enforced) | `application/json` (mime-type) | JSON string |

### Resolution Hierarchy in `get_llm_provider()`
1. Explicit function argument (`provider_name`)
2. Environment variable `LLM_PROVIDER`
3. Auto-detection if `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set → `GeminiProvider`
4. Safe fallback default → `OllamaProvider` (offline, local, zero API cost)

---

## 3. Embedding Model & Dimensionality

Configured in [`embeddings/embedder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/embeddings/embedder.py) and [`app/config.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/config.py):

- **Model Identifier**: `BAAI/bge-small-en-v1.5`
- **Embedding Framework**: `sentence-transformers` (`SentenceTransformer`)
- **Embedding Dimensions**: **384** (Verified via model initialization and dummy vector probe: `dummy_embed.shape[1] == 384`)
- **Vector Normalization**: L2 Unit Normalization (`||v|| = 1.0` via `embeddings / np.linalg.norm(...)`). Enables exact cosine similarity computation using standard dot-product matrix multiplication.
- **Inference Mode**: PyTorch CPU (`USE_TF="0"`, `USE_TORCH="1"`, `TF_ENABLE_ONEDNN_OPTS="0"`).
- **Offline Cache Control**: Set via `HF_HUB_OFFLINE="1"` to prevent unwanted outbound network calls during runtime query processing.

---

## 4. Vector Store Architecture & Persistence

Implemented in [`vectorstore/faiss_store.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/vectorstore/faiss_store.py) and [`vectorstore/metadata_store.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/vectorstore/metadata_store.py):

1. **FAISS Dense Index**:
   - **Index Type**: `faiss.IndexFlatIP` (Exact Inner Product on L2-normalized 384d vectors = Cosine Similarity)
   - **Persistence Path**: `data/indexes/hld_index.faiss`
   - **Search Complexity**: Exact exhaustive search (suitable for precision automotive document catalogs).
2. **Metadata Catalog Store**:
   - **Storage Format**: JSON catalog at `data/indexes/hld_metadata.json`
   - **Indexing Structure**: In-memory list mapping 0-indexed FAISS positions (`faiss_id`) to full chunk metadata objects.
3. **Relational Database**:
   - **Storage**: SQLite database at `data/autosar_hld.db` managed by [`db/repository.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/db/repository.py) (`HLDRepository`).
   - **Tables**: `documents`, `governance`, `engineering_reviews`.

---

## 5. Retrieval Architecture & Parameter Configurations

Implemented in [`rag/hybrid_retriever.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/hybrid_retriever.py) and [`rag/query_router.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/query_router.py):

The assistant provides two distinct retrieval engines:

### 5.1. Baseline Retriever (`BaselineRetriever`)
- **Strategy**: Pure dense semantic similarity via FAISS alone.
- **Candidate Pool**: `search_k = min(total_vectors, max(top_k * 5, 25))`
- **Filtering**: Filters on `project_id`, `chunk_type`, and `version` post-search.
- **Returned Top-K**: Configured `top_k` (default: 5).

### 5.2. Architecture-Aware Hybrid Retriever (`HybridRetriever` — Default)
- **Candidate Pool**: `candidate_pool_size = min(total_vectors, max(top_k * 20, 100))`
- **Multi-Signal Composite Scoring**:
  $$\text{Composite Score} = (0.50 \cdot S_{\text{semantic}} + 0.30 \cdot S_{\text{entity}} + 0.20 \cdot S_{\text{section}}) \times \text{Gov}_{\text{multiplier}}$$
  - **Semantic Score ($0.50$)**: Cosine similarity from FAISS distance bounded to $[0.0, 1.0]$.
  - **Entity Match Score ($0.30$)**: Exact match of software components, ports, signals, or interfaces detected by `QueryRouter`.
  - **Section Relevance Score ($0.20$)**: Section heuristics (e.g. Ports → Section 6.0, Signals → Section 5.0, Dependencies → Section 7.1, Interfaces → Section 4.0).
  - **Document Governance Multiplier**:
    - `APPROVED`: `1.0` (Full confidence)
    - `DRAFT`: `0.60` (Deprioritized)
    - `ARCHIVED`: `0.30` (Heavily penalized)
    - `Unreviewed / External`: `0.50`
- **Cross-Version Balancing**: For queries comparing releases across versions without explicit version filters, enforces balanced allocation of candidates across `v1.0` and `v2.0` (`max(2, top_k // 2)` per version) to prevent candidate starvation.
- **Comparative Completeness Check**: If evidence from either version is absent, the pipeline abstains before LLM invocation.

---

## 6. Document Chunking & Metadata Fields

Implemented in [`chunking/hld_chunker.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/chunking/hld_chunker.py):

- **Maximum Chunk Size**: `1500` characters (`CHUNK_MAX_CHARS`).
- **Splitting Strategy**: Logical blocks at paragraph and numbered heading boundaries; preserves table matrices (`TABLE: ...`).
- **Semantic Classification Types**:
  `component`, `interface`, `port`, `signal`, `dependency`, `flow`, `table`, `architecture`, `general`.
- **Entity Extraction**: Regex pattern matching for CamelCase entities (`VehicleControl`, `VehicleDataInterface`).
- **Complete Metadata Fields Recorded**:
  - `faiss_id`: Integer position in FAISS vector store
  - `chunk_id`: Standardized unique string (e.g. `autosar_hld__v2.0_p08_c34`)
  - `document_id`: Source file stem (e.g. `autosar_hld_v2.0`)
  - `project_id`: Project identifier (default: `demo_project`)
  - `version`: Specification release (`1.0`, `2.0`, or detected)
  - `page_number`: Integer 1-based page number
  - `section`: Section number (e.g. `7.1`)
  - `section_title`: Section heading (e.g. `Component Dependencies`)
  - `chunk_type`: Semantic architectural category
  - `entity_hint`: Prominent extracted architectural entity
  - `text`: Clean chunk content

---

## 7. Prompt Assets & Roles

| File | Live Code Source | Primary Role |
| :--- | :--- | :--- |
| [`prompts/system_prompt.md`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/Model_Prompts_Config/prompts/system_prompt.md) | `SYSTEM_PROMPT` in [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py) | 11 Critical Engineering Rules, JSON schema enforcement, prompt injection defense, cross-version claim separation. |
| [`prompts/user_prompt_template.md`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/Model_Prompts_Config/prompts/user_prompt_template.md) | `build_user_prompt` in [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py) | Injects question and structured chunk headers formatted by `ContextBuilder`. |
| [`prompts/grounding_prompt.md`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/Model_Prompts_Config/prompts/grounding_prompt.md) | [`rag/grounding_checker.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/grounding_checker.py) | Documents the **deterministic Python implementation** (citation verification, token support ratio >= 60%, signal data type contradiction checking). |

---

## 8. Grounding & Citation Validation Rules

- **Citation Verification**: Every claim must cite valid `chunk_id` values present in the retrieved candidate set. Fabricated or non-retrieved IDs are invalidated.
- **Token Support Ratio**: Requires $\ge 60\%$ content word overlap between the claim and the cited chunk text (excluding stopwords).
- **Cross-Version Alignment**: Prohibits claims about version 2.0 citing version 1.0 chunks.
- **Factual Contradiction Check**: Validates signal data types against cited table rows (e.g. preventing claiming `VehicleSpeed` is `float32` in version 2.0).

---

## 9. OCR Fallback & Architecture Validator

### 9.1. OCR Fallback (`ingestion/pdf_parser.py`)
- **Trigger**: Pages yielding `len(raw_text.strip()) < 50` characters.
- **Fallback Engine**: `pytesseract` + Pillow (`PIL.Image`) extracting rendered page pixmaps at 150 DPI.
- **Resilience**: If OCR binaries are not installed on the host system, logs a warning and gracefully preserves raw extracted text without crashing.

### 9.2. Architecture Consistency Validator (`analysis/architecture_validator.py`)
- **Execution Mode**: Dedicated endpoint (`GET /architecture/validate`) and Streamlit Explorer tab. **It is NOT executed on every general Q&A query.**
- **Scope**: Evaluates extracted `CompleteArchitectureModel` for 8 consistency categories:
  `UNDEFINED_REFERENCE`, `MISSING_REFERENCE`, `ORPHAN_ENTITY`, `INVALID_RELATIONSHIP`, `MISSING_MAPPING`, `INCOMPLETE_ENTITY`, `DUPLICATE_ENTITY`, `VERSION_INCONSISTENCY`.

---

## 10. Service Deployment & Communication

- **Backend API**: FastAPI on port `8000` (`app/main.py`), started via `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Frontend UI**: Streamlit on port `8501` (`app/streamlit_app.py`), started via `python scripts/run_ui.py --host 0.0.0.0 --port 8501`.
- **Service Networking**: In Docker, the UI connects to the API via `API_BASE_URL=http://hld-api:8000` over bridge network `hld-network`. On a local host, defaults to `http://localhost:8000`.

---

## 11. Docker & Local Execution Requirements

### Local Python Environment
- Python 3.10+ (tested on Python 3.12.3)
- Virtual environment at `.venv/`
- PyTorch CPU and Sentence-Transformers installed

### Docker Compose Environment
- `docker-compose.yml` configures two isolated containers: `hld-api` and `hld-ui`
- Volumes: `./data:/app/data` (persists indexes, SQLite database, processed models)
- Extra Hosts: `host.docker.internal:host-gateway` (allows containers to reach local Ollama on host)

---

## 12. Verified Test Commands & Results

| Test Target | Command | Result |
| :--- | :--- | :--- |
| **Ingestion, Chunking, FAISS** | `& .venv/Scripts/python.exe -m pytest tests/test_chunker.py tests/test_metadata.py tests/test_faiss.py -v` | **14 Passed** (4.24s) |
| **Retrieval Engine & Filters** | `& .venv/Scripts/python.exe -m pytest tests/test_retrieval.py -v` | **2 Passed** (29.30s) |
| **Cross-Version Grounding** | `& .venv/Scripts/python.exe -m pytest tests/test_vehiclespeed_cross_version.py -v` | **8 Passed** (31.72s) |
| **Retrieval & Validation Regression** | `& .venv/Scripts/python.exe -m pytest tests/test_validation_and_retrieval_fixes.py -v` | **13 Passed** (34.52s) |
| **Security & OCR Behavior** | `& .venv/Scripts/python.exe -m pytest tests/test_phase5_security.py tests/test_phase6.py -v` | **11 Passed** (38.68s) |
| **Architecture Consistency** | `& .venv/Scripts/python.exe -m pytest tests/test_phase7_validation.py -v` | **13 Passed** (0.28s) |
| **Reports & Governance Lifecycle** | `& .venv/Scripts/python.exe -m pytest tests/test_phase8_reports_governance.py -v` | **11 Passed** (40.38s) |
| **Comprehensive Functional Suite** | `& .venv/Scripts/python.exe -m pytest tests/test_phase2b.py tests/test_phase3.py tests/test_phase4.py tests/test_phase8_ingestion.py -v` | **95 Passed** (153.40s) |

---

## 13. Limitations & Engineering Governance

1. **Abstention Boundary**: Non-HLD questions regarding hardware registers, microcontroller part numbers, baud rates, or silicon errata trigger immediate grounded abstention.
2. **Review Gating**: Any answer with low similarity ($< 0.45$), invalid citations, ungrounded claims ($< 0.60$), or detected contradictions sets `review_required: true`.
3. **No Autonomous Certification**: Outputs are intended to assist human engineering peer reviews and traceability audits, not to substitute for formal engineering approval.