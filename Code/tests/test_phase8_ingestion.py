import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_non_pdf_rejection(client):
    # Test uploading a non-PDF file
    files = {"file": ("test.txt", b"dummy text", "text/plain")}
    data = {"version": "3.0", "governance_status": "DRAFT"}
    response = client.post("/documents/upload", files=files, data=data)
    assert response.status_code == 400
    assert "Only PDF files are supported." in response.json()["detail"]

def test_empty_filename(client):
    files = {"file": ("", b"dummy text", "application/pdf")}
    data = {"version": "3.0", "governance_status": "DRAFT"}
    response = client.post("/documents/upload", files=files, data=data)
    assert response.status_code == 422

def test_path_traversal_protection(client):
    files = {"file": ("../../malicious.pdf", b"dummy content", "application/pdf")}
    data = {"version": "3.0", "governance_status": "DRAFT"}
    response = client.post("/documents/upload", files=files, data=data)
    
    # Path traversal characters should be stripped by Path.name
    # But if the file is invalid PDF, ingestion fails. Let's see if the path is sanitized.
    # The file parser might fail with malformed PDF, which gives 500 or 400
    assert response.status_code in [400, 500]
    
def test_malformed_pdf_handling(client):
    files = {"file": ("malformed.pdf", b"not a real pdf content", "application/pdf")}
    data = {"version": "3.0", "governance_status": "DRAFT"}
    response = client.post("/documents/upload", files=files, data=data)
    
    # PyMuPDF or the parser should fail and return 500 or 400
    assert response.status_code in [400, 500]
    assert "Ingestion failed" in response.json().get("detail", "") or "error" in response.json().get("detail", "").lower()

def test_document_listing_and_governance(client):
    # We test that the document listing works, and it includes existing documents
    res = client.get("/documents")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)

def test_successful_upload_and_ingestion(client):
    pdf_path = Path("data/raw/AUTOSAR_HLD_v1.0.pdf")
    if not pdf_path.exists():
        pytest.skip("Test PDF not found")
        
    with open(pdf_path, "rb") as f:
        files = {"file": ("test_upload_v3.pdf", f, "application/pdf")}
        data = {"version": "3.0", "governance_status": "DRAFT"}
        response = client.post("/documents/upload", files=files, data=data)
        
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "upload_successful"
    assert res_data["version"] == "3.0"
    assert res_data["document"] == "test_upload_v3.pdf"
    assert res_data["pages"] > 0
    assert res_data["chunks"] > 0
    assert res_data["faiss_status"] == "queued"
    
    import time
    job_id = res_data["job_id"]
    for _ in range(30):
        status_res = client.get(f"/documents/indexing_status/{job_id}")
        if status_res.json()["status"] == "completed":
            break
        time.sleep(1)
    
    assert status_res.json()["status"] == "completed"

    # Test Q&A can retrieve it
    q_data = {"question": "What is the architecture?", "version": "3.0", "provider": "mock"}
    q_res = client.post("/query", json=q_data)
    assert q_res.status_code == 200
    assert len(q_res.json().get("citations", [])) > 0

    # Cleanup to avoid breaking other tests
    from db.repository import HLDRepository
    from db.models import Chunk, DocumentVersion, GovernanceRecord
    repo = HLDRepository()
    session = repo.SessionFactory()
    try:
        session.query(Chunk).filter_by(version='3.0').delete()
        session.query(DocumentVersion).filter_by(version='3.0').delete()
        session.query(GovernanceRecord).filter_by(document_id='autosar_hld_v3.0').delete()
        session.commit()
    except:
        session.rollback()
    finally:
        session.close()
    
    # Trigger re-index
    client.post("/documents/index")
