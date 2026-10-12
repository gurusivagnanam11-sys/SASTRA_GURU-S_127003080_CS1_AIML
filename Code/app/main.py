"""FastAPI Service for AUTOSAR HLD Intelligence & Traceability Assistant.

Provides REST API endpoints for:
- Health and index status check
- Grounded RAG query execution (direct and LangChain)
- Document catalog and re-indexing
- Engineer review recording
- Component & Interface architecture extraction with provenance
- JSON & Markdown report export
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, status, Request, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
from app.config import (
    EMBEDDING_MODEL,
    GEMINI_MODEL,
    INDEX_DIR,
    LLM_PROVIDER,
    OLLAMA_MODEL,
    TOP_K,
)
from db.repository import HLDRepository
from analysis.impact_analysis import get_impact_analyzer
from analysis.revision_diff import get_revision_diff_engine

from app.config import RAW_DATA_DIR, PROJECT_ID, PROCESSED_DATA_DIR
from ingestion.pdf_parser import parse_pdf
from chunking.hld_chunker import chunk_document
from pathlib import Path
import shutil
import time
from db.repository import HLDRepository
from ingestion.metadata import create_metadata, save_processed_document

from extraction.basic_extractor import (
    ArchitectureCatalog,
    ExtractedComponent,
    ExtractedInterface,
    get_architecture_extractor,
)
from extraction.models import (
    ArchitectureGraph,
    CompleteArchitectureModel,
    ComprehensiveImpactReport,
    ExtractedDependency,
    ExtractedFunctionalFlow,
    ExtractedPort,
    ExtractedSignal,
    RevisionDiffResult,
)
from rag.export import export_response_to_json, export_response_to_markdown
from analysis.architecture_validator import validate_architecture, ValidationResult
from rag.langchain_rag import LangChainRAGChain
from rag.llm_provider import get_llm_provider
from rag.models import Citation, Claim, ConfidenceLevel, QueryRequest, RAGResponse
from rag.pipeline import get_pipeline
from evaluation.benchmark import BenchmarkRunner, get_or_run_benchmark, load_benchmark_results
from evaluation.dataset import get_benchmark_dataset, get_unsupported_dataset

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AUTOSAR HLD Intelligence & Traceability Assistant",
    description="Grounded RAG and Architecture Intelligence for AUTOSAR High-Level Design specifications.",
    version="2.0.0",
)

# Enable CORS for Streamlit or web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

class APIQueryRequest(BaseModel):
    """Query request model with provider and framework overrides."""
    question: str = Field(..., max_length=5000, description="Natural language question about AUTOSAR HLD")
    project: Optional[str] = Field(None, description="Optional project filter")
    document_version: Optional[str] = Field(None, description="Optional version filter ('1.0', '2.0')")
    chunk_type: Optional[str] = Field(None, description="Optional chunk type filter")
    top_k: int = Field(default=TOP_K, ge=1, le=50, description="Max chunks to retrieve")
    provider: Optional[str] = Field(None, description="LLM provider: 'ollama', 'gemini', or 'mock'")
    use_langchain: bool = Field(default=False, description="Whether to route through LangChain chain")
    retriever_mode: Optional[str] = Field("hybrid", description="Retrieval strategy: 'hybrid' or 'baseline'")


class ReviewSubmission(BaseModel):
    """Engineer review submission model."""
    question: str = Field(..., description="Query being reviewed")
    decision: str = Field(..., description="Decision: 'accepted', 'rejected', or 'modified'")
    engineer_id: str = Field(default="engineer_1", description="Identifier of reviewing engineer")
    feedback: Optional[str] = Field(None, description="Reviewer feedback or rationale")
    corrections: Optional[str] = Field(None, description="Corrected architecture facts if modified")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    embedding_model: str
    default_llm_provider: str
    active_llm_model: str
    faiss_indexed_chunks: int
    metadata_catalog_chunks: int
    available_versions: List[str]


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Verify system health, vector index status, and available versions."""
    try:
        pipeline = get_pipeline()
        faiss_count = pipeline.faiss_store.count
        meta_count = pipeline.metadata_store.count
        versions = sorted(list(set(
            str(e.get("version")) for e in pipeline.metadata_store.entries if e.get("version")
        )))
    except Exception as e:
        logger.warning(f"Health check index warning: {e}")
        faiss_count = 0
        meta_count = 0
        versions = []

    active_model = OLLAMA_MODEL if LLM_PROVIDER == "ollama" else GEMINI_MODEL

    return HealthResponse(
        status="healthy",
        embedding_model=EMBEDDING_MODEL,
        default_llm_provider=LLM_PROVIDER,
        active_llm_model=active_model,
        faiss_indexed_chunks=faiss_count,
        metadata_catalog_chunks=meta_count,
        available_versions=versions,
    )


