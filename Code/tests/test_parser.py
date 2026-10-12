import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from ingestion.models import DocumentData
from ingestion.pdf_parser import parse_pdf

def test_parse_pdf_returns_document_data(parsed_v1):
    assert isinstance(parsed_v1, DocumentData), "Expected DocumentData instance"

def test_page_count_greater_than_zero(parsed_v1):
    assert len(parsed_v1.pages) > 0, "Page count should be > 0"
    assert len(parsed_v1.pages) >= 5, "Expected at least 5 pages in fixture"

def test_page_numbers_are_one_indexed(parsed_v1):
    for i, page in enumerate(parsed_v1.pages):
        assert page.page_number == i + 1, "Page numbers should be 1-indexed"

def test_pages_have_non_empty_raw_text(parsed_v1):
    for page in parsed_v1.pages:
        assert page.raw_text.strip(), f"Page {page.page_number} has empty text"

def test_document_id_and_version_set(parsed_v1):
    assert parsed_v1.document_id, "document_id should be set"
    assert parsed_v1.version == "1.0", "version should be set to 1.0"

def test_headings_detected(parsed_v1):
    has_headings = any(len(page.headings) > 0 for page in parsed_v1.pages)
    assert has_headings, "Expected headings to be detected on at least some pages"

def test_text_contains_autosar_keywords(parsed_v1):
    all_text = " ".join(p.raw_text for p in parsed_v1.pages)
    keywords = ["VehicleControl", "SensorManager"]
    for kw in keywords:
        assert kw in all_text, f"Expected keyword '{kw}' in document text"

def test_missing_file_raises_error():
    with pytest.raises(Exception):
        parse_pdf(Path("non_existent_file.pdf"), "proj", "1.0")
