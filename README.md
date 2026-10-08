# AUTOSAR HLD Intelligence & Traceability Assistant

Production-grade engineering assistant for AUTOSAR High-Level Design (HLD) specifications, providing architecture-aware chunking, dense vector retrieval, grounded RAG question answering, citation verification, architecture entity extraction, and audit review workflows.

Based on **Case Study 1: AUTOSAR HLD Document Analysis Assistant**.

---

## 1. System Architecture

```
┌─────────────────────────────────┐
│     HLD PDF Specifications      │ (AUTOSAR HLD v1.0 & v2.0)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Document Ingestion Engine   │ (PyMuPDF / fitz, section tracking)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Architecture-Aware Chunker    │ (71 chunks: SWC, Port, Interface, Signal)
└────────┬───────────────┬────────┘
         │               │
         ▼               ▼
┌─────────────────┐ ┌─────────────────┐
│  HLDEmbedder    │ │ HLDRepository   │
│ (BGE-small /    │ │ (SQLite DB +    │
│  Torch 384-dim) │ │  Review Table)  │
└────────┬────────┘ └─────────────────┘
         │
         ▼
┌─────────────────┐ ┌─────────────────┐
│ FAISS IndexFlatIP│ │ Metadata Store  │
│ (Normalized IP) │ │ (JSON Provenance│
└────────┬────────┘ └────────┬────────┘
         │                   │
         └─────────┬─────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│             LangChain & RAG Orchestration              │
│ (HLDRetriever + ChatPromptTemplate + Provenance Docs) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   LLM Provider Tier                    │
│ 1. PRIMARY/PRIVATE: Local Ollama (qwen3:4b, on-prem)   │
│ 2. DEV/DEMO: Google Gemini Free Tier (Cloud API)       │
│ 3. TEST/CI: MockLLMProvider (Deterministic offline)    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│         Verification, Grounding & Review Gate          │
│ • CitationValidator ([VALID] vs [UNVERIFIED])         │
│ • GroundingChecker (Token overlap & claim grounding)   │
│ • Review Gating (Application-level confidence)         │
│ • SQLite Engineer Review Audit Log                     │
└──────────────────────────┬─────────────────────────────┘
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│       FastAPI REST Service      │ │       Streamlit Pilot UI        │
│  (/health, /query, /review,     │ │ (Q&A Console, Evidence Viewer,  │
│   /entities/components, etc.)   │ │  Entity Explorer, Audit Log)    │
└─────────────────────────────────┘ └─────────────────────────────────┘
```

---

## 2. LLM Provider Hierarchy & Deployment Modes

The assistant enforces a strict **free-tier / free-only** policy with no mandatory paid API dependencies:

| Tier | Provider | Model | Deployment & Privacy Classification | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **PRIMARY / PRIVATE** | **Local Ollama** | `qwen3:4b` | **Local / On-Premises**. Runs 100% locally via Ollama daemon (`http://localhost:11434`). Zero cloud egress, fully private. | Production engineering queries requiring strict IP protection. |
| **DEVELOPMENT / DEMO** | **Google Gemini Free Tier** | `gemini-3.7-flash` | **External Cloud API**. Uses Google GenAI free tier. Requires internet connection and free Google API key. *(Not local/private)*. | Rapid prototyping, cloud testing, and development validation. |
| **TESTING / CI** | **MockLLMProvider** | Deterministic | **In-Memory / Offline**. Zero network calls, zero external credentials. | Automated unit/integration tests and CI/CD pipelines. |

> [!IMPORTANT]
> **Privacy Note:** Google Gemini is an external cloud service. Do not send proprietary or classified automotive specifications to Gemini. Local Ollama (`qwen3:4b`) must be used for private, on-premises execution.

---

## 3. Grounded Semantic Q&A vs. Deterministic Revision Diff Engine

The assistant provides two complementary intelligence tiers:

1. **Semantic RAG Q&A Tier (Phase 2 & 2B):**
   - Natural language Q&A with citations, claims validation, and human-in-the-loop review.
   - Ideal for conceptual queries (e.g. *"What components are associated with VehicleControl?"*, *"What interface carries VehicleSpeed?"*).
   - Handles Canonical Query #5 (*"What changed between version 1.0 and version 2.0?"*) via semantic retrieval over overview chunks (Section 2.2).

