import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
from ingestion.metadata import generate_document_id, save_processed_document, load_processed_document
from ingestion.models import DocumentData, DocumentMetadata, PageData

def test_generate_document_id():
    doc_id = generate_document_id("AUTOSAR_HLD v1.0.pdf")
    assert " " not in doc_id
    assert doc_id.islower()
    assert doc_id != ""

def test_document_metadata_fields():
    meta = DocumentMetadata(
        document_id="doc1",
        filename="test.pdf",
        project_id="p1",
        document_type="HLD",
        version="1.0",
        source="local",
        ingestion_timestamp="2024-01-01T00:00:00",
        page_count=10
    )
    assert meta.document_id == "doc1"
    assert meta.version == "1.0"

def test_save_and_load_processed_document(tmp_path):
    doc = DocumentData(
        document_id="test_doc",
        filename="test.pdf",
        project_id="proj1",
        version="2.0",
        pages=[PageData(page_number=1, raw_text="hello world", headings=["Intro"])]
    )
    
    save_processed_document(doc, tmp_path)
    
    expected_path = tmp_path / f"{doc.document_id}_v{doc.version}.json"
    assert expected_path.exists()
    
    loaded_doc = load_processed_document(expected_path)
    assert loaded_doc.document_id == "test_doc"
    assert loaded_doc.version == "2.0"
    assert len(loaded_doc.pages) == 1
    assert loaded_doc.pages[0].raw_text == "hello world"
    assert loaded_doc.pages[0].headings == ["Intro"]
