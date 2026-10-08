"""Comprehensive unit and integration tests for Phase 2B.

Tests:
1. Free-Only LLM Providers (MockLLMProvider, OllamaProvider, GeminiProvider, factory)
2. LangChain RAG Orchestration (to_langchain_documents, HLDRetriever, LangChainRAGChain)
3. Architecture Extraction (SWCs, Interfaces, Provenance, Filtering)
4. Export Utilities (JSON and Markdown)
5. Pilot FastAPI Endpoints (health, query, documents, review, entities)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import INDEX_DIR
from app.main import app
from extraction.basic_extractor import (
    ArchitectureExtractor,
    ExtractedComponent,
    ExtractedInterface,
    get_architecture_extractor,
)
from rag.citation_validator import CitationValidator
from rag.export import export_response_to_json, export_response_to_markdown
from rag.langchain_rag import (
    HLDRetriever,
    LangChainRAGChain,
    format_documents_to_context,
    to_langchain_documents,
)
from rag.llm_provider import (
    GeminiProvider,
    MockLLMProvider,
    OllamaProvider,
    get_llm_provider,
)
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk, RAGResponse
from rag.pipeline import get_pipeline


# ==========================================
# 1. Free-Only LLM Provider Tests
# ==========================================


def test_mock_llm_provider_custom_response():
    """Verify MockLLMProvider returns injected custom response."""
    provider = MockLLMProvider()
    custom = {
        "answer": "Custom test answer.",
        "claims": [],
        "citations": [],
        "confidence": "high",
        "limitations": [],
        "review_required": False,
    }
    provider.set_custom_response(custom)
    res = provider.generate("sys", "user")
    assert json.loads(res)["answer"] == "Custom test answer."

    provider.clear_custom_response()
    # Now defaults back to parsing
    res2 = provider.generate("sys", "USER QUESTION:\nWhat?\n\nRETRIEVED HLD EVIDENCE CONTEXT:\n")
    assert "Insufficient evidence" in res2 or "answer" in res2


def test_mock_llm_provider_canonical_queries():
    """Verify MockLLMProvider handles all 5 canonical queries deterministically."""
    provider = MockLLMProvider()
    canonical_questions = [
        "What components are associated with VehicleControl?",
        "What interface carries VehicleSpeed?",
        "What ports belong to VehicleControl?",
        "What signals are consumed by VehicleControl?",
        "What changed between version 1.0 and version 2.0?",
    ]
    mock_prompt_template = (
        "USER QUESTION:\n{q}\n\nRETRIEVED HLD EVIDENCE CONTEXT:\n"
        "--- EVIDENCE ITEM 1 ---\n"
        "Chunk ID: chunk_1\nDocument: autosar_hld_v2.0\nVersion: 2.0\nPage: 3\nSection: 3.1 (VehicleControl)\n"
        "Relevance Score: 0.8500\nContent:\nVehicleControl depends on SensorManager and DiagnosticManager.\n\n"
        "--- EVIDENCE ITEM 2 ---\n"
        "Chunk ID: chunk_2\nDocument: autosar_hld_v1.0\nVersion: 1.0\nPage: 2\nSection: 2.2 (Component Overview)\n"
        "Relevance Score: 0.8000\nContent:\nThe system consists of four primary software components in version 1.0.\n\n"
        "--- EVIDENCE ITEM 3 ---\n"
        "Chunk ID: chunk_3\nDocument: autosar_hld_v2.0\nVersion: 2.0\nPage: 2\nSection: 2.2 (Component Overview)\n"
        "Relevance Score: 0.8100\nContent:\nThe system consists of five primary software components in version 2.0 with SafetyManager.\n\n"
        "--- EVIDENCE ITEM 4 ---\n"
        "Chunk ID: chunk_4\nDocument: autosar_hld_v2.0\nVersion: 2.0\nPage: 6\nSection: 4.1 (VehicleDataInterface)\n"
        "Relevance Score: 0.7900\nContent:\nVehicleSpeed is carried by VehicleDataInterface from SensorManager to VehicleControl.\n"
    )

    for q in canonical_questions:
        user_p = mock_prompt_template.format(q=q)
        output = provider.generate("system", user_p)
        data = json.loads(output)
        assert "answer" in data
        assert len(data["answer"]) > 10
        assert "citations" in data
        assert isinstance(data["citations"], list)
        assert len(data["citations"]) >= 1


def test_ollama_provider_configuration():
    """Verify OllamaProvider defaults and offline connection behavior."""
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3:4b", timeout=2)
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "qwen3:4b"
    assert provider.timeout == 2

    # Expect ConnectionError if local daemon is not running on port 11434
    try:
        provider.generate("sys", "user")
    except ConnectionError as e:
        assert "Could not connect to local Ollama" in str(e)
    except Exception:
        # If Ollama is running, it won't raise ConnectionError
        pass


def test_gemini_provider_missing_key_raises():
    """Verify GeminiProvider raises clear ValueError if no API key is provided."""
    with pytest.raises(ValueError) as excinfo:
        GeminiProvider(api_key="")
    assert "GEMINI_API_KEY is not set" in str(excinfo.value)


def test_get_llm_provider_factory():
    """Verify factory returns appropriate provider types."""
    p_mock = get_llm_provider("mock")
    assert isinstance(p_mock, MockLLMProvider)

    p_ollama = get_llm_provider("ollama")
    assert isinstance(p_ollama, OllamaProvider)


# ==========================================
# 2. LangChain RAG Orchestration Tests
# ==========================================


def test_to_langchain_documents_preserves_provenance():
    """Verify to_langchain_documents preserves all AUTOSAR provenance fields."""
    context_chunk = ContextChunk(
        chunk_id="chunk_test_01",
        document_id="autosar_hld_v2.0",
        project_id="test_project",
        version="2.0",
        page_number=4,
        section="3.2",
        section_title="SensorManager",
        chunk_type="component",
        entity_hint="SensorManager",
        text="SensorManager produces VehicleSpeed signal.",
        score=0.88,
    )

    docs = to_langchain_documents([context_chunk])
    assert len(docs) == 1
    doc = docs[0]
    assert doc.page_content == "SensorManager produces VehicleSpeed signal."
    assert doc.metadata["chunk_id"] == "chunk_test_01"
    assert doc.metadata["document"] == "autosar_hld_v2.0"
    assert doc.metadata["version"] == "2.0"
    assert doc.metadata["page"] == 4
    assert doc.metadata["section"] == "3.2"
    assert doc.metadata["score"] == 0.88

    # Also test tuple format (score, dict)
    tuple_item = (0.75, {
        "chunk_id": "chunk_tuple_02",
        "document_id": "autosar_hld_v1.0",
        "version": "1.0",
        "page_number": 5,
        "section": "4.1",
        "section_title": "VehicleDataInterface",
        "chunk_type": "interface",
        "text": "Interface definition text",
    })
    docs2 = to_langchain_documents([tuple_item])
    assert len(docs2) == 1
    assert docs2[0].metadata["chunk_id"] == "chunk_tuple_02"
    assert docs2[0].metadata["score"] == 0.75


def test_hld_retriever_query():
    """Verify HLDRetriever retrieves LangChain Documents from Phase 1 FAISS."""
    pipe = get_pipeline()
    retriever = HLDRetriever(pipeline=pipe, top_k=3)
    docs = retriever.invoke("VehicleControl software component")
    assert len(docs) <= 3
    assert len(docs) > 0
    first = docs[0]
    assert "chunk_id" in first.metadata
    assert "document" in first.metadata
    assert "version" in first.metadata
    assert "page" in first.metadata
    assert len(first.page_content) > 0


def test_langchain_rag_chain_query():
    """Verify LangChainRAGChain executes with MockLLMProvider and returns validated response."""
    pipe = get_pipeline()
    mock_provider = MockLLMProvider()
    chain = LangChainRAGChain(pipeline=pipe, llm_provider=mock_provider)

    response = chain.query("What interface carries VehicleSpeed?")
    assert isinstance(response, RAGResponse)
    assert "VehicleSpeed" in response.answer or "VehicleDataInterface" in response.answer
    assert response.retrieved_chunks_count > 0
    assert len(response.citations) > 0


def test_langchain_empty_query():
    """Verify LangChain chain handles empty query gracefully."""
    chain = LangChainRAGChain(llm_provider=MockLLMProvider())
    resp = chain.query("")
    assert resp.confidence == ConfidenceLevel.LOW
    assert resp.review_required is True
    assert "No question was provided" in resp.answer


# ==========================================
# 3. Architecture Extraction Tests
# ==========================================


def test_architecture_extractor_catalog():
    """Verify ArchitectureExtractor extracts SWCs and interfaces with provenance."""
    extractor = get_architecture_extractor()
    catalog = extractor.extract_catalog()

    assert catalog.total_components >= 5
    assert catalog.total_interfaces >= 4
    assert "1.0" in catalog.versions
    assert "2.0" in catalog.versions

    # Verify SWCs
    comp_names = [c.name for c in catalog.components]
    assert "VehicleControl" in comp_names
    assert "SensorManager" in comp_names
    assert "DiagnosticManager" in comp_names
    assert "CommunicationManager" in comp_names
    assert "SafetyManager" in comp_names

    # Check provenance on VehicleControl
    vc = next(c for c in catalog.components if c.name == "VehicleControl")
    assert vc.chunk_id.startswith("autosar_hld")
    assert vc.version in ["1.0", "2.0"]
    assert vc.page > 0
    assert vc.section != ""
    assert len(vc.ports) > 0


def test_architecture_extractor_version_difference():
    """Verify SafetyManager is present in v2.0 but not in v1.0."""
    extractor = get_architecture_extractor()

    v1_comps = extractor.extract_components(version="1.0")
    v2_comps = extractor.extract_components(version="2.0")

    v1_names = [c.name for c in v1_comps]
    v2_names = [c.name for c in v2_comps]

    assert "SafetyManager" not in v1_names
    assert "SafetyManager" in v2_names
    assert len(v2_names) > len(v1_names)


def test_architecture_extractor_interfaces():
    """Verify interface extraction and provenance."""
    extractor = get_architecture_extractor()
    interfaces = extractor.extract_interfaces()

    iface_names = [i.name for i in interfaces]
    assert "VehicleDataInterface" in iface_names
    assert "DiagnosticInterface" in iface_names

    vdi = next(i for i in interfaces if i.name == "VehicleDataInterface")
    assert vdi.interface_type == "Sender-Receiver"
    assert vdi.chunk_id != ""
    assert vdi.page > 0
    assert "VehicleSpeed" in vdi.signals


# ==========================================
# 4. JSON & Markdown Export Tests
# ==========================================


def test_export_response_to_json_and_markdown(tmp_path: Path):
    """Verify exporting RAGResponse to JSON and Markdown with files."""
    response = RAGResponse(
        question="What interface carries VehicleSpeed?",
        answer="VehicleSpeed is carried by VehicleDataInterface.",
        claims=[
            Claim(text="VehicleSpeed is carried by VehicleDataInterface.", citation_ids=["c1"], grounded=True)
        ],
        citations=[
            Citation(
                document="autosar_hld_v2.0",
                version="2.0",
                page=6,
                section="4.1",
                chunk_id="c1",
                valid=True,
            )
        ],
        confidence=ConfidenceLevel.HIGH,
        limitations=[],
        review_required=False,
        grounding_score=1.0,
        retrieved_chunks_count=3,
    )

    json_file = tmp_path / "export.json"
    md_file = tmp_path / "export.md"

    json_str = export_response_to_json(response, provider="mock", output_path=json_file)
    assert json_file.exists()
    parsed_json = json.loads(json_str)
    assert parsed_json["question"] == "What interface carries VehicleSpeed?"
    assert parsed_json["provider"] == "mock"
    assert parsed_json["confidence"] == "high"
    assert len(parsed_json["citations"]) == 1

    md_str = export_response_to_markdown(response, provider="mock", output_path=md_file)
    assert md_file.exists()
    assert "# AUTOSAR HLD Architecture Q&A Report" in md_str
    assert "VehicleSpeed is carried by VehicleDataInterface." in md_str
    assert "| `c1` | `autosar_hld_v2.0` | 2.0 | p. 6 | Sec 4.1 | [VALID] |" in md_str


# ==========================================
# 5. FastAPI Endpoints Tests
# ==========================================


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def controlled_hld_pipeline(monkeypatch, v1_chunks, v2_chunks):
    """Controlled 71-chunk test state from synthetic HLD specification fixtures."""
    all_chunks = v1_chunks + v2_chunks
    entries = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "version": c.version,
            "page": getattr(c, "page_number", getattr(c, "page", 1)),
            "section": c.section,
            "section_title": c.section_title,
            "chunk_type": c.chunk_type,
            "entity_hint": c.entity_hint,
            "text": c.text,
        }
        for c in all_chunks
    ]

    class ControlledMetaStore:
        count = len(entries)
        def __init__(self):
            self.entries = entries

    class ControlledFAISSStore:
        count = len(entries)
        dimension = 384

    class ControlledPipeline:
        faiss_store = ControlledFAISSStore()
        metadata_store = ControlledMetaStore()

    controlled = ControlledPipeline()
    monkeypatch.setattr("app.main.get_pipeline", lambda provider_name=None: controlled)
    return controlled


def test_fastapi_health(client: TestClient, controlled_hld_pipeline):
    """Verify /health endpoint returns 200 and complete diagnostics."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["faiss_indexed_chunks"] == 71
    assert data["metadata_catalog_chunks"] == 71
    assert "1.0" in data["available_versions"]
    assert "2.0" in data["available_versions"]


