"""Phase 8: Tests for Engineering Reports and Source Governance."""
import pytest
from db.models import EngineeringReviewRecord, GovernanceRecord
from db.repository import HLDRepository
from reports.models import (
    ComponentReport,
    DocumentStatus,
    ReportCatalog,
)
from reports.generator import (
    generate_component_report,
    get_governance,
    set_governance_status,
    get_all_governance,
    get_active_version,
)
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    repo = HLDRepository()
    repo.init_db()
    yield

def test_governance_store_default():
    docs = get_all_governance()
    assert len(docs) > 0
    # Spec 1.0 is default approved
    spec1 = get_governance("autosar_hld_v1.0")
    assert spec1 is not None
    assert spec1.status == DocumentStatus.APPROVED

def test_governance_status_update():
    doc_id = "autosar_hld_v1.0"
    new_doc = set_governance_status(doc_id, DocumentStatus.DRAFT, "TestUser")
    assert new_doc.status == DocumentStatus.DRAFT
    assert new_doc.last_status_change is not None
    
    # Restore
    set_governance_status(doc_id, DocumentStatus.APPROVED, "TestUser")

def test_active_version():
    ver = get_active_version()
    assert ver in ["1.0", "2.0"]

def test_generate_component_report():
    report = generate_component_report("VehicleControl", "2.0")
    assert report is not None
    assert report.component_name == "VehicleControl"
    assert report.source_version == "2.0"
    assert len(report.impact_information) >= 0

def test_api_report_catalog():
    response = client.get("/reports/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "available_reports" in data
    assert "component_report" in data["available_reports"]

def test_api_component_report():
    response = client.get("/reports/component/VehicleControl?version=2.0")
    assert response.status_code == 200
    data = response.json()
    assert data["component_name"] == "VehicleControl"

def test_api_validation_report():
    response = client.get("/reports/validation?version=2.0")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_api_revision_report():
    response = client.get("/reports/revision?v1=1.0&v2=2.0")
    assert response.status_code == 200
    data = response.json()
    assert data["source_version"] == "1.0"
    assert data["target_version"] == "2.0"

def test_api_impact_report():
    response = client.get("/reports/impact?v1=1.0&v2=2.0")
    assert response.status_code == 200
    data = response.json()
    assert "total_impacts" in data

def test_api_governance_endpoints():
    # List documents
    res_list = client.get("/governance/documents")
    assert res_list.status_code == 200
    assert len(res_list.json()["documents"]) > 0

    doc_id = "autosar_hld_v1.0"
    
    # Get document
    res_get = client.get(f"/governance/documents/{doc_id}")
    assert res_get.status_code == 200
    
    # Update status
    res_post = client.post(
        f"/governance/documents/{doc_id}/status",
        json={"status": "ARCHIVED", "changed_by": "TestUser", "reason": "Test"}
    )
    assert res_post.status_code == 200
    assert res_post.json()["document"]["status"] == "ARCHIVED"
    
    # Check audit trail
    res_audit = client.get(f"/governance/audit?document_id={doc_id}")
    assert res_audit.status_code == 200
    audit = res_audit.json()["audit"]
    assert len(audit) > 0
    assert audit[0]["new_status"] == "ARCHIVED"
    
    # Restore status
    client.post(
        f"/governance/documents/{doc_id}/status",
        json={"status": "APPROVED", "changed_by": "TestUser", "reason": "Restore"}
    )

def test_api_engineering_reviews():
    payload = {
        "report_type": "component_report",
        "report_identifier": "VehicleControl",
        "reviewer": "Alice",
        "decision": "ENGINEER_APPROVED",
        "comment": "Looks good"
    }
    res_post = client.post("/reports/reviews", json=payload)
    assert res_post.status_code == 200
    
    res_get = client.get("/reports/reviews")
    assert res_get.status_code == 200
    reviews = res_get.json()["reviews"]
    assert len(reviews) > 0
    found = any(r["reviewer"] == "Alice" and r["report_identifier"] == "VehicleControl" for r in reviews)
    assert found
