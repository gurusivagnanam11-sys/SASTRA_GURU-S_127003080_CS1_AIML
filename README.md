# AUTOSAR HLD Intelligence & Traceability Assistant

**Capstone Project Submission**  
**Repository:** [SASTRA_GURU-S_127003080_CS1_AIML](https://github.com/gurusivagnanam11-sys/SASTRA_GURU-S_127003080_CS1_AIML)  
**Candidate:** GURU S (Register No: 127003080)  
**Program:** B.Tech. Computer Science & Engineering (AI & ML), SASTRA Deemed to be University

---

## Case Study 1 — AUTOSAR HLD Intelligence & Traceability

This project presents a Retrieval-Augmented Generation (RAG) assistant designed to help users explore AUTOSAR High-Level Design (HLD) documents. It supports document retrieval, question answering, and traceability-oriented analysis across design-document versions.

The application combines a **FastAPI backend**, a **Streamlit interface**, **FAISS** vector retrieval, text embeddings, and a locally hosted language model through Ollama.

The project uses synthetic HLD documents for demonstration and evaluation. It is a research and educational prototype, not a certified automotive safety or compliance tool.

---

## 🚀 Choose How to Run the Project

Choose either of the following deployment methods:

| Method | Recommended for | Main requirements |
|---|---|---|
| **Option 1: Local Windows Setup** | Development, debugging, and source-code exploration | Python, project dependencies, Ollama, model, and project data |
| **Option 2: Docker Deployment** | Running the packaged backend and UI in containers | Docker Desktop, published images, and required external dependencies and configuration |

---
## Option 1 — Quick Start (Local Windows)

### Prerequisites

- Python 3.12
- Ollama installed and running
- Required project dependencies and embedding model
- Internet access for any model files that are not already cached

### Installation

Open Command Prompt from the repository root and run each command separately:

```bat
cd Code
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

In `.env`, configure the local LLM provider:

```ini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

Save the file and close Notepad. Make sure Ollama is running and download the required model:

```bat
ollama pull qwen2.5:3b
```

### Prepare the HLD documents and retrieval index

Run these commands from the `Code` directory, with the virtual environment activated:

```bat
python scripts\ingest_document.py "fixtures\v1\AUTOSAR_HLD_v1.0.pdf" --version 1.0
python scripts\ingest_document.py "fixtures\v2\AUTOSAR_HLD_v2.0.pdf" --version 2.0
python scripts\build_index.py
```

Complete ingestion and indexing before asking retrieval questions. These commands create the document records and build the vector index needed for retrieval.

### Launch the application

```bat
scripts\start_project.bat
```

### Access the application

- **FastAPI API documentation:** http://localhost:8000/docs
- **Streamlit interface:** http://localhost:8501

## Option 2 — Docker Compose Deployment

The repository includes a Dockerfile and a Docker Compose configuration for the FastAPI backend and Streamlit interface.

### Prerequisites

- Docker Desktop installed and running.
- Either Ollama running on the host with `qwen2.5:3b`, or a valid Google Gemini API key.
- The required environment configuration and HLD retrieval index.

### 1. Configure the environment

Open Command Prompt in the repository root:

```bat
cd Code
copy .env.example .env
notepad .env
```

Choose one LLM provider.

**Local Ollama:**

```ini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b
```

Ensure Ollama is running on the host and the model is downloaded.

**Google Gemini:**

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_api_key
```

Use your real API key only in your local `.env` file. Never commit it to GitHub.

### 2. Build and start the containers

Run from the `Code` directory:

```bash
docker compose up --build -d
```

This builds the included Docker configuration and starts the API and UI services.

### 3. Prepare the retrieval index

On a first deployment, run:

```bash
docker compose exec hld-api python scripts/ingest_document.py fixtures/v1/AUTOSAR_HLD_v1.0.pdf --version 1.0
docker compose exec hld-api python scripts/ingest_document.py fixtures/v2/AUTOSAR_HLD_v2.0.pdf --version 2.0
docker compose exec hld-api python scripts/build_index.py
docker compose restart hld-api hld-ui
```

These commands ingest both bundled HLD fixtures into the shared data directory and build the retrieval index.

### 4. Open the application

- **Streamlit interface:** http://localhost:8501
- **FastAPI API documentation:** http://localhost:8000/docs
- **Health endpoint:** http://localhost:8000/health

### 5. Check status and logs

```bash
docker compose ps
docker compose logs -f
```

Press `Ctrl+C` to stop following logs; this does not stop the containers.

### 6. Stop the services

```bash
docker compose down
```

### Common Docker problems

| Problem | Suggested solution |
|---|---|
| Docker is not running | Start Docker Desktop and verify `docker info`. |
| A port is already in use | Stop the conflicting process or container, or change the host-side port mapping. |
| Container name already exists | Check `docker ps -a`; remove old containers if appropriate. |
| Streamlit cannot connect to the API | Check the `API_BASE_URL` setting and Docker network configuration. The Compose configuration uses `http://hld-api:8000` internally. |
| Ollama connection fails | Verify Ollama is running on the host and the configured URL is `http://host.docker.internal:11434`. |
| Gemini requests fail | Check that `GEMINI_API_KEY` is valid and that `LLM_PROVIDER=gemini`. |
| Retrieval returns no useful results | Verify that both HLD PDFs were ingested and the FAISS index was built successfully. |
| A container crashes | Run `docker compose logs hld-api` or `docker compose logs hld-ui` to inspect the error. |

**Important:** The repository's Docker Compose configuration builds the application from source. The published Docker Hub images are separate artifacts; the standalone `docker run` commands are not the recommended deployment path documented here.



## 1. Project Title and Summary

**AUTOSAR HLD Intelligence & Traceability Assistant: Architecture-Aware Retrieval-Augmented Generation with Deterministic Verification for Automotive Software Specifications**

The AUTOSAR HLD Intelligence Assistant is an enterprise-grade automotive engineering platform designed to analyze, trace, and verify complex High-Level Design (HLD) specifications across release versions (v1.0 and v2.0). By combining **multi-signal hybrid retrieval (Dense FAISS + Sparse BM25 + Reciprocal Rank Fusion)** with **deterministic AST-based architectural validation**, **claim-level grounding checks**, and an **honest abstention engine**, the system eliminates hallucinations in safety-critical automotive architecture reviews.

---

## 2. Problem Statement and Intended Users

### Problem Statement
Automotive software architectures governed by AUTOSAR Classic and Adaptive standards encompass hundreds of interconnected Software Components (SWCs), ports, interfaces (Sender-Receiver, Client-Server), and signals. Engineering teams face major challenges:
- Manual cross-referencing between architectural revisions (e.g., v1.0 baseline vs. v2.0 evolution) is labor-intensive and prone to missing deprecated or altered interfaces.
- Standard Large Language Model (LLM) chatbots hallucinate architectural details, fabricate non-existent CAN/Ethernet signals, and fail to provide verifiable provenance.
- Pure semantic vector search frequently misses exact architectural identifiers (e.g., confusing `VehicleSpeed` in `VehicleDataInterface` with general velocity references).

### Intended Users
- **Automotive Software Architects:** Reviewing system topology, component boundaries, and cross-release interface changes.
- **Systems & Safety Engineers:** Verifying signal routing, component dependency cycles, and compliance against ISO 26262 requirements.
- **Tier-1 Suppliers & OEMs:** Validating incoming High-Level Design specifications against implementation baselines.

---

## 3. Key Capabilities Actually Implemented

1. **Architecture-Aware Document Ingestion & Chunking:**
   - Ingests multi-version AUTOSAR HLD PDFs using PyMuPDF (`fitz`) with OCR fallback via Tesseract.
   - Deterministic chunking along architectural boundaries (SWC definitions, port tables, interface schemas).
2. **Multi-Signal Hybrid Retrieval & Version Filtering:**
   - Dual-index architecture combining `BAAI/bge-small-en-v1.5` dense embeddings (FAISS FlatIP) with BM25 sparse keyword matching fused via Reciprocal Rank Fusion ($k=60$).
   - Explicit version-isolation and cross-version comparative retrieval (v1.0, v2.0, or All Versions).
3. **Canonical Architecture Query Routing:**
   - Automatically detects architectural dependency questions (e.g., *"What components are associated with VehicleControl?"*) and routes them to deterministic component dependency evidence.
4. **Deterministic Architecture Explorer & AST Validation:**
   - Extracts formal component graphs to validate port connectivity, unmapped interfaces, and dependency cycles without relying on LLM guesses.
5. **Multi-Stage Grounding & Citation Verification:**
   - Deterministic verification ensuring every bracketed citation chunk ID exists in retrieved context, resolves to the correct page/version, and supports the associated claim.
6. **Honest Abstention Engine:**
   - Explicitly abstains (`confidence="low"`, `review_required=True`) on out-of-scope or unsupported automotive parameters, achieving zero hallucinations on adversarial queries.
7. **Document Governance & Compliance Export:**
   - Document lifecycle state tracking (Draft, In-Review, Approved) with governance-aware retrieval penalties and automated markdown/PDF audit exports.

---

## 4. Architecture Summary and Diagrams

The system architecture follows a six-tier pipeline:
```text
[HLD PDFs v1.0 & v2.0]
         │
         ▼
[PyMuPDF + Architectural Chunker] ──► [Structured Chunks & Metadata DB]
         │
         ├──► [Dense Index: FAISS (BGE-small 384d)]
         └──► [Sparse Index: Rank-BM25]
                     │
                     ▼
             [User Query] ──► [Query Router]
                                    │
                                    ▼
       [Hybrid Retrieval: Reciprocal Rank Fusion (RRF)]
                                    │
                                    ▼
       [Local Ollama / Gemini LLM + JSON Syntax Repair]
                                    │
                                    ▼
       [Citation Validator & Claim Grounding Checker]
                                    │
                                    ▼
       [Streamlit Enterprise Console / FastAPI REST API]
```

Detailed architectural diagrams are available in the [`Documentation/`](Documentation/) folder:

- **Architecture Workflow Diagram (PNG):** [`Documentation/RAG_Workflow.png`](Documentation/RAG_Workflow.png)
- **Vector Workflow Diagram (SVG):** [`Documentation/RAG_Workflow.svg`](Documentation/RAG_Workflow.svg)
- **Mermaid Source Specification:** [`Documentation/RAG_Workflow.mmd`](Documentation/RAG_Workflow.mmd)

### AUTOSAR HLD Assistant Architecture

![AUTOSAR HLD Assistant Architecture](Documentation/AUTOSAR%20RAG%20Workflow%20Architecture.png)

---

## 5. Technology Stack Verified from Source Code

- **Core Backend Framework:** Python 3.12, FastAPI 0.115+, Uvicorn, Pydantic v2
- **User Interface:** Streamlit 1.40+ (Restrained, high-contrast automotive engineering console)
- **Document Processing & Parsing:** PyMuPDF (`fitz` 1.25+), pytesseract 0.3.13, Pillow
- **Information Retrieval & Vector Store:** FAISS (`faiss-cpu` 1.9+), Rank-BM25 0.2.2, Reciprocal Rank Fusion
- **Embedding Model:** `BAAI/bge-small-en-v1.5` (384 dimensions, PyTorch CPU-only runtime)
- **LLM Orchestration:** LangChain 0.3+, LangChain Community, LangChain Ollama, Google GenAI SDK
- **LLM Models Supported:**
  - *Local On-Premises (Default):* Ollama `qwen2.5:3b`
  - *Cloud Fallback:* Google Gemini (`gemini-3.7-flash` / `gemini-2.0-flash`)
  - *Deterministic CI/Offline:* CompleteMockJudge
- **Storage & Metadata:** SQLite 3 via SQLAlchemy 2.0 ORM, JSON metadata stores
- **Testing & Quality Assurance:** Pytest 9.1+, RAGAS 0.4.3, Datasets 3.0+
- **Containerization:** Docker, Docker Compose v2 (CPU-optimized `python:3.12-slim`)

---

## 6. Repository Folder Guide

The repository is structured according to the capstone submission guidelines:

```text
SASTRA_GURU-S_127003080_CSE_AIML/
├── README.md                 # Primary capstone submission overview (this file)
├── .gitignore                # Root ignore file excluding .env, caches, and binary indexes
├── Synopsis/                 # Capstone executive summary and research objectives
│   └── Synopsis.md
├── Input_Data/               # AUTOSAR HLD specification benchmark documents (v1.0 & v2.0)
│   ├── AUTOSAR_HLD_v1.0.pdf
│   ├── AUTOSAR_HLD_v2.0.pdf
│   └── README.md
├── Code/                     # Complete application source code, tests, scripts, and runtime
│   ├── app/                  # FastAPI & Streamlit application source
│   ├── rag/                  # Hybrid retriever, citation validator, grounding checker
│   ├── analysis/             # Architecture validator, revision diff, impact analysis
│   ├── chunking/             # Semantic HLD chunker
│   ├── db/                   # Database repository and models
│   ├── embeddings/           # Embedding generation wrappers
│   ├── extraction/           # Interface and signal extractors
│   ├── ingestion/            # PDF parsing and metadata extraction
│   ├── vectorstore/          # FAISS vector store
│   ├── fixtures/             # Test fixtures and generator
│   ├── reports/              # Compliance report generator
│   ├── scripts/              # Windows batch scripts and execution helpers
│   ├── tests/                # Automated pytest unit and regression suites
│   ├── evaluation_result/    # RAGAS evaluation harness, datasets, and runtime shim
│   ├── Dockerfile            # Production Dockerfile
│   ├── docker-compose.yml    # Docker Compose multi-service definition
│   ├── requirements.txt      # Core Python dependencies
│   ├── .env.example          # Authoritative environment template
│   └── README.md             # Codebase setup and execution guide
├── Model_Prompts_Config/     # System prompts, model configurations, and environment template
│   ├── prompts/              # System, user, and grounding prompt templates
│   ├── model_config.md       # Model parameters and selection rationale
│   ├── .env.example          # Synchronized reference environment template
│   └── README.md
├── Evaluation_Results/       # Verified evaluation reports, benchmark metrics, and evidence
│   ├── baseline_vs_hybrid_comparison.md # Baseline vs Hybrid comparative report
│   ├── retrieval_metrics.json          # Deterministic Hit Rate@5, Recall@5, MRR
│   ├── ragas_summary.json              # Full RAGAS execution summary
│   ├── per_sample_results.csv          # Granular per-query metric scores
│   ├── unsupported_query_abstention_report.json # Adversarial abstention results
│   ├── test_execution_evidence.md      # Pytest execution log (43 passed tests)
│   └── README.md
├── Documentation/            # Technical report and high-resolution architecture diagrams
│   ├── Technical_Report.docx # Comprehensive capstone technical report
│   ├── RAG_Workflow.png      # High-resolution architecture workflow diagram
│   ├── RAG_Workflow.svg      # Vector architecture diagram
│   ├── RAG_Workflow.mmd      # Mermaid workflow diagram source
│   └── README.md
├── Video/                    # Demonstration video walkthrough details and links
│   └── README.md
└── Declarations/             # Signed academic integrity and AI tool usage declarations
    ├── Academic_Integrity_Declaration.docx
    ├── AI_Tool_Usage_Declaration.docx
    └── README.md
```

---

## 7. Quick Links to Key Deliverables

- 📄 **Technical Report (PDF):** [View Technical Report](Technical_Report.pdf)
- 📘 **Project Synopsis (PDF):** [View Project Synopsis](Synopsis/Project_Synopsis.pdf)
- 📊 **Evaluation Benchmark Report:** [Baseline vs. Hybrid Retrieval](Evaluation_Results/baseline_vs_hybrid_comparison.md)
- 🏗️ **Architecture Diagram:** [View Architecture (PNG)](Documentation/AUTOSAR%20RAG%20Workflow%20Architecture.png)
- 🎥 **Demonstration Video:** [Watch Project Demo](Video/README.md)
- 📝 **Academic Integrity Declaration (PDF):** [View Declaration](Declarations/Academic_Integrity_Declaration.pdf)
- 🤖 **AI Tool Usage Declaration (PDF):** [View AI Usage Declaration](Declarations/AI_Tool_Usage_Declaration.pdf)

---

## 8. Setup Instructions

Complete setup and local execution instructions are provided in [`Code/README.md`](Code/README.md).


---



## 9. Model and Environment Configuration

The application enforces a **free-tier / on-premises policy**:
- **Default Local Model:** Ollama `qwen2.5:3b` running at `http://localhost:11434` (zero cloud data transfer).
- **Cloud Fallback:** Google Gemini `gemini-3.7-flash` via API key.
- **Offline / CI Testing:** Deterministic `mock` provider.

Full prompt definitions, hyperparameters, and environment variable documentation are located in [`Model_Prompts_Config/README.md`](Model_Prompts_Config/README.md).

---

## 10. Evaluation Methodology and Verified Results

### Evaluation Framework
- **Retrieval-Only Benchmark:** 25 grounded AUTOSAR queries evaluated on top-5 retrieved chunks against documented specification chunk IDs.
- **RAGAS Evaluator:** Faithfulness, Answer Relevancy, Context Precision, Context Recall, and Answer Correctness.
- **Adversarial Abstention Benchmark:** 10 out-of-scope automotive queries evaluating abstention rate and hallucination prevention.

### Evaluator Mode Transparency
- **Smoke Tests / Schema Validation:** Use `--judge mock` (`OFFLINE_MOCK_JUDGE`). Explicitly labeled as non-live; never presented as genuine quality ratings.
- **Live LLM Evaluation:** Evaluated with local Ollama (`qwen2.5:3b`). Failures and timeouts are recorded as `null`, never replaced with artificial perfect scores.

### Verified Results

| Metric Category | Metric | Baseline Dense (FAISS) | Hybrid (Dense + BM25 + RRF) | Delta ($\Delta$) |
| :--- | :--- | :---: | :---: | :---: |
| **Retrieval-Only (Top-5)** | Hit Rate@5 | 1.0000 | 1.0000 | 0.0000 |
| | Recall@5 | 0.5833 | 0.8333 | **+0.2500 (+25.0%)** |
| | Mean Reciprocal Rank (MRR) | 0.7500 | 1.0000 | **+0.2500** |
| **Adversarial Testing** | Abstention Rate | 100% (10/10) | 100% (10/10) | 0.0000 |
| | Low Confidence Rate | 100% (10/10) | 100% (10/10) | 0.0000 |
| | Unsupported Claims | 0 | 0 | 0 |

---

## 11. Responsible AI, Privacy, Citations, and Human Oversight

- **Privacy & On-Premises First:** Architectural specifications are processed locally. By default, embeddings and inference run locally via PyTorch and Ollama, preventing sensitive IP leakage.
- **Mandatory Citation Verification:** Every assertion must map to a retrieved chunk ID with document, page, and section provenance.
- **Human Oversight & Gating:** Queries flagged with `review_required=True` alert engineers that human verification is needed before design sign-off.
- **Document Governance:** Outdated or draft documents receive retrieval score penalties, preventing contamination from superseded specifications.

---

## 12. Known Limitations

- **Complex Multi-Page Nested Diagram Parsing:** Current OCR and text extraction parse text, tables, and section hierarchies; deep structural understanding of arbitrary vector graphics or proprietary CAD schematics is not supported.
- **Synthetic Specification Scope:** Benchmark datasets are grounded on synthetic AUTOSAR HLD v1.0 and v2.0 specifications designed for academic benchmarking, not proprietary OEM vehicle designs.
- **Compute Constraints on Local Judge:** Running comprehensive RAGAS live evaluations on a local CPU/GPU using 7B+ parameter judges requires significant compute and time (~20–30 minutes for full suites).

---

## 13. Academic Integrity and AI Tool Usage Disclosure

This project was conducted in strict compliance with the academic integrity guidelines of SASTRA Deemed to be University.
- Core architecture models, hybrid retrieval algorithms, deterministic validation engines, grounding checkers, and test harnesses were authored and evaluated by the candidate.
- AI assistants were utilized for boilerplate generation, test case scaffolding, and documentation styling under human direction and verification.
- Signed declarations are provided in [`Declarations/Academic_Integrity_Declaration.docx`](Declarations/Academic_Integrity_Declaration.docx) and [`Declarations/AI_Tool_Usage_Declaration.docx`](Declarations/AI_Tool_Usage_Declaration.docx).

---

## 14. License and Data-Sharing Status

- **Software Code:** Academic research prototype developed for capstone evaluation.
- **Data Sharing:** Benchmark synthetic HLD specifications (`AUTOSAR_HLD_v1.0.pdf` and `AUTOSAR_HLD_v2.0.pdf`) are bundled for reproducibility. No proprietary, classified, or confidential OEM data is included.