@app.post("/query", response_model=RAGResponse)
def run_query(request: APIQueryRequest):
    """Execute grounded question answering over AUTOSAR HLD documents.

    Supports optional provider override and LangChain orchestration.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query question cannot be empty.",
        )

    pipeline = get_pipeline(provider_name=request.provider)
    mode = request.retriever_mode or "hybrid"

    if request.use_langchain:
        provider = get_llm_provider(request.provider)
        chain = LangChainRAGChain(pipeline=pipeline, llm_provider=provider)
        response = chain.query(
            question=request.question,
            project=request.project,
            version=request.document_version,
            chunk_type=request.chunk_type,
            top_k=request.top_k,
            retriever_mode=mode,
        )
    else:
        response = pipeline.ask(
            question=request.question,
            project=request.project,
            document_version=request.document_version,
            chunk_type=request.chunk_type,
            top_k=request.top_k,
            retriever_mode=mode,
        )

    return response


@app.get("/documents")
def list_documents():
    """List indexed documents, versions, and statistical summaries."""
    repo = HLDRepository()
    try:
        repo_docs = repo.get_documents()
        repo_stats = repo.get_stats()
    except Exception:
        repo_docs = []
        repo_stats = {}

    pipeline = get_pipeline()
    entries = pipeline.metadata_store.entries

    # Group by version and document_id
    versions = set()
    doc_ids = set()
    by_version: Dict[str, int] = {}
    for e in entries:
        v = str(e.get("version", ""))
        d = str(e.get("document_id", ""))
        if v:
            versions.add(v)
            by_version[v] = by_version.get(v, 0) + 1
        if d:
            doc_ids.add(d)

    return {
        "status": "success",
        "total_chunks": len(entries),
        "versions": sorted(list(versions)),
        "document_ids": sorted(list(doc_ids)),
        "chunks_per_version": by_version,
        "database_stats": repo_stats,
        "documents": repo_docs,
    }

INDEXING_JOBS: Dict[str, Dict[str, Any]] = {}

@app.get("/documents/indexing_status/{job_id}")
def get_indexing_status(job_id: str):
    """Get the status of a background indexing job."""
    if job_id not in INDEXING_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return INDEXING_JOBS[job_id]

def incremental_index_update(chunks: List[Any], job_id: str):
    """Background task to incrementally embed new chunks and update FAISS."""
    try:
        INDEXING_JOBS[job_id]["status"] = "in_progress"
        INDEXING_JOBS[job_id]["message"] = "Loading pipeline and filtering existing chunks..."
        
        pipeline = get_pipeline()
        metadata_store = pipeline.metadata_store
        faiss_store = pipeline.faiss_store
        embedder = pipeline.embedder
        
        # Filter out chunks that are already in the metadata store
        new_chunks = []
        for c in chunks:
            chunk_id = c.get("chunk_id") if isinstance(c, dict) else c.chunk_id
            if not metadata_store.get_by_chunk_id(chunk_id):
                new_chunks.append(c)
                
        if not new_chunks:
            INDEXING_JOBS[job_id]["status"] = "completed"
            INDEXING_JOBS[job_id]["message"] = "No new chunks to index."
            INDEXING_JOBS[job_id]["progress"] = "100%"
            return
            
        INDEXING_JOBS[job_id]["message"] = f"Embedding {len(new_chunks)} new chunks..."
        logger.info(f"Job {job_id}: Embedding {len(new_chunks)} new chunks...")
        
        texts = [c.get("text") if isinstance(c, dict) else c.text for c in new_chunks]
        
        # Batch embed and track progress
        batch_size = 32
        import numpy as np
        all_vectors = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_vecs = embedder.embed_documents(batch_texts, batch_size=batch_size)
            all_vectors.append(batch_vecs)
            
            progress = min(100, int((i + len(batch_texts)) / len(texts) * 100))
            INDEXING_JOBS[job_id]["progress"] = f"{progress}%"
            logger.info(f"Job {job_id} embedding progress: {min(i + len(batch_texts), len(texts))}/{len(texts)}")
            
        vectors_arr = np.vstack(all_vectors)
        
        INDEXING_JOBS[job_id]["message"] = "Updating FAISS index and metadata..."
        faiss_store.add_vectors(vectors_arr)
        
        for c in new_chunks:
            metadata_store.add_chunk(c)
            
        # Save securely
        from app.config import INDEX_DIR
        faiss_path = INDEX_DIR / "hld_index.faiss"
        metadata_path = INDEX_DIR / "hld_metadata.json"
        
        faiss_store.save(faiss_path)
        metadata_store.save(metadata_path)
        
        INDEXING_JOBS[job_id]["status"] = "completed"
        INDEXING_JOBS[job_id]["message"] = "Indexing completed successfully."
        INDEXING_JOBS[job_id]["progress"] = "100%"
        logger.info(f"Job {job_id}: Indexing completed for {len(new_chunks)} chunks.")
        
    except Exception as e:
        logger.error(f"Job {job_id}: Background indexing failed: {e}", exc_info=True)
        INDEXING_JOBS[job_id]["status"] = "failed"
        INDEXING_JOBS[job_id]["message"] = f"Error: {str(e)}"

@app.post("/documents/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    version: str = Form(...),
    governance_status: str = Form("DRAFT")
):
    """Upload, parse, chunk, and index a new HLD PDF document."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    filename = Path(file.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
        
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DATA_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")
        
    try:
        start_time = time.time()
        # Parse PDF
        doc_data = parse_pdf(file_path, PROJECT_ID, version)
        
        # Chunk document
        chunks = chunk_document(doc_data)
        
        # Metadata
        if not doc_data.metadata:
            doc_data.metadata = create_metadata(doc_data)
            
        # Set governance status
        try:
            from reports.models import DocumentStatus
            from reports.generator import set_governance_status
            
            # Map string to enum
            status_enum = DocumentStatus(governance_status.upper())
            set_governance_status(doc_data.metadata.document_id, status_enum, "system")
            
            repo = HLDRepository()
            repo.save_governance_change(
                document_id=doc_data.metadata.document_id,
                old_status=None,
                new_status=status_enum.value,
                changed_by="system",
                reason="Initial upload"
            )
        except Exception as e:
            logger.warning(f"Could not set initial governance status: {e}")
        
        # Save processed data
        save_processed_document(doc_data, PROCESSED_DATA_DIR)
        
        # Save to DB
        repo = HLDRepository()
        repo.init_db()
        repo.save_document(doc_data.metadata)
        repo.save_chunks(chunks)
        
        # Trigger incremental index update in background
        job_id = f"job_{int(time.time())}_{filename}"
        INDEXING_JOBS[job_id] = {"status": "queued", "message": "Waiting to start...", "progress": "0%"}
        background_tasks.add_task(incremental_index_update, chunks, job_id)
        
        return {
            "status": "upload_successful",
            "job_id": job_id,
            "document": filename,
            "version": version,
            "pages": getattr(doc_data.metadata, "page_count", 0),
            "chunks": len(chunks),
            "ocr_pages": getattr(doc_data.metadata, "ocr_pages", 0),
            "tables": getattr(doc_data.metadata, "table_count", 0),
            "embedding_status": "queued",
            "faiss_status": "queued",
            "message": "Upload successful, indexing queued in background."
        }
    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@app.post("/documents/index")
