# Capstone Project Synopsis: AUTOSAR HLD Intelligence & Traceability Assistant

**Student Name:** GURU S<br/>
**Register Number:** 127003080<br/>
**Department:** Computer Science & Engineering (AI & ML)<br/>
**Institution:** SASTRA Deemed to be University<br/>
**Project Title:** AUTOSAR HLD Intelligence & Traceability Assistant: Architecture-Aware Retrieval-Augmented Generation with Deterministic Verification for Automotive Software Specifications

---

## 1. Executive Summary

Automotive software engineering requires stringent compliance with architectural standards such as AUTOSAR Classic and Adaptive platforms. High-Level Design (HLD) specifications govern critical Electronic Control Unit (ECU) topologies, Software Component (SWC) ports, signal routing, and safety interfaces. However, manual inspection and cross-version traceability across multi-hundred-page HLD releases (e.g., v1.0 to v2.0) are error-prone, labor-intensive, and susceptible to severe hallucinations when queried using generic large language model (LLM) chatbots.

This capstone project presents the **AUTOSAR HLD Intelligence & Traceability Assistant**, an enterprise-grade, architecture-aware Retrieval-Augmented Generation (RAG) system engineered specifically for automotive systems engineering. The system integrates:
1. **Multi-Signal Hybrid Retrieval:** Combining dense semantic search (FAISS + `BAAI/bge-small-en-v1.5`) with exact architectural keyword search (BM25) fused via Reciprocal Rank Fusion (RRF, $k=60$).
2. **Deterministic Architecture Validation:** An Abstract Syntax Tree (AST) architectural validator capable of identifying unmapped ports, unresolved signals, cycle dependencies, and cross-version interface diffs.
3. **Grounding & Citation Verification:** A multi-stage validator ensuring every cited chunk ID exists in retrieved context, maps to the correct document/version/page, and supports the claimed assertion without hallucination.
4. **Honest Abstention Engine:** Low-confidence flagging (`review_required=True`) on out-of-scope or adversarial queries, ensuring zero hallucinations on unsupported automotive parameters.

---

## 2. Problem Statement & Research Objectives

1. **Information Retrieval Deficits in Generic RAG:** Dense vector embeddings alone fail to retrieve precise AUTOSAR entity identifiers (e.g., distinguishing `VehicleSpeed` in `VehicleDataInterface` from general speed references).
2. **Cross-Version Traceability Gaps:** Comparing architecture revisions (v1.0 vs. v2.0) frequently leads to temporal confusion, where attributes from v1.0 are attributed to v2.0 without explicit isolation.
3. **Hallucination in Safety-Critical Domains:** Automotive engineering cannot tolerate unverified assertions or fabricated citations.
4. **Research Objectives:**
   - Develop an architecture-aware chunking and hybrid retrieval strategy outperforming standard dense retrieval.
   - Implement deterministic rule-based verification to validate architecture topology independently of LLM biases.
   - Formulate an evaluation harness benchmarked with RAGAS metrics and adversarial abstention tests.

---

## 3. System Architecture & Methodology

The system is constructed around four interconnected tiers:
1. **Document Ingestion & Chunking Tier:** PyMuPDF extraction, semantic header preservation, and architectural chunking retaining component boundaries and table structures.
2. **Retrieval & Fusion Tier:** Dual FAISS dense and BM25 sparse indices, query routing (canonical architecture vs. general exploration), and cross-version balanced retrieval.
3. **Reasoning & Validation Tier:** Local LLM inference (Ollama `qwen2.5:3b`) and cloud fallback (Google Gemini 3.7 Flash), structured JSON output parser with resilient repair, citation validator, and claim-level grounding checker.
4. **Presentation & Governance Tier:** High-contrast Streamlit enterprise engineering console, FastAPI REST backend, document governance lifecycle (Draft, Review, Approved), and exportable engineering compliance reports.

---

## 4. Key Results & Achievements

- **Retrieval Recall@5:** Elevated from 58.33% (Baseline Dense) to **83.33%** (Architecture-Aware Hybrid), a **+25.0 percentage point gain**.
- **Mean Reciprocal Rank (MRR):** Improved from 0.7500 to **1.0000** (+0.2500), placing the primary architectural definition chunk at rank 1 across benchmark queries.
- **Hallucination Prevention:** Achieved **100% clean abstention** across 10 adversarial/unsupported automotive queries with zero unsupported claims.
- **Verification Integrity:** 43 automated unit and regression tests passing with 100% success rate across architecture routing, validation, and RAGAS pipeline adapters.