2. **Deterministic Structural Revision Diff & Impact Engine (Phase 3):**
   - Extracts strongly-typed architecture entities (**Components, Interfaces, Ports, Signals, Dependencies, and Functional Flows**) into a consolidated graph model.
   - Detects **100% (7/7)** intentional architectural modifications across synthetic HLD fixtures without LLM hallucination:
     1. **Component Added:** `SafetyManager` (ISO 26262 ASIL-D functional safety)
     2. **Signal Data Type Change:** `VehicleSpeed` (`float32` $\rightarrow$ `float64`)
     3. **Signal Added:** `EngineTemperature` (`float32` added to `VehicleDataInterface`)
     4. **Port Added:** `SafetyStatusIn` (Input port added to `VehicleControl`)
     5. **Interface Added:** `SafetyMonitorInterface` (Client-Server)
     6. **Interface Renamed:** `CommunicationInterface` $\rightarrow$ `V2XCommunicationInterface`
     7. **Dependency Added:** `VehicleControl` $\rightarrow$ `SafetyManager` (Safety override coupling)
   - Propagates impact across graph relationships (`CONTAINS`, `CONNECTS_TO`, `CARRIES`, `DEPENDS_ON`, `PROVIDES`, `REQUIRES`) to assess RTE buffer memory alignment and functional safety implications.

---

## 4. Directory Structure

