# Input Data - AUTOSAR High-Level Design (HLD) Specifications

This directory contains the primary input architectural specifications evaluated by the **AUTOSAR HLD Intelligence & Traceability Assistant**.

---

## 1. Specification Inventory

| File | Release Version | Scope | Content Summary |
| :--- | :---: | :--- | :--- |
| [`AUTOSAR_HLD_v1.0.pdf`](AUTOSAR_HLD_v1.0.pdf) | **v1.0** (Initial Baseline) | Powertrain & Sensor Management | Baseline architecture specification defining initial Software Components (SWCs), ports, Sender-Receiver / Client-Server interfaces, and signals (e.g., `SensorManager`, `VehicleControl`, `VehicleSpeed`, `EngineSpeed`). |
| [`AUTOSAR_HLD_v2.0.pdf`](AUTOSAR_HLD_v2.0.pdf) | **v2.0** (Major Evolution) | Autonomous Driving, V2X, & Diagnostics | Major architectural evolution introducing new SWCs (`ADAS_Perception`, `DiagnosticManager`), modified interfaces, altered component dependencies, and deprecated signals. |

---

## 2. Ingestion & Processing Pipeline

When ingested via the application (`Code/ingestion/pdf_parser.py` or the Streamlit / FastAPI UI):
1. **Document Parsing:** PyMuPDF (`fitz`) extracts textual content, document metadata, section headers, tables, and page boundaries.
2. **Deterministic Chunking (`Code/chunking/hld_chunker.py`):** Structured chunking with semantic boundaries (SWC definitions, interface tables, signal specifications) rather than blind character sliding windows.
3. **Embeddings & Vector Indexing (`Code/embeddings/` & `Code/vectorstore/`):** Dense embeddings generated with `BAAI/bge-small-en-v1.5` (384 dims) and indexed in FAISS with metadata tracking (version, page, section).
4. **Keyword BM25 Indexing:** BM25 corpus indexed for exact architectural token matching (`SWC`, `Sender-Receiver`, `VehicleControl`).
5. **Multi-Signal Hybrid Retrieval:** Combined using Reciprocal Rank Fusion (RRF) with version-aware filtering.