def trigger_indexing():
    """Rebuild or reload the FAISS index and metadata store from fixtures."""
    import subprocess
    import sys
    from app.config import PROJECT_ROOT

    script_path = PROJECT_ROOT / "scripts" / "build_index.py"
    if not script_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Index build script not found at {script_path}",
        )

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Index build script failed: {proc.stderr}")

        # Reload singleton pipeline
        from rag.pipeline import _default_pipeline
        import rag.pipeline as rag_module
        rag_module._default_pipeline = None

        new_pipe = get_pipeline()
        return {
            "status": "success",
            "message": "Index built and loaded successfully.",
            "indexed_chunks": new_pipe.faiss_store.count,
        }
    except Exception as e:
        logger.error(f"Re-indexing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-indexing failed: {str(e)}",
        )


@app.post("/review")
def record_review(review: ReviewSubmission):
    """Record an engineer review decision and feedback."""
    repo = HLDRepository()
    try:
        saved = repo.save_review(
            question=review.question,
            decision=review.decision,
            engineer_id=review.engineer_id,
            feedback=review.feedback,
            corrections=review.corrections,
        )
        return {
            "status": "success",
            "message": "Review recorded successfully.",
            "review": saved,
        }
    except Exception as e:
        logger.error(f"Failed to record review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record review: {str(e)}",
        )


