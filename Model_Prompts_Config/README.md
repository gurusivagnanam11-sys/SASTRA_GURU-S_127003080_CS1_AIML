# Model Prompts and Configuration Package (`Model_Prompts_Config/`)

## 1. Directory Overview & Purpose

This directory serves as the centralized technical reference and configuration template package for the **AUTOSAR HLD Intelligence & Traceability Assistant**. It documents how language models, embedding models, prompt templates, vector stores, and runtime environment settings are structured, loaded, and maintained across the repository.

```
Model_Prompts_Config/
├── prompts/
│   ├── system_prompt.md            # Active system prompt (11 engineering rules & JSON schema)
│   ├── user_prompt_template.md     # Production user query template & context format
│   └── grounding_prompt.md         # Deterministic Python grounding & citation specification
├── model_config.md                 # Complete technical reference of models, retrieval & limits
├── .env.example                    # Verified environment template with zero secrets
└── README.md                       # This operational and onboarding guide
```

---

## 2. Live Code Correspondence

The files in this directory document the live codebase without duplicating runtime execution:

| Documentation File | Live Implementation Source | Live Code Role |
| :--- | :--- | :--- |
| `prompts/system_prompt.md` | [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py) (`SYSTEM_PROMPT`) | Passed to `LLMProvider.generate(system_prompt=...)` in [`rag/pipeline.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/pipeline.py). |
| `prompts/user_prompt_template.md` | [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py) (`build_user_prompt`) | Formats user question and retrieved context headers from [`rag/context_builder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/context_builder.py). |
| `prompts/grounding_prompt.md` | [`rag/grounding_checker.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/grounding_checker.py) & [`rag/citation_validator.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/citation_validator.py) | Documents the **deterministic Python grounding engine** (not an LLM prompt). |
| `model_config.md` | [`app/config.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/config.py), [`embeddings/embedder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/embeddings/embedder.py), [`vectorstore/faiss_store.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/vectorstore/faiss_store.py) | Technical specification of all active model, retrieval, chunking, and database parameters. |
| `.env.example` | [`docker-compose.yml`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/docker-compose.yml) & [`.env`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/.env) | Safe environment template matching application configuration loaders. |

> [!NOTE]
> The markdown files in `prompts/` are reference specifications. The live Python application reads prompt definitions directly from [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py).

---

## 3. How Settings are Loaded at Runtime

Configuration is centralized in [`app/config.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/config.py):
1. `PROJECT_ROOT` is resolved to the repository root.
2. `load_dotenv(PROJECT_ROOT / ".env")` reads `.env` variables if the file exists.
3. System environment variables override `.env` values (allowing Docker Compose and CI environment overrides).
4. Code defaults are applied when environment variables are unset:
   - `LLM_PROVIDER`: Defaults to `"ollama"` (or auto-detects `"gemini"` if `GEMINI_API_KEY` is present).
   - `EMBEDDING_MODEL`: Defaults to `"BAAI/bge-small-en-v1.5"`.
   - `TOP_K`: Defaults to `5`.
   - `CHUNK_MAX_CHARS`: Defaults to `1500`.
   - `OLLAMA_MODEL`: Defaults to `"qwen2.5:3b"`.
   - `GEMINI_MODEL`: Defaults to `"gemini-3.7-flash"`.

---

## 4. Setup Guide: Creating `.env` Safely

To configure the application without exposing credentials:

### Step 1: Copy Template to Root `.env`
On Windows (PowerShell):
```powershell
Copy-Item Model_Prompts_Config\.env.example .env
```
On Linux / macOS:
```bash
cp Model_Prompts_Config/.env.example .env
```

### Step 2: Configure Provider Settings
Open `.env` in the root directory and select your provider:

- **Offline / Local Execution (Recommended Default)**:
  ```dotenv
  LLM_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=qwen2.5:3b
  ```
  *(No API keys needed. Ensure Ollama is running with `ollama run qwen2.5:3b`)*

- **Cloud Free-Tier Development (Optional)**:
  ```dotenv
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=AIzaSy...your-actual-api-key...
  GEMINI_MODEL=gemini-3.7-flash
  ```

### Step 3: Verify Security
Confirm that `.env` is ignored by Git:
```powershell
git status --ignored
```
*(The file `.env` should appear under "Ignored files", not "Untracked files" or "Changes to be committed".)*

---

## 5. Pre-Flight Configuration Verification

Before starting services, run the automated configuration smoke test:

```powershell
# Using the local virtual environment on Windows:
& .venv/Scripts/python.exe -c "from app.config import LLM_PROVIDER, EMBEDDING_MODEL, TOP_K; print(f'Config OK: Provider={LLM_PROVIDER}, Embedding={EMBEDDING_MODEL}, Top-K={TOP_K}')"
```

Verify that the vector index and metadata catalog are present:
```powershell
Test-Path data/indexes/hld_index.faiss
Test-Path data/indexes/hld_metadata.json
```
If missing, regenerate the index from the raw HLD documents:
```powershell
& .venv/Scripts/python.exe scripts/build_index.py
```

---

## 6. Regression Testing After Modifying Prompts or Settings

Whenever you update `SYSTEM_PROMPT` in `rag/prompts.py` or modify retrieval weights in `rag/hybrid_retriever.py`, execute the following regression tests:

```powershell
# 1. Cross-Version Grounding & Signal Datatype Contradiction Tests (8 tests)
& .venv/Scripts/python.exe -m pytest tests/test_vehiclespeed_cross_version.py -v

# 2. Retrieval Quality, Metadata Filtering & True/False Abstention Tests (13 tests)
& .venv/Scripts/python.exe -m pytest tests/test_validation_and_retrieval_fixes.py -v

# 3. Core RAG Pipeline Unit & Integration Tests (23 tests)
& .venv/Scripts/python.exe -m pytest tests/test_rag.py -v

# 4. End-to-End Architecture Consistency Suite (13 tests)
& .venv/Scripts/python.exe -m pytest tests/test_phase7_validation.py -v

# 5. Security & Prompt Injection Defense Suite (11 tests)
& .venv/Scripts/python.exe -m pytest tests/test_phase5_security.py tests/test_phase6.py -v
```

---

## 7. Container Rebuild & Restart Policies

| Modified File / Configuration | Docker Action Required | Host Action Required |
| :--- | :--- | :--- |
| `rag/prompts.py` (Prompt updates) | `docker compose restart hld-api` | Restart API process |
| `app/config.py` (Default values) | `docker compose restart hld-api hld-ui` | Restart running scripts |
| `.env` (Environment variables) | `docker compose down && docker compose up -d` | Reload terminal environment |
| `requirements.txt` or `Dockerfile` | `docker compose build --no-cache && docker compose up -d` | `pip install -r requirements.txt` |
| `data/indexes/` (Re-indexed FAISS) | `docker compose restart hld-api` | No restart needed (re-read on load) |

---

## 8. Active Settings vs Examples Summary

- **Active Production Settings**: Defined in [`app/config.py`](file:///C:/Users/guru2/Downloads/techpulsde\autosar_hld_assistant/app/config.py) and loaded dynamically from the root `.env`.
- **Reference Examples**: `.env.example` is an uncommitted example template with placeholder values. It has no effect on running containers until copied to `.env`.