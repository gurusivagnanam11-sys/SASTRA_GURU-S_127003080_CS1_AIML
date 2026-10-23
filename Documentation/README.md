# Documentation - AUTOSAR HLD Intelligence & Traceability Assistant

This directory contains the formal technical deliverables, engineering reports, and high-resolution architecture workflow diagrams for the capstone submission.

---

## 1. Deliverables Inventory

| File | Format | Description |
| :--- | :---: | :--- |

| [`RAG_Workflow.png`](RAG_Workflow.png) | PNG (High Res) | Complete end-to-end RAG architecture diagram illustrating ingestion, hybrid retrieval, query routing, LLM reasoning, citation validation, and architecture explorer. |
| [`RAG_Workflow.svg`](RAG_Workflow.svg) | SVG (Vector) | Scalable vector graphic representation of the system architecture suitable for high-dpi rendering and documentation embedding. |
| [`RAG_Workflow.mmd`](RAG_Workflow.mmd) | Mermaid Source | Source code of the Mermaid architecture workflow diagram for version-controlled maintenance. |

---

## 2. Architecture Workflow Overview

The architecture workflow illustrated in [`RAG_Workflow.png`](RAG_Workflow.png) spans 6 integrated pipelines:
1. **Document Ingestion Pipeline:** PDF upload, table structure extraction, and section header parsing.
2. **Hybrid Indexing Pipeline:** Dense FAISS vector store (`BAAI/bge-small-en-v1.5`) paired with BM25 sparse keyword indices.
3. **Query Classification & Routing:** Classifies incoming queries into Canonical Architecture Queries (routed to deterministic SWC dependencies) vs. General Exploration Queries.
4. **Retrieval & Fusion Engine:** Multi-signal Reciprocal Rank Fusion (RRF) with version-aware filtering.
5. **LLM Orchestration & Fallback:** Local Ollama (`qwen2.5:3b`) with Gemini fallback, generating structured JSON with resilient syntax repair.
6. **Grounding & Citation Verification:** Bracketed citation mapping, chunk ID verification, and claim-level grounding checks before presenting findings in the UI.
