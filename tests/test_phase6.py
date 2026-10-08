import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from ingestion.pdf_parser import parse_pdf, _ocr_page, _extract_tables
from ingestion.models import DocumentData
from chunking.hld_chunker import chunk_document

@pytest.fixture
def mock_fitz_doc():
    doc = MagicMock()
    doc.page_count = 3
    doc.__enter__.return_value = doc
    
    # Page 1: Normal text
    page1 = MagicMock()
    def get_text_1(*args, **kwargs):
        if args and args[0] == "dict":
            return {"blocks": []}
        return "This is a normal text page with plenty of text. Version 1.0" + " " * 50
    page1.get_text.side_effect = get_text_1
    page1.find_tables.return_value = []
    
    # Page 2: Image only (requires OCR)
    page2 = MagicMock()
    def get_text_2(*args, **kwargs):
        if args and args[0] == "dict":
            return {"blocks": []}
        return "  "
    page2.get_text.side_effect = get_text_2
    page2.find_tables.return_value = []
    
    # Page 3: Table page
    page3 = MagicMock()
    def get_text_3(*args, **kwargs):
        if args and args[0] == "dict":
            return {"blocks": []}
        return "This page contains a table and has plenty of normal text so it does not trigger the OCR fallback. " * 3
    page3.get_text.side_effect = get_text_3
    mock_table = MagicMock()
    mock_table.extract.return_value = [
        ["Port", "Interface", "Direction", "Signal"],
        ["SpeedIn", "VehicleSpeedInterface", "IN", "VehicleSpeed"]
    ]
    page3.find_tables.return_value = [mock_table]
    
    doc.__getitem__.side_effect = lambda i: [page1, page2, page3][i]
    return doc


@patch('ingestion.pdf_parser.fitz.open')
@patch('ingestion.pdf_parser._ocr_page')
def test_mixed_pdf_processing(mock_ocr, mock_fitz_open, mock_fitz_doc, tmp_path):
    mock_fitz_open.return_value = mock_fitz_doc
    mock_ocr.return_value = "OCR extracted text for the scanned image page."
    
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock")
    
    doc_data = parse_pdf(fake_pdf, "test_proj")
    
    assert len(doc_data.pages) == 3
    
    # Page 1: normal text
    assert doc_data.pages[0].extraction_method == "text"
    assert "normal text" in doc_data.pages[0].raw_text
    
    # Page 2: OCR
    assert doc_data.pages[1].extraction_method == "ocr"
    assert doc_data.pages[1].raw_text == "OCR extracted text for the scanned image page."
    
    # Page 3: Table
    assert doc_data.pages[2].extraction_method == "text"
    assert len(doc_data.pages[2].tables) == 1
    assert "TABLE:" in doc_data.pages[2].tables[0]
    assert "Port: SpeedIn" in doc_data.pages[2].tables[0]

@patch('ingestion.pdf_parser.fitz.open')
@patch('ingestion.pdf_parser._ocr_page')
def test_ocr_failure_graceful(mock_ocr, mock_fitz_open, tmp_path):
    doc = MagicMock()
    doc.page_count = 1
    page = MagicMock()
    def get_text_p(*args, **kwargs):
        if args and args[0] == "dict":
            return {"blocks": []}
        return ""
    page.get_text.side_effect = get_text_p
    page.find_tables.return_value = []
    doc.__getitem__.return_value = page
    mock_fitz_open.return_value = doc
    
    # Simulate OCR failure returning empty string
    mock_ocr.return_value = ""
    
    fake_pdf = tmp_path / "test2.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock")
    
    doc_data = parse_pdf(fake_pdf, "test_proj")
    assert len(doc_data.pages) == 1
    assert doc_data.pages[0].raw_text == ""
    assert doc_data.pages[0].extraction_method == "text"  # fell back to original method


@patch('ingestion.pdf_parser.fitz.open')
def test_table_extraction_format(mock_fitz_open, tmp_path):
    doc = MagicMock()
    doc.page_count = 1
    page = MagicMock()
    def get_text_p(*args, **kwargs):
        if args and args[0] == "dict":
            return {"blocks": []}
        return "Page with table" + " "*50
    page.get_text.side_effect = get_text_p
    
    mock_table = MagicMock()
    mock_table.extract.return_value = [
        ["Signal Name", "Data Type", "Range"],
        ["EngineTemp", "float32", "-40..150"],
        [None, None, None], # empty row
        ["VehicleSpeed", "uint16", "0..300"]
    ]
    page.find_tables.return_value = [mock_table]
    doc.__getitem__.return_value = page
    mock_fitz_open.return_value = doc
    
    fake_pdf = tmp_path / "test3.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock")
    
    doc_data = parse_pdf(fake_pdf, "test_proj")
    tables = doc_data.pages[0].tables
    assert len(tables) == 1
    
    table_str = tables[0]
    assert "TABLE:" in table_str
    assert "Signal Name: EngineTemp" in table_str
    assert "Data Type: float32" in table_str
    assert "Range: -40..150" in table_str
    assert "Signal Name: VehicleSpeed" in table_str
    assert "Data Type: uint16" in table_str

@patch('ingestion.pdf_parser.fitz.open')
@patch('ingestion.pdf_parser._ocr_page')
def test_chunking_preserves_provenance(mock_ocr, mock_fitz_open, mock_fitz_doc, tmp_path):
    mock_fitz_open.return_value = mock_fitz_doc
    mock_ocr.return_value = "OCR text containing some VehicleControl component description."
    
    fake_pdf = tmp_path / "test4.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock")
    
    doc_data = parse_pdf(fake_pdf, "test_proj")
    chunks = chunk_document(doc_data)
    
    assert len(chunks) >= 3
    
    # Text chunk
    assert any(c.extraction_method == 'text' and 'normal text' in c.text for c in chunks)
    
    # OCR chunk
    ocr_chunks = [c for c in chunks if c.extraction_method == 'ocr']
    assert len(ocr_chunks) > 0
    assert ocr_chunks[0].content_type == 'ocr'
    assert 'VehicleControl' in ocr_chunks[0].text
    
    # Table chunk
    table_chunks = [c for c in chunks if 'TABLE:' in c.text]
    assert len(table_chunks) > 0
    assert table_chunks[0].extraction_method == 'text'
    assert table_chunks[0].content_type == 'table'
    assert 'Port: SpeedIn' in table_chunks[0].text

