import sys
import os
import pymupdf

sys.path.insert(0, os.path.abspath("scripts"))
from diagram_part1 import get_header_and_defs
from diagram_part2 import get_stage1
from diagram_part3 import get_stage2
from diagram_part4 import get_stage3_and_4
from diagram_part5 import get_stage5_and_validator
from diagram_part6 import get_part6

os.makedirs("Documentation", exist_ok=True)

full_svg = (
    get_header_and_defs() + "\n" +
    get_stage1() + "\n" +
    get_stage2() + "\n" +
    get_stage3_and_4() + "\n" +
    get_stage5_and_validator() + "\n" +
    get_part6()
)

svg_path = "Documentation/RAG_Workflow.svg"
with open(svg_path, "w", encoding="utf-8") as f:
    f.write(full_svg)
print(f"Wrote {svg_path} (length: {len(full_svg)} chars)")

# Render to PNG using PyMuPDF
doc = pymupdf.open("svg", full_svg.encode("utf-8"))
page = doc[0]
pix = page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25))
png_path = "Documentation/RAG_Workflow.png"
pix.save(png_path)
print(f"Rendered {png_path} ({pix.width}x{pix.height} px, {os.path.getsize(png_path)} bytes)")

# Create Mermaid source counterpart
mermaid_content = """```mermaid
flowchart TD
    %% Global Styling
    classDef ingestion fill:#EFF6FF,stroke:#3B82F6,stroke-width:1.5px,color:#1E3A8A;
    classDef retrieval fill:#F0FDF4,stroke:#10B981,stroke-width:1.5px,color:#065F46;
    classDef inference fill:#F5F3FF,stroke:#8B5CF6,stroke-width:1.5px,color:#4C1D95;
    classDef validation fill:#FEF2F2,stroke:#EF4444,stroke-width:1.5px,color:#991B1B;
    classDef output fill:#FFFBEB,stroke:#F59E0B,stroke-width:1.5px,color:#92400E;
    classDef storage fill:#F8FAFC,stroke:#64748B,stroke-width:1.5px,color:#0F172A;

    subgraph PHASE_1["Phase 1: Document Ingestion & Vector Indexing (Offline Pipeline)"]
        A[HLD PDF Upload: AUTOSAR Specs]:::ingestion --> B[PyMuPDF Text & Table Extraction]:::ingestion
        B -->|Scanned / Corrupt Page?| C{Text < 50 chars?}:::ingestion
        C -->|Yes: OCR Fallback| D[Tesseract OCR Engine<br/>ingestion/ocr_parser.py]:::ingestion
        C -->|No| E[Structured Page Content]:::ingestion
        D --> E
        E --> F[AUTOSAR HLD Chunker<br/>chunking/hld_chunker.py<br/>500-1500 tokens, 100 overlap]:::ingestion
        F --> G[(Metadata Extraction<br/>Doc, Page, Section, Version, Entities)]:::storage
        F --> H[BGE-small-en-v1.5 Embedder<br/>embeddings/embedder.py<br/>384-dimensional normalized vectors]:::ingestion
        H --> I[(FAISS Vector Index<br/>IndexFlatIP Cosine Similarity<br/>data/indexes/hld_index.faiss)]:::storage
        G --> J[(SQLite Metadata Database<br/>data/autosar_hld.db)]:::storage
    end

    subgraph PHASE_2["Phase 2: User Query & Multi-Stage Retrieval (Online Pipeline)"]
        U[User Query via Streamlit UI :8501]:::output --> K[FastAPI Backend :8000<br/>POST /rag/query]:::retrieval
        K --> L[Security & Sanitization<br/>Prompt Injection & Path Validation]:::validation
        L --> M{Retrieval Mode?}:::retrieval
        M -->|hybrid mode| N[Hybrid Retriever<br/>rag/hybrid_retriever.py]:::retrieval
        M -->|baseline mode| O[Baseline FAISS Retriever<br/>Cosine Similarity top_k=5]:::retrieval
        N --> P[Candidate Pool Generation<br/>N=100 candidate chunks]:::retrieval
        P --> Q[Tri-Factor Scoring Formula<br/>Score = 0.50*Sem + 0.30*Ent + 0.20*Sec]:::retrieval
        Q --> R[Cross-Version Balancing<br/>v4.2 vs v4.4 vs R20-11 Parity]:::retrieval
        R --> S[Top-K Ranked Context Assembly]:::retrieval
        O --> S
    end

    subgraph PHASE_3["Phase 3: Context Assembly & Model Inference"]
        S --> T[Prompt Builder<br/>rag/prompts.py: build_user_prompt<br/>Injects [C1]..[Cn] numbered contexts]:::inference
        T --> V[System Prompt Enforcement<br/>11 Automotive Engineering Rules]:::inference
        V --> W{Configured LLM Provider}:::inference
        W -->|Local Default| X[Ollama Local Engine<br/>qwen2.5:3b (Port 11434)]:::inference
        W -->|Cloud Fallback| Y[Google Gemini API<br/>gemini-3.7-flash (Official SDK)]:::inference
        X --> Z[Raw JSON Model Output]:::inference
        Y --> Z
    end

    subgraph PHASE_4["Phase 4: Deterministic Grounding & Dedicated Architecture Validation"]
        Z --> AA[Deterministic Grounding Checker<br/>rag/grounding_checker.py]:::validation
        AA --> AB{Grounding Checks}:::validation
        AB -->|Citation Extraction| AC[Verify [C1]..[Cn] match retrieved set]:::validation
        AB -->|Contradiction Check| AD[Detect explicit conflict keywords]:::validation
        AB -->|Overlap Metric| AE[Token Overlap >= 60% with context]:::validation
        AC --> AF[Assign Grounding Status<br/>GROUNDED | PARTIALLY | UNGROUNDED]:::validation
        AD --> AF
        AE --> AF
        AF -->|Low Confidence / Contradiction| AG[Flag review_required = true]:::validation

        K -.->|Optional GET /architecture/validate| AH[Dedicated Architecture Validator<br/>analysis/architecture_validator.py<br/>8 Structural Consistency Checks]:::validation
    end

    subgraph PHASE_5["Phase 5: Output Synthesis, UI Display & Governance Gating"]
        AF --> AI[Final RAGResponse Payload<br/>Answer, Sources, Grounding, Latency]:::output
        AG --> AI
        AI --> AJ[Streamlit UI Display<br/>Markdown Answer + Expandable Citations]:::output
        AJ --> AK[Human-in-the-Loop Review Form<br/>POST /reports/reviews to SQLite Audit]:::output
    end

    %% Storage connections
    I -.-> P
    I -.-> O
    J -.-> P
    AH -.-> AK
```
"""

mmd_path = "Documentation/RAG_Workflow.mmd"
with open(mmd_path, "w", encoding="utf-8") as f:
    f.write(mermaid_content)
print(f"Wrote {mmd_path}")