def test_fastapi_query_endpoint_direct(client: TestClient):
    """Verify POST /query with mock provider."""
    payload = {
        "question": "What components are associated with VehicleControl?",
        "provider": "mock",
        "use_langchain": False,
    }
    res = client.post("/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "VehicleControl" in data["answer"]
    assert len(data["citations"]) >= 1


def test_fastapi_query_endpoint_langchain(client: TestClient):
    """Verify POST /query with LangChain orchestration."""
    payload = {
        "question": "What interface carries VehicleSpeed?",
        "provider": "mock",
        "use_langchain": True,
    }
    res = client.post("/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["citations"]) >= 1


def test_fastapi_query_empty_raises_400(client: TestClient):
    """Verify empty query returns 400 error."""
    res = client.post("/query", json={"question": "   "})
    assert res.status_code == 400


def test_fastapi_documents_endpoint(client: TestClient, controlled_hld_pipeline):
    """Verify GET /documents returns indexed versions and chunk breakdown."""
    res = client.get("/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["total_chunks"] == 71
    assert "1.0" in data["versions"]
    assert "2.0" in data["versions"]


def test_fastapi_review_lifecycle(client: TestClient):
    """Verify POST /review saves review and GET /reviews retrieves it."""
    review_data = {
        "question": "What interface carries VehicleSpeed?",
        "decision": "accepted",
        "engineer_id": "test_engineer_42",
        "feedback": "Fully verified against Section 4.1.",
        "corrections": None,
    }
    res = client.post("/review", json=review_data)
    assert res.status_code == 200
    saved = res.json()
    assert saved["status"] == "success"
    assert saved["review"]["engineer_id"] == "test_engineer_42"

    # Fetch reviews
    res2 = client.get("/reviews")
    assert res2.status_code == 200
    rev_list = res2.json()["reviews"]
    assert any(r["engineer_id"] == "test_engineer_42" for r in rev_list)


def test_fastapi_entities_components(client: TestClient):
    """Verify GET /entities/components returns components with provenance."""
    res = client.get("/entities/components?version=2.0")
    assert res.status_code == 200
    comps = res.json()
    assert len(comps) >= 4
    for c in comps:
        assert c["version"] == "2.0"
        assert c["chunk_id"] != ""
        assert c["page"] > 0


def test_fastapi_entities_interfaces(client: TestClient):
    """Verify GET /entities/interfaces returns interfaces with provenance."""
    res = client.get("/entities/interfaces?version=1.0")
    assert res.status_code == 200
    ifaces = res.json()
    assert len(ifaces) >= 3
    for i in ifaces:
        assert i["version"] == "1.0"
        assert i["chunk_id"] != ""


def test_fastapi_entities_catalog(client: TestClient):
    """Verify GET /entities/catalog returns full catalog."""
    res = client.get("/entities/catalog")
    assert res.status_code == 200
    cat = res.json()
    assert cat["total_components"] >= 5
    assert cat["total_interfaces"] >= 4