@app.get("/reviews")
def list_reviews(limit: int = Query(50, ge=1, le=500)):
    """Fetch recorded engineer reviews."""
    repo = HLDRepository()
    try:
        reviews = repo.get_reviews(limit=limit)
        return {"status": "success", "count": len(reviews), "reviews": reviews}
    except Exception as e:
        logger.error(f"Failed to fetch reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reviews: {str(e)}",
        )


@app.get("/entities/components", response_model=List[ExtractedComponent])
def get_components(version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')")):
    """Extract and list Software Components with full provenance."""
    extractor = get_architecture_extractor()
    return extractor.extract_components(version=version)


@app.get("/entities/interfaces", response_model=List[ExtractedInterface])
def get_interfaces(version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')")):
    """Extract and list Interfaces with full provenance."""
    extractor = get_architecture_extractor()
    return extractor.extract_interfaces(version=version)


@app.get("/entities/catalog", response_model=ArchitectureCatalog)
def get_architecture_catalog(version: Optional[str] = Query(None, description="Optional version filter")):
    """Extract full architecture catalog (components + interfaces) with provenance."""
    extractor = get_architecture_extractor()
    return extractor.extract_catalog(version=version)


# ==========================================
# Phase 3: Architecture Intelligence Endpoints
# ==========================================


@app.get("/architecture")
def get_architecture_summary():
    """Summary overview of extracted architecture across all versions and endpoints."""
    extractor = get_architecture_extractor()
    v1_model = extractor.get_complete_model("1.0")
    v2_model = extractor.get_complete_model("2.0")
    return {
        "status": "success",
        "description": "AUTOSAR High-Level Design Architecture Intelligence Model",
        "versions": {
            "1.0": {
                "components_count": len(v1_model.components),
                "interfaces_count": len(v1_model.interfaces),
                "ports_count": len(v1_model.ports),
                "signals_count": len(v1_model.signals),
                "dependencies_count": len(v1_model.dependencies),
                "flows_count": len(v1_model.functional_flows),
            },
            "2.0": {
                "components_count": len(v2_model.components),
                "interfaces_count": len(v2_model.interfaces),
                "ports_count": len(v2_model.ports),
                "signals_count": len(v2_model.signals),
                "dependencies_count": len(v2_model.dependencies),
                "flows_count": len(v2_model.functional_flows),
            },
        },
        "endpoints": [
            "/architecture/components",
            "/architecture/interfaces",
            "/architecture/ports",
            "/architecture/signals",
            "/architecture/dependencies",
            "/architecture/flows",
            "/architecture/graph",
            "/architecture/model",
            "/architecture/diff",
            "/architecture/impact",
        ],
    }


@app.get("/architecture/components", response_model=List[ExtractedComponent])
def get_architecture_components(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
):
    """Extract and list Software Components (SWCs) with full provenance."""
    extractor = get_architecture_extractor()
    return extractor.extract_components(version=version)


@app.get("/architecture/interfaces", response_model=List[ExtractedInterface])
def get_architecture_interfaces(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
):
    """Extract and list Interfaces with full provenance."""
    extractor = get_architecture_extractor()
    return extractor.extract_interfaces(version=version)


@app.get("/architecture/ports", response_model=List[ExtractedPort])
def get_architecture_ports(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
    component: Optional[str] = Query(None, description="Filter by component name"),
):
    """Extract and list Port definitions with component, direction, and interface binding."""
    extractor = get_architecture_extractor()
    return extractor.extract_ports(version=version, component=component)


@app.get("/architecture/signals", response_model=List[ExtractedSignal])
def get_architecture_signals(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
    interface: Optional[str] = Query(None, description="Filter by carrier interface"),
):
    """Extract and list Signals with data types, units, and source/destination routing."""
    extractor = get_architecture_extractor()
    return extractor.extract_signals(version=version, interface_name=interface)


@app.get("/architecture/dependencies", response_model=List[ExtractedDependency])
def get_architecture_dependencies(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
    component: Optional[str] = Query(None, description="Filter by source or target component"),
):
    """Extract and list Component Dependencies with relationship types and descriptions."""
    extractor = get_architecture_extractor()
    return extractor.extract_dependencies(version=version, component=component)


@app.get("/architecture/flows", response_model=List[ExtractedFunctionalFlow])
def get_architecture_flows(
    version: Optional[str] = Query(None, description="Optional version filter ('1.0', '2.0')"),
):
    """Extract and list Functional Flows (Sensor Data Flow, Diagnostic Flow)."""
    extractor = get_architecture_extractor()
    return extractor.extract_flows(version=version)


@app.get("/architecture/graph", response_model=ArchitectureGraph)
def get_architecture_graph(
    version: str = Query("2.0", description="Architecture release version ('1.0', '2.0')"),
):
    """Get the complete Architecture Traceability Graph with typed nodes and edges."""
    extractor = get_architecture_extractor()
    return extractor.build_graph(version=version)


@app.get("/architecture/model", response_model=CompleteArchitectureModel)
def get_complete_architecture_model(
    version: str = Query("2.0", description="Architecture release version ('1.0', '2.0')"),
):
    """Get the complete consolidated Architecture Model for a specified version."""
    extractor = get_architecture_extractor()
    return extractor.get_complete_model(version=version)


@app.get("/architecture/diff", response_model=RevisionDiffResult)
def get_revision_diff(
    v1: str = Query("1.0", description="Base HLD version"),
    v2: str = Query("2.0", description="Target HLD version"),
):
    """Deterministically compare two HLD revisions and detect all structural modifications."""
    diff_engine = get_revision_diff_engine()
    return diff_engine.compare_versions(base_version=v1, target_version=v2)


@app.get("/architecture/impact", response_model=ComprehensiveImpactReport)
def get_architecture_impact(
    v1: str = Query("1.0", description="Base HLD version"),
    v2: str = Query("2.0", description="Target HLD version"),
):
    """Run comprehensive impact analysis propagating changes across the architecture."""
    impact_analyzer = get_impact_analyzer()
    return impact_analyzer.generate_comprehensive_report(base_version=v1, target_version=v2)


@app.get("/architecture/validate", response_model=ValidationResult)
def validate_architecture_endpoint(
    version: str = Query("2.0", description="Architecture release version ('1.0', '2.0')"),
):
    """Run deterministic structural architecture validation (inconsistency & completeness)."""
    extractor = get_architecture_extractor()
    model = extractor.get_complete_model(version=version)
    return validate_architecture(model)



# ==========================================
# Phase 4: Engineering Evaluation Endpoints
# ==========================================


@app.get("/evaluation/summary")
def get_evaluation_summary():
    """High-level KPI executive summary of retrieval, grounding, citation, and abstention benchmarks."""
    data = get_or_run_benchmark(force_recompute=False)
    return {
        "status": "success",
        "benchmark_timestamp": data.get("timestamp"),
        "key_metrics": data.get("key_metrics_summary", {}),
        "dataset_stats": data.get("dataset", {}),
        "latencies": data.get("latency_benchmarks", {}),
    }


@app.get("/evaluation/retrieval")
def get_retrieval_evaluation():
    """Information Retrieval evaluation comparing Baseline (Dense FAISS) vs Hybrid Retriever."""
    data = get_or_run_benchmark(force_recompute=False)
    retrieval_data = data.get("retrieval_evaluation", {})
    return {
        "status": "success",
        "baseline": retrieval_data.get("baseline", {}),
        "hybrid": retrieval_data.get("hybrid", {}),
        "deltas": retrieval_data.get("deltas", {}),
        "category_breakdown": retrieval_data.get("category_breakdown", {}),
        "itemized": retrieval_data.get("itemized_comparison", []),
    }


@app.get("/evaluation/grounding")
def get_grounding_evaluation():
    """Evaluation of claim-level groundedness (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED)."""
    data = get_or_run_benchmark(force_recompute=False)
    gen_data = data.get("generation_evaluation", {})
    return {
        "status": "success",
        "macro_averages": gen_data.get("macro_averages", {}),
        "itemized": gen_data.get("itemized", []),
    }


@app.get("/evaluation/citations")
def get_citation_evaluation():
    """Evaluation of citation precision, coverage, and review gating metrics."""
    data = get_or_run_benchmark(force_recompute=False)
    gen_data = data.get("generation_evaluation", {})
    itemized = [
        {
            "query_id": it["query_id"],
            "query": it["query"],
            "citation_count": it["citation_count"],
            "citation_precision": it["citation_precision"],
            "citation_coverage": it["citation_coverage"],
            "review_required": it["review_required"],
            "confidence": it.get("confidence"),
        }
        for it in gen_data.get("itemized", [])
    ]
    return {
        "status": "success",
        "citation_precision": data.get("key_metrics_summary", {}).get("citation_precision"),
        "citation_coverage": data.get("key_metrics_summary", {}).get("citation_coverage"),
        "macro_averages": {
            "mean_citation_precision": gen_data.get("macro_averages", {}).get("mean_citation_precision"),
            "mean_citation_coverage": gen_data.get("macro_averages", {}).get("mean_citation_coverage"),
        },
        "itemized": itemized,
    }


@app.get("/evaluation/abstention")
def get_abstention_evaluation():
    """Adversarial and unsupported query evaluation checking abstention accuracy and hallucination rate."""
    data = get_or_run_benchmark(force_recompute=False)
    abs_data = data.get("abstention_evaluation", {})
    return {
        "status": "success",
        "abstention_accuracy": abs_data.get("abstention_accuracy"),
        "hallucination_rate": abs_data.get("hallucination_rate"),
        "total_evaluated": abs_data.get("total_queries"),
        "total_abstained": abs_data.get("correctly_abstained"),
        "total_hallucinated": abs_data.get("hallucinated"),
        "adversarial_results": abs_data.get("itemized", []),
    }


@app.get("/evaluation/benchmark")
def get_full_benchmark_report():
    """Return complete raw benchmark results JSON."""
    data = get_or_run_benchmark(force_recompute=False)
    return data


@app.get("/evaluation/providers")
def get_providers_profile():
    """Technical profile of supported LLM providers: Ollama (private/local), Gemini (cloud/demo), Mock (test)."""
    return {
        "status": "success",
        "active_provider": LLM_PROVIDER,
        "providers": {
            "ollama": {
                "role": "PRIMARY private/local LLM",
                "model": OLLAMA_MODEL,
                "privacy": "100% on-premise, no cloud egress",
                "target_environment": "Engineering workstation / offline lab",
            },
            "gemini": {
                "role": "OPTIONAL cloud demo/development provider",
                "model": GEMINI_MODEL,
                "privacy": "Cloud API (requires Google AI API key)",
                "target_environment": "Cloud demo, rapid prototyping",
            },
            "mock": {
                "role": "DETERMINISTIC CI / offline test provider",
                "model": "rule-based deterministic mock",
                "privacy": "Zero external dependencies",
                "target_environment": "CI/CD automated regression tests",
            },
        },
    }


@app.post("/evaluation/run")
def recompute_benchmark(force: bool = Query(True, description="Force recomputation of benchmarks")):
    """Trigger execution of full benchmark harness and return updated metrics."""
    try:
        results = get_or_run_benchmark(force_recompute=force)
        return {
            "status": "success",
            "message": "Benchmark recomputed successfully.",
            "benchmark": results,
        }
    except Exception as e:
        logger.error(f"Benchmark execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}",
        )


# ==========================================
# Phase 8: Engineering Reports & Governance
# ==========================================

from reports.models import (
    ComponentReport,
    DocumentGovernance,
    DocumentStatus,
    EngineeringReview,
    ImpactReport,
    ReportCatalog,
    ReviewDecision,
    RevisionReport,
    ValidationReport as ValidationReportModel,
)
from reports.generator import (
    generate_component_report,
    generate_impact_report,
    generate_revision_report,
    generate_validation_report,
    get_active_version,
    get_all_governance,
    get_governance,
    set_governance_status,
)
from reports.export import (
    export_report_json,
    export_report_md,
    export_validation_findings_csv,
    export_revision_changes_csv,
)


class EngineeringReviewRequest(BaseModel):
    """Request body for submitting an engineering review."""
    report_type: str = Field(..., description="Type: component_report, validation_report, revision_report, impact_report")
    report_identifier: str = Field(..., description="Entity or query being reviewed")
    reviewer: str = Field(default="Engineering Reviewer", description="Reviewer name")
    decision: str = Field(..., description="ENGINEER_APPROVED, ENGINEER_CORRECTED, ENGINEER_REJECTED")
    comment: Optional[str] = Field(None, description="Review comment")
    correction: Optional[str] = Field(None, description="Correction text if ENGINEER_CORRECTED")
    source_document: Optional[str] = Field(None, description="Source document name")
    source_version: Optional[str] = Field(None, description="Source document version")
    original_result_summary: Optional[str] = Field(None, description="Summary of original AI/analysis result")


class GovernanceStatusRequest(BaseModel):
    """Request body for changing document governance status."""
    status: str = Field(..., description="APPROVED, DRAFT, or ARCHIVED")
    changed_by: str = Field(default="Engineering Reviewer", description="Who changed the status")
    reason: Optional[str] = Field(None, description="Reason for status change")


@app.get("/reports/catalog", response_model=ReportCatalog)
def get_report_catalog():
    """List available report types, export formats, and governance options."""
    return ReportCatalog()


@app.get("/reports/component/{component_name}", response_model=ComponentReport)
def get_component_report(
    component_name: str,
    version: Optional[str] = Query(None, description="HLD version ('1.0', '2.0')"),
):
    """Generate a structured engineering report for a specific AUTOSAR SWC."""
    report = generate_component_report(component_name=component_name, version=version)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component '{component_name}' not found in version '{version or get_active_version()}'.",
        )
    return report


@app.get("/reports/validation", response_model=ValidationReportModel)
def get_validation_report(
    version: Optional[str] = Query(None, description="HLD version ('1.0', '2.0')"),
):
    """Generate a structured validation report using the Phase 7 validator."""
    return generate_validation_report(version=version)


@app.get("/reports/revision", response_model=RevisionReport)
def get_revision_report(
    v1: str = Query("1.0", description="Source HLD version"),
    v2: str = Query("2.0", description="Target HLD version"),
):
    """Generate a structured revision comparison report."""
    return generate_revision_report(source_version=v1, target_version=v2)


@app.get("/reports/impact", response_model=ImpactReport)
def get_impact_report(
    v1: str = Query("1.0", description="Base HLD version"),
    v2: str = Query("2.0", description="Target HLD version"),
):
    """Generate a structured impact analysis report."""
    return generate_impact_report(base_version=v1, target_version=v2)


@app.post("/reports/reviews")
def submit_engineering_review(review: EngineeringReviewRequest):
    """Submit an engineering review decision for a report or finding."""
    valid_decisions = {"ENGINEER_APPROVED", "ENGINEER_CORRECTED", "ENGINEER_REJECTED", "PENDING_REVIEW"}
    if review.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{review.decision}'. Must be one of: {sorted(valid_decisions)}",
        )

    repo = HLDRepository()
    try:
        saved = repo.save_engineering_review(
            report_type=review.report_type,
            report_identifier=review.report_identifier,
            decision=review.decision,
            reviewer=review.reviewer,
            comment=review.comment,
            correction=review.correction,
            source_document=review.source_document,
            source_version=review.source_version,
            original_result_summary=review.original_result_summary,
        )
        return {"status": "success", "message": "Engineering review recorded.", "review": saved}
    except Exception as e:
        logger.error(f"Failed to save engineering review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save engineering review: {str(e)}",
        )


