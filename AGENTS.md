# AGENTS.md — Multi-Agent Coordination & Source of Truth

**Project Name:** AUTOSAR HLD Intelligence & Traceability Assistant  
**Reference Case Study:** Case Study 1 — *AUTOSAR HLD Document Analysis Assistant*  
**Domain:** Automotive Systems Engineering + Generative AI + RAG + Document Intelligence  
**Document Status:** Living Master Coordination Document & Shared Source of Truth  
**Target Audience:** Autonomous Coding Agents, Peer Subagents, Human Reviewers, and Evaluators  

---

> [!IMPORTANT]
> **READ THIS DOCUMENT BEFORE MAKING ANY CHANGES.**  
> This file is the primary shared contract for all AI agents operating in this repository. Agents must never treat this file as a temporary session scratchpad or single-agent note. All modifications to schemas, directories, interfaces, and phase transitions must be recorded here.

---

## 1. Project Purpose & Scope Classification

The **AUTOSAR HLD Intelligence & Traceability Assistant** is an AI-assisted engineering software application designed to extract, organize, search, analyze, compare, and validate architectural knowledge from classic and adaptive AUTOSAR High-Level Design (HLD) documents.

### 1.1 Strict Scope Separation
To avoid requirement drift and ungrounded implementations, all tasks are strictly classified into three tiers:

1. **Official Case Study Requirements (Mandatory Foundation):**
   - Ingestion of HLD specifications (PDF, text, structured tables, OCR for scanned sheets).
   - Preservation of document hierarchy (headings, sections, tables, page numbers).
   - Extraction of AUTOSAR architecture entities: Software Components (SWCs), Interfaces, Ports, Signals, Functional Flows, and Dependencies.
   - Natural-language semantic search and grounded Question Answering (RAG).
   - Mandatory page-level and section-level citations for every output claim.
   - Cross-version revision comparison (e.g., v1.0 vs v2.0 delta analysis).
   - Inconsistency and completeness detection (identifying unmapped ports, dangling signals, interface type mismatches).
   - Human-in-the-Loop (HITL) review: Accept, Edit, Reject capabilities for all findings.
   - Export of structured findings (JSON, CSV, markdown reports).

2. **Project Implementation Decisions (Current Technical Architecture):**
   - Modular Python 3.12 architecture without heavy enterprise frameworks (No LangChain, No LlamaIndex).
   - Local dense embeddings using HuggingFace models (default: `BAAI/bge-small-en-v1.5`, 384-dimensional).
   - Local vector store: FAISS `IndexFlatIP` with L2-normalized embeddings for exact cosine similarity.
   - Document Parsing: PyMuPDF (`fitz`) for fast, local layout and table extraction.
   - Persistence: SQLite database managed via SQLAlchemy ORM alongside structured JSON metadata catalogs.
   - Web API & User Interface: FastAPI backend + Streamlit web frontend (Phases 10+).

3. **Optional Future Enhancements (Post-MVP / Non-blocking):**
   - Knowledge Graph storage (Neo4j) for graph-traversal visualization.
   - Enterprise PostgreSQL / pgvector migration.
   - Advanced multi-tenant Role-Based Access Control (RBAC).
   - Enterprise OCR pipeline (Tesseract / Docling / Vision LLMs).

---

## 2. Boundaries & Out-of-Scope Constraints

The system is strictly an **engineering assistant**, not an autonomous authority. 

> [!CAUTION]
> **Prohibited Actions:**
> - NEVER automatically approve architectural decisions or sign off on safety compliance.
> - NEVER modify or overwrite approved source HLD documents.
> - NEVER treat an AI prediction, synthesis, or inferred relationship as authoritative engineering truth.
> - NEVER fabricate architectural data, ports, signals, or component links.

### Mandatory Language Guidelines for Findings & Analysis
When reporting deviations, discrepancies, or anomalies, agents and generative modules MUST use cautious, review-oriented terminology:
- **Required:** `"potential inconsistency"`, `"possible missing relationship"`, `"unmapped signal candidate"`, `"requires engineer review"`.
- **Prohibited:** `"the architecture is incorrect"`, `"the specification is invalid"`, `"the design violates ISO 26262"` (unless verifiable by an exact, deterministic rule check).

---

## 3. System Target Architecture

