# AUTOSAR HLD Intelligence & Traceability Assistant - Codebase Guide

This directory contains the complete source code, tests, scripts, evaluation harnesses, Docker configuration, and runtime environment for the **AUTOSAR HLD Intelligence & Traceability Assistant**.

---

## 1. Supported Runtime Requirements

- **Operating System:** Windows 10/11, macOS, or Linux (Ubuntu 22.04+ recommended)
- **Python Version:** Python 3.12 (CPython 3.12.3+ verified)
- **Local LLM Inference (Free-Tier Default):** Ollama daemon with model `qwen2.5:3b` (or `qwen3:4b` / `llama3.1:8b`)
- **Cloud LLM Inference (Fallback):** Google Gemini Cloud (`gemini-3.7-flash` or `gemini-2.0-flash`) with API key
- **Container Runtime:** Docker Desktop 4.25+ with Docker Compose v2 (optional for containerized deployment)
- **OCR Engine (Optional for scanned PDFs):** Tesseract OCR 5.x with English language data

---

## 2. Directory Structure

```text
Code/
├── app/                  # FastAPI backend (main.py), Streamlit UI (streamlit_app.py), and config.py
├── rag/                  # Multi-signal hybrid retriever, query router, LLM provider, citation validator, grounding checker
├── analysis/             # Architecture validator, revision diff, and impact analysis
├── chunking/             # Semantic HLD chunker and data models
├── db/                   # SQLite database models and repository (autosar_hld.db)
├── embeddings/           # SentenceTransformer wrapper (BAAI/bge-small-en-v1.5)
├── extraction/           # Structural interface and signal extractor
├── ingestion/            # PyMuPDF PDF parser, metadata extractor, and OCR fallback
├── vectorstore/          # FAISS vector store and metadata store
├── fixtures/             # Benchmark HLD specification PDFs (v1.0 & v2.0)
├── reports/              # Compliance report generator, governance tracking, and exports
├── evaluation/           # Historical benchmark modules and retrieval evaluation scripts
├── evaluation_result/    # Audited RAGAS evaluation harness, datasets, and runtime shim (compat.py)
├── scripts/              # Service launchers (start_project.bat, run_ui.py, ask.py)
├── tests/                # Automated pytest unit, regression, and Docker test suites
├── Dockerfile            # Production CPU-only Dockerfile
├── docker-compose.yml    # Multi-container orchestration (hld-api + hld-ui)
├── requirements.txt      # Core application dependencies
├── pytest.ini            # Pytest configuration
├── .env.example          # Authoritative environment configuration template
└── .streamlit/           # Streamlit theme and server configuration (config.toml)
```

---

## 3. Local Environment Setup

### 3.1 Create Virtual Environment & Install Dependencies
From the `Code/` directory:

```powershell
# Navigate to the Code directory
cd C:\Users\guru2\Downloads\techpulsde\autosar_hld_assistant\Code

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install application dependencies
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) Install evaluation dependencies for RAGAS
pip install -r evaluation_result/requirements-eval.txt
```

### 3.2 Environment Configuration
Copy the safe `.env.example` template to `.env`:

```powershell
# Windows:
copy .env.example .env

# Linux/macOS:
cp .env.example .env
```

Edit `.env` to configure your preferred LLM provider:
```ini
# Core Configuration
PROJECT_ID=demo_project
TOP_K=5
CHUNK_MAX_CHARS=1500

# Provider Selection: "ollama", "gemini", or "mock"
LLM_PROVIDER=ollama

# Local Ollama Settings (Default)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
LLM_TIMEOUT_SECONDS=180

# Gemini Settings (Optional Cloud Fallback)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash
```

---

## 4. Ollama Service Verification

Ensure the Ollama daemon is running locally:
```powershell
# Verify Ollama is responsive
curl http://localhost:11434/api/tags

# Pull the required model if not already present
ollama pull qwen2.5:3b

# Verify the model appears in your local model list
ollama list
```

---

## 5. Starting API and UI Services

### Option A: Automated Windows Launcher
From the `Code/` directory, simply run:
```cmd
scripts\start_project.bat
```
This launcher checks port availability, activates `.venv`, verifies Ollama, and opens both the FastAPI and Streamlit services in dedicated terminal windows.

### Option B: Manual Service Launch
In Terminal 1 (FastAPI Backend):
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

In Terminal 2 (Streamlit UI Console):
```powershell
python scripts/run_ui.py --host 0.0.0.0 --port 8501
```
- Engineering Console: `http://localhost:8501`

---

## 6. Docker Compose Deployment

The application is containerized with CPU-only PyTorch and Tesseract OCR:

```powershell
# From the Code/ directory:
docker compose up --build -d

# Check service logs:
docker compose logs -f

# Verify running containers:
docker compose ps

# Shut down services:
docker compose down
```

- FastAPI Endpoint: `http://localhost:8000`
- Streamlit Console: `http://localhost:8501`

---

## 7. Automated Test Suite Execution

Run all test suites from the `Code/` directory:

```powershell
# Run all unit and regression tests
pytest -v

# Run RAGAS evaluation pipeline tests
pytest tests/test_ragas_evaluation.py -v

# Run validation and retrieval regression tests
pytest tests/test_validation_and_retrieval_fixes.py -v

# Run architecture regression tests
pytest tests/test_architecture_regression.py -v

# Run Docker configuration verification
pytest tests/test_docker_configuration.py -v
```

---

## 8. Running the Evaluation Pipeline

All evaluation harnesses and adapters are located in `evaluation_result/`:

```powershell
# 1. Validate dataset schema without executing LLM inference (Dry Run):
python evaluation_result/ragas/evaluate_ragas.py --validate-only

# 2. Fast pipeline smoke test with verified mock judge:
python evaluation_result/ragas/evaluate_ragas.py --mode both --sample-limit 2 --judge mock --output-dir evaluation_result/ragas/results_corrected

# 3. Full live LLM evaluation using local Ollama:
python evaluation_result/ragas/evaluate_ragas.py --mode both --judge ollama --model qwen2.5:3b --output-dir evaluation_result/ragas/results_corrected
```

Generated outputs are saved in:
- `Code/evaluation_result/ragas/results_corrected/summary.json`
- `Code/evaluation_result/ragas/results_corrected/per_sample_results.csv`
- `Code/evaluation_result/ragas/results_corrected/evaluation_report.md`
- Final submission-level reports are mirrored in `../Evaluation_Results/`.

---

## 9. Troubleshooting & Common Issues

1. **Port 8000 or 8501 already in use:**
   ```powershell
   Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
   Get-Process -Id (Get-NetTCPConnection -LocalPort 8501).OwningProcess | Stop-Process -Force
   ```
2. **Ollama connection timeout:**
   Ensure Ollama is started (`ollama serve`). If running in Docker, Docker connects via `host.docker.internal:11434`.
3**Missing retrieval index:** First ingest both fixture documents, then build the index from the `Code/` directory with the virtual environment activated:

```powershell
python scripts/ingest_document.py "fixtures/v1/AUTOSAR_HLD_v1.0.pdf" --version 1.0
python scripts/ingest_document.py "fixtures/v2/AUTOSAR_HLD_v2.0.pdf" --version 2.0
python scripts/build_index.py
```

Run indexing after ingestion has created the chunks in the local SQLite database. The index-building script does not accept a `--version all` option.