@app.get("/reports/reviews")
def list_engineering_reviews(limit: int = Query(50, ge=1, le=500)):
    """List engineering review records."""
    repo = HLDRepository()
    try:
        reviews = repo.get_engineering_reviews(limit=limit)
        return {"status": "success", "count": len(reviews), "reviews": reviews}
    except Exception as e:
        logger.error(f"Failed to fetch engineering reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch engineering reviews: {str(e)}",
        )


@app.get("/governance/documents")
def list_governance_documents():
    """List all document governance entries with status."""
    docs = get_all_governance()
    return {
        "status": "success",
        "active_version": get_active_version(),
        "documents": [d.model_dump() for d in docs],
    }


@app.get("/governance/documents/{document_id}")
def get_governance_document(document_id: str):
    """Get governance status for a specific document."""
    gov = get_governance(document_id)
    if gov is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in governance store.",
        )
    return {"status": "success", "document": gov.model_dump()}


@app.post("/governance/documents/{document_id}/status")
def update_governance_status(document_id: str, request: GovernanceStatusRequest):
    """Update the governance status for a document."""
    valid_statuses = {"APPROVED", "DRAFT", "ARCHIVED"}
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{request.status}'. Must be one of: {sorted(valid_statuses)}",
        )

    # Get old status for audit trail
    old_gov = get_governance(document_id)
    if old_gov is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found in governance store.",
        )
    old_status = old_gov.status.value

    updated = set_governance_status(
        document_id=document_id,
        new_status=DocumentStatus(request.status),
        changed_by=request.changed_by,
    )

    # Record in audit trail
    repo = HLDRepository()
    try:
        repo.save_governance_change(
            document_id=document_id,
            old_status=old_status,
            new_status=request.status,
            changed_by=request.changed_by,
            reason=request.reason,
        )
    except Exception as e:
        logger.warning(f"Governance audit trail write failed: {e}")

    return {
        "status": "success",
        "message": f"Document '{document_id}' status changed from {old_status} to {request.status}.",
        "document": updated.model_dump() if updated else None,
    }


@app.get("/governance/audit")
def get_governance_audit(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    limit: int = Query(50, ge=1, le=500),
):
    """Fetch the governance audit trail."""
    repo = HLDRepository()
    try:
        audit = repo.get_governance_audit(document_id=document_id, limit=limit)
        return {"status": "success", "count": len(audit), "audit": audit}
    except Exception as e:
        logger.error(f"Failed to fetch governance audit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch governance audit: {str(e)}",
        )