```
autosar_hld_assistant/
├── analysis/                  # Phase 3 Deterministic Analysis
│   ├── __init__.py
│   ├── revision_diff.py       # Deterministic structural diff engine (7/7 intentional detection)
│   └── impact_analysis.py     # Graph-based architectural impact & risk propagation
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment configuration & model paths
│   ├── logging_config.py      # Structured logging setup
│   ├── main.py                # FastAPI REST API service (11 architecture endpoints)
│   └── streamlit_app.py       # Streamlit Web UI (Multi-view Architecture Explorer)
├── chunking/
│   ├── __init__.py
│   ├── models.py              # HLDChunk dataclass with full provenance
│   └── hld_chunker.py         # Architecture-aware chunking heuristics
├── db/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models (Document, Version, Chunk, ReviewRecord)
│   └── repository.py          # Database operations & review persistence
├── embeddings/
│   ├── __init__.py
│   └── embedder.py            # BAAI/bge-small-en-v1.5 lazy-loading embedder
├── extraction/
│   ├── __init__.py
│   ├── models.py              # Pydantic models (SWCs, Ports, Signals, Graph, Diffs)
│   └── basic_extractor.py     # Architecture entity extractor with provenance
├── fixtures/
│   ├── generate_fixtures.py   # Synthetic AUTOSAR HLD PDF generator
│   ├── v1/                    # Generated v1.0 PDF
│   └── v2/                    # Generated v2.0 PDF
├── ingestion/
│   ├── __init__.py
│   ├── models.py              # PageData, DocumentData, DocumentMetadata
│   ├── pdf_parser.py          # PyMuPDF-based structure-aware parser
│   └── metadata.py            # Metadata extraction and persistence
├── rag/
│   ├── __init__.py            # Exported symbols (ask, RAGPipeline, models)
│   ├── models.py              # Schemas (RAGResponse, Citation, Claim, ContextChunk)
│   ├── context_builder.py     # Context builder maintaining evidence blocks
│   ├── prompts.py             # System & user prompts enforcing grounding & JSON
│   ├── llm_provider.py        # OllamaProvider, GeminiProvider, MockLLMProvider
│   ├── langchain_rag.py       # LangChain Document conversion, HLDRetriever, LCEL chain
│   ├── export.py              # Structured JSON and Markdown export utilities
│   ├── citation_validator.py  # Deterministic citation verifier against metadata
│   ├── grounding_checker.py   # Claim-to-evidence vocabulary support checker
│   └── pipeline.py            # End-to-end RAG orchestrator & ask() API
├── reports/
│   ├── phase1_validation_report.md
│   ├── phase2_validation_report.md
│   ├── phase2b_validation_report.md
│   ├── phase3_validation_report.md
│   ├── phase4_evaluation_report.md
│   ├── phase5_security_hardening.md
│   ├── phase7_architecture_validation.md
│   ├── phase8_engineering_reports_governance.md
│   ├── models.py              # Phase 8 Pydantic models for reports and governance
│   ├── generator.py           # Phase 8 report generation logic
│   └── export.py              # Phase 8 JSON/Markdown/CSV exporters
├── scripts/
│   ├── ingest_document.py     # Document ingestion script
│   ├── build_index.py         # FAISS index builder
│   ├── test_retrieval.py      # Retrieval verification script
│   ├── ask.py                 # Grounded RAG Q&A CLI interface
│   └── run_ui.py              # Streamlit Web UI launcher script
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_metadata.py
│   ├── test_chunker.py
│   ├── test_embeddings.py
│   ├── test_faiss.py
│   ├── test_retrieval.py
│   ├── test_rag.py
│   ├── test_phase2b.py        # Free providers, LangChain, FastAPI, extraction, export
│   ├── test_phase3.py         # Architecture models, Graph, 7/7 Diff, Impact, API
│   ├── test_phase4.py         # Advanced RAG evaluation, metrics, benchmarking
│   ├── test_phase5_security.py # Production security, path traversal, prompt injection
│   ├── test_phase6_ocr_tables.py # OCR, table extraction, table-aware chunking
│   ├── test_phase7_validation.py # Architecture validation rules
│   └── test_phase8_reports_governance.py # Engineering reports, governance, reviews
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. OCR & Table Extraction (Phase 6)

### OCR Support
The application includes local Optical Character Recognition (OCR) to handle scanned documents or image-only PDF pages:
- **Normal extraction preferred:** Standard PDFs use native text extraction, which is extremely fast and accurate.
- **Fallback OCR:** If a page contains insufficient text (e.g., scanned schematics or image-only pages), the local OCR fallback is automatically triggered.
- **Provenance preserved:** OCR-extracted text is explicitly tagged with `extraction_method="ocr"` to preserve evidence provenance through to the final citation.
- **Local Dependency:** OCR relies on `pytesseract`. To utilize OCR, you must install Tesseract OCR on your local machine and ensure the `tesseract` executable is in your system's PATH. If not installed, the application fails gracefully and skips OCR.

### Table Extraction
Engineering documents heavily utilize tables for Ports, Signals, and Interfaces. The system now natively supports table extraction:
- **Structure preservation:** Engineering tables are extracted while retaining row and column structures natively.
- **Deterministic representations:** Extracted tables are converted into structured text formats that can be embedded efficiently by FAISS.
- **Table-aware RAG:** Tables become first-class retrievable evidence for Q&A, allowing precise querying of interfaces and signal directions.
- **Citation accuracy:** Citations generated from table evidence explicitly retain page and table provenance.

---

## 6. Architecture Validation (Phase 7)

### Deterministic Validation Engine
The assistant provides a strict structural validation engine to analyze extracted models for inconsistencies and completeness. This does NOT replace formal AUTOSAR governance but provides robust engineering assistance during architecture reviews.

- **Inconsistency & Reference Checks:** Detects undefined component, interface, and signal references across dependencies, ports, and functional flows.
- **Completeness & Orphan Detection:** Identifies isolated or "orphan" components, interfaces, and signals to flag potentially incomplete definitions.
- **Dependency Validation:** Ensures source and target components for architectural dependencies are well-defined.
- **Duplicate Detection:** Scans for identical definitions of components, interfaces, or signals.
- **Version-Aware & Provenance Preserving:** Validation strictly operates on the selected document version. Finding reports include full provenance (document, version, page, and section) to allow direct auditing.

---

## 7. Engineering Reports & Governance (Phase 8)

### Structured Reports and Audit Trails
Phase 8 upgrades the system into an enterprise-grade traceability platform supporting formal workflows:

- **Source Governance:** Tracks document statuses (`APPROVED`, `DRAFT`, `ARCHIVED`) directly impacting downstream extraction. The active architecture defaults to the highest `APPROVED` version.
- **Enhanced Engineering Review:** Human-in-the-loop workflows allowing engineers to review, accept, correct, or reject specific report findings with full auditing.
- **Comprehensive Reports:** Standardized `ComponentReport`, `ValidationReport`, `RevisionReport`, and `ImpactReport` models.
- **Flexible Export:** Full serialization to JSON (for automated ingestion) and Markdown (for human consumption).

## Quick Start — Windows

On Windows, you can start both the FastAPI backend and Streamlit UI simultaneously using the automated batch launcher:

```cmd
scripts\start_project.bat
```

This batch script automatically:
1. Resolves the project root relative to the launcher script location.
2. Verifies expected project file structure.
3. Detects and activates the existing Python virtual environment (`.venv\Scripts\activate.bat`).
4. Verifies system dependencies (`python`, `uvicorn`, `ollama`, and the `qwen3:4b` model).
5. Checks port availability (ports 8000 and 8501).
6. Launches FastAPI Backend and Streamlit UI simultaneously in separate console windows.

Once started, access the application at:
- **FastAPI OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Streamlit Web UI**: [http://127.0.0.1:8501](http://127.0.0.1:8501)

> [!NOTE]
> **Prerequisites & Service Management:**
> - Ollama must be installed and accessible in PATH.
> - The `qwen3:4b` model must be pulled prior to starting the application:
>   ```cmd
>   ollama pull qwen3:4b
>   ```
> - To safely stop the application services, run:
>   ```cmd
>   scripts\stop_project.bat
>   ```

---

## 7. Quick Start Guide (Manual Setup)

### Step 1: Environment Setup
```bash
pip install -r requirements.txt
```

Verify LangChain integrations:
```bash
python -c "from langchain_ollama import ChatOllama; print('LangChain Ollama: OK')"
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('LangChain Gemini: OK')"
```

### Step 2: Build the Data Foundation
```bash
# 1. Generate synthetic HLD specifications (v1.0 & v2.0)
python fixtures/generate_fixtures.py