```
                               ┌─────────────────────────────────────────┐
                               │             Human Engineer              │
                               └────────────────────┬────────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │          Streamlit Web Console          │
                               └────────────────────┬────────────────────┘
                                                    │ REST API
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │             FastAPI Backend             │
                               └────────────────────┬────────────────────┘
                                                    │
         ┌──────────────────────────────────────────┴──────────────────────────────────────────┐
         ▼                                                                                     ▼
┌─────────────────────────────────┐                                           ┌─────────────────────────────────┐
│     Deterministic Services      │                                           │     RAG & Retrieval Engine      │
│  - Document Ingestion (PyMuPDF) │                                           │  - Query Embedding (BGE-small)  │
│  - Architecture Chunker         │                                           │  - FAISS Vector Store (IP)      │
│  - Exact Entity Lookup          │                                           │  - Metadata Store (Provenance)  │
│  - Rule Consistency Check       │                                           │  - Grounded Context Assembly    │
│  - SQLite Database (SQLAlchemy) │                                           │  - Citation Verification        │
└─────────────────────────────────┘                                           └────────────────┬────────────────┘
                                                                                               │
                                                                                               ▼
                                                                              ┌─────────────────────────────────┐
                                                                              │      Grounded LLM Synthesizer   │
                                                                              │  - Structured JSON Output       │
                                                                              │  - Evidence Citations Attached  │
                                                                              │  - Confidence / Limitations     │
                                                                              └────────────────┬────────────────┘
                                                                                               │
                                                                                               ▼
                                                                              ┌─────────────────────────────────┐
                                                                              │     HITL Review & Storage       │
                                                                              │  - Accept / Edit / Reject       │
                                                                              │  - Audit Trail (SQLite)         │
                                                                              └─────────────────────────────────┘
```

---

## 4. End-to-End Pipeline & Traceability Rules

Every document follows a strict, auditable pipeline:

$$\text{HLD PDF} \longrightarrow \text{Ingest} \longrightarrow \text{Structure Chunker} \longrightarrow \text{Metadata} \longrightarrow \text{Vector Index} \longrightarrow \text{Retrieval} \longrightarrow \text{Synthesis} \longrightarrow \text{Citation} \longrightarrow \text{HITL Review}$$

### 4.1 Ingestion Rules
1. Process page-by-page. Never discard `page_number` (1-indexed).
2. Retain structural heading context (`section`, `section_title`).
3. Retain tabular structures (signal definitions, port mappings, dependency tables).
4. Auto-detect and store document version (`version`) and unique `document_id`.

### 4.2 Architecture-Aware Chunking Rules
- **Do NOT** use blind fixed character/token slicing across structural boundaries.
- Respect section boundaries: Software Components, Interfaces, Ports, Signals, Dependencies, and Functional Flows.
- Preserve table blocks intact wherever possible.
- Each chunk must be assigned an immutable provenance ID:
  $$\text{chunk\_id} = \texttt{\{doc\_id\_short\}\_v\{version\}\_p\{page:02d\}\_c\{counter:02d\}}$$

### 4.3 Provenance & Citation Invariant
For every statement generated by the assistant, the reviewer must be able to verify:
- **Source Document ID**
- **Document Version**
- **Source Page Number**
- **Section Number & Title**
- **Exact Extracted Text Chunk**

If evidence is insufficient to answer a query, the assistant must explicitly output:
`"Insufficient evidence in approved documents to support this query."`

---

## 5. Domain Entities & Relationships

### 5.1 Primary Entities
- **Component (SWC):** Application Software Component, Sensor SWC, Actuator SWC, Composition SWC.
- **Interface:** Sender-Receiver (data), Client-Server (operations), Parameter, Trigger.
- **Port:** Provide Port (P-Port / Output), Require Port (R-Port / Input), PR-Port.
- **Signal / Data Element:** Name, data type (e.g., `float32`, `uint16`, `float64`), unit, min/max range.
- **Dependency:** Directional reliance between components (e.g., component $A$ consumes signal from component $B$).
- **Functional Flow:** Sequence of component interactions satisfying a vehicle feature (e.g., sensor to actuator path).

### 5.2 Deterministic Evidence Principle
Agents must **never** infer a dependency or architectural relationship solely because two entities are mentioned in the same paragraph. Relationships must be established through explicit textual or tabular assertions in the document.

---

## 6. Implementation Principles: AI vs. Deterministic Separation

To guarantee predictability and eliminate hallucination:

| Capability | Execution Model | Implementation Method |
| :--- | :--- | :--- |
| PDF Layout & Text Parsing | **Deterministic** | PyMuPDF (`fitz`), Regex |
| Chunk Partitioning & Typing | **Deterministic** | Domain heuristics (`hld_chunker.py`) |
| Vector Similarity & Filtering | **Deterministic** | FAISS `IndexFlatIP`, JSON Metadata filter |
| Relational Storage & CRUD | **Deterministic** | SQLite, SQLAlchemy ORM |
| Exact Entity Matching & Diff | **Deterministic** | Python set/dict algorithms |
| Rule Consistency Validation | **Deterministic** | Rule engine (dangling ports, type mismatch) |
| Audit Trail Logging | **Deterministic** | SQLite `hitl_checkpoints` table |
| Natural-Language Understanding | **AI / LLM** | Dense retriever + prompt-guided synthesizer |
| Architectural Summarization | **AI / LLM** | Context-grounded generation with citations |
| Explaining Complex Changes | **AI / LLM** | Synthesis over deterministic diff tables |

---

## 7. Project Isolation & Multi-Tenancy Rules

- All data, chunks, and index vectors must be scoped by `project_id`.
- Retrieval queries must never mix documents across different `project_id` boundaries.
- Cross-version comparisons must only occur within the same project when explicitly requested.
- Never commit private OEM documents, API keys, credentials, or proprietary binaries.

---

## 8. Multi-Phase Roadmap & Milestones

| Phase | Title | Objective | Status | Exit Criteria |
| :---: | :--- | :--- | :---: | :--- |
| **Phase 1** | **Discovery & Retrieval Foundation** | Ingestion, architecture-aware chunking, FAISS, metadata catalog, test suite. | **DONE** | Ingestion pipeline functional, FAISS index built, 28/28 tests passing. |
| **Phase 2** | **Grounded RAG Q&A Engine** | Context builder, LLM provider abstraction, structured JSON schema, citation validation, grounding checker, CLI `ask.py`. | **DONE** | Grounded answers, valid citations, all canonical queries passing, 51/51 tests passing. |
| **Phase 3** | **Index Persistence & Optimization** | Metadata filtering, multi-index routing by project/version. | Planned | Dynamic index reloading, version-filtered vector queries. |
| **Phase 4** | **Grounded RAG Q&A Engine** | LLM prompt design, context assembly, structured JSON mode, citations. | Planned | Traceable answers with exact page/section citations; handling of unknown queries. |
| **Phase 5** | **Architecture Entity Extraction** | Structured extraction of SWCs, Ports, Interfaces, Signals into DB models. | Planned | Automated entity tables populated with document provenance. |
| **Phase 6** | **Traceability & Relationship Graph** | Directed relationship mapping (Component $\to$ Port $\to$ Interface $\to$ Signal). | Planned | Traceability queries functional; relationship matrix validated. |
| **Phase 7** | **Consistency & Completeness Analyzer** | Heuristic & deterministic rule checks for dangling signals, unmapped ports. | Planned | Reproducible finding reports labeled `"potential inconsistency"`. |
| **Phase 8** | **Cross-Version Revision Diffing** | Delta engine comparing v1.0 and v2.0 entities, signals, and dependencies. | Planned | Accurate change reports categorized into Added/Modified/Removed. |
| **Phase 9** | **HITL Governance & Review Workflow** | Accept/Edit/Reject workflow, audit logging, approved findings database. | Planned | Review state persistent in SQLite; complete audit history trail. |
| **Phase 10**| **FastAPI Backend & Streamlit Console** | Full-stack interactive UI for architects and engineering leads. | Planned | End-to-end web demo with interactive search, diffing, and HITL actions. |
| **Phase 11**| **Evaluation & Benchmark Harness** | Precision@K, Recall@K, MRR, citation groundedness scoring. | Planned | Benchmark reports generated on formal gold-standard evaluation dataset. |
| **Phase 12**| **Containerization & Deployment** | Dockerfile, docker-compose, reproducible setup, final documentation. | Planned | Single-command containerized spin-up and demo execution. |

---

## 9. Multi-Agent Coordination Protocol

When autonomous agents or subagents operate on this repository, they must strictly abide by the following rules:

1. **Check Repository State First:** Never assume a file does not exist. Inspect directories using file listing tools before creating new modules.
2. **Never Blindly Overwrite:** Do not replace working code. If refactoring is necessary, preserve existing interfaces and backward compatibility.
3. **Respect Shared Models:** The core models in `ingestion/models.py`, `chunking/models.py`, and `db/models.py` are shared contracts. If extending a model, ensure all consumers are updated.
4. **No Direct Reference Repo Edits:** The lecturer reference directory `GenAICaseStudy-main/` must remain **completely untouched**.
5. **No Hardcoded Absolute Paths:** Always use Python `pathlib.Path` relative to the project root (`app.config.PROJECT_ROOT`).
6. **No Heavy Framework Creep:** Do not introduce LangChain, LlamaIndex, ChromaDB, or Neo4j unless explicitly required and approved in project planning.
7. **Run Tests After Any Modification:** Every code change must be validated by running `pytest tests/ -v`.
8. **Keep Data & Code Separated:** Vector indexes, SQLite databases, and parsed JSON files belong in `data/`, never in source directories.
9. **Update Documentation:** Whenever architecture, configuration, or pipeline behaviors are modified, update `README.md` and `AGENTS.md`.

---

## 10. Agent Handoff Protocol

Every agent concluding a task must provide a standardized handoff summary:

```markdown
### Agent Handoff Summary
- **Task Objective:** [Clear description of what was tackled]
- **Files Modified/Created:** [List of paths]
- **Key Implementation Details:** [Architectural choices, non-obvious logic]
- **Tests Executed:** [Pytest command and pass/fail summary]
- **Known Limitations / Edge Cases:** [Any unresolved issues or constraints]
- **Next Recommended Steps:** [Immediate next task for subsequent agents]
```

---

## 11. Definition of Done (DoD)

A feature or phase is **DONE** only when:
- [x] Code is implemented cleanly with clear docstrings and error handling.
- [x] Full source traceability and provenance are maintained.
- [x] Integration with existing repository components is validated.
- [x] Dedicated unit and integration tests exist and pass (`pytest`).
- [x] No secrets, private credentials, or absolute local file paths are introduced.
- [x] Phase exit criteria are satisfied and verified by actual execution.
- [x] Documentation (`README.md`, `AGENTS.md`, and relevant reports) is synchronized.

---

### Agent Handoff Summary — Phase 2: Grounded RAG Q&A
- **Task Objective:** Implement grounded Question Answering over the Phase 1 FAISS retrieval foundation with structured JSON schemas, deterministic citation validation, grounding verification, application-level confidence rating, human review gating, CLI `scripts/ask.py`, and comprehensive test suite.
- **Files Modified/Created:**
  - `rag/__init__.py`: Exported package API (`ask`, `RAGPipeline`, schemas).
  - `rag/models.py`: Pydantic models for `RAGResponse`, `Citation`, `Claim`, `ContextChunk`, `QueryRequest`.
  - `rag/context_builder.py`: Context assembler preserving all provenance headers.
  - `rag/prompts.py`: Engineering assistant system prompt and user prompt formatters.
  - `rag/llm_provider.py`: Abstraction for `LLMProvider`, `OpenAILLMProvider`, `GeminiLLMProvider`, `MockLLMProvider`, and `get_llm_provider`.
  - `rag/citation_validator.py`: Deterministic citation verification against retrieved chunks and metadata.
  - `rag/grounding_checker.py`: Deterministic token/vocabulary support checker for claims against cited chunks.
  - `rag/pipeline.py`: Main RAG orchestrator with filtering, embedding, retrieval, LLM synthesis, and confidence evaluation.
  - `scripts/ask.py`: CLI verification tool supporting version/project filters, providers, and formatted output.
  - `tests/test_rag.py`: 23 dedicated unit/integration tests covering items A through L.
  - `app/config.py`: Added offline hub caching fallback and LLM provider configuration.
  - `embeddings/embedder.py`: Added local cache fallback on load.
  - `README.md`: Updated architecture layout, CLI examples, and test suite instructions.
  - `reports/phase2_validation_report.md`: Formal Phase 2 validation and compliance report.
- **Key Implementation Details:**
  - Zero framework bloat (no LangChain or LlamaIndex).
  - Deterministic separation: Citations are verified against actual retrieved `chunk_id`, `version`, `page`, and `section`.
  - Offline-first & CI-safe: `MockLLMProvider` enables 100% credential-free testing with accurate domain synthesis.
  - Metadata isolation: Queries can be filtered by `version` (e.g. `1.0` vs `2.0`) without vector leakage.
- **Tests Executed:** `pytest tests/ -v` passed all 51 tests (28 Phase 1 + 23 Phase 2) with 0 failures in 50.58s.
- **Known Limitations / Edge Cases:** Grounding checker uses token/vocabulary overlap heuristic; complex semantic inference will benefit from Phase 3 entity graph validation.
- **Next Recommended Steps:** Phase 3: Architecture Entity Extraction (SWCs, Ports, Interfaces, Signals into relational/graph DB models).