# 2. Ingest documents and extract architecture chunks
python scripts/ingest_document.py

# 3. Generate BGE embeddings and construct FAISS index
python scripts/build_index.py
```

### Step 3: Run the Local Ollama Model (Primary / Private)
Ensure Ollama is running and pull the local model:
```bash
ollama run qwen3:4b
```

Execute a grounded architectural query via CLI:
```bash
python scripts/ask.py "What interface carries VehicleSpeed?" --provider ollama
```

### Step 4: Run Google Gemini Free Tier (Optional Cloud Dev/Demo)
Set your free Gemini API key:
```bash
# In Windows PowerShell:
$env:GEMINI_API_KEY="your-api-key-here"
$env:LLM_PROVIDER="gemini"
python scripts/ask.py "What interface carries VehicleSpeed?" --provider gemini
```

### Step 5: Launch the Streamlit Pilot Web UI
```bash
python scripts/run_ui.py --port 8501
```
Navigate to `http://localhost:8501`:
- **Tab 1 (Grounded Architecture Q&A)**: Quick-launch buttons for canonical questions Q1–Q5, answer inspection, validation badges (`[VALID]` vs `[UNVERIFIED]`), JSON/Markdown report downloads, and engineer review sign-off form.
- **Tab 2 (Architecture Explorer)**: Multi-view architecture intelligence:
  - `🧩 SWCs & Interfaces`: Specification entities with full provenance
  - `🔌 Ports & Signals`: Port definitions, signal routing, data types, and precision comparison
  - `🔗 Dependencies & Flows`: Component dependencies and end-to-end execution flows
  - `🌐 Architecture Graph`: Graph topology and Mermaid architecture diagram
  - `🔍 Revision Diff (v1.0 vs v2.0)`: Deterministic diffing verifying all 7 intentional changes
  - `💥 Change Impact Analysis`: Graph propagation, affected flows, and ASIL-D safety risk notes
- **Tab 3 (Audit Log & System Info)**: View recorded engineer review audits.

### Step 6: Launch the FastAPI REST Service
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI documentation available at `http://127.0.0.1:8000/docs`, including the 11 `/architecture/...` endpoints.

### Step 7: Run Automated Verification Tests
```bash
pytest tests/ -v
```
All **175 tests** run completely offline and pass with zero paid credentials.
