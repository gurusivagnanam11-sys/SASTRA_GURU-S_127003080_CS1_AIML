"""Shared pytest fixtures for AUTOSAR HLD Assistant tests."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from app.config import PROJECT_ROOT, FIXTURES_DIR


@pytest.fixture
def v1_pdf_path():
    """Path to synthetic v1.0 HLD PDF."""
    path = FIXTURES_DIR / "v1" / "AUTOSAR_HLD_v1.0.pdf"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Run 'python fixtures/generate_fixtures.py' first.")
    return path


@pytest.fixture
def v2_pdf_path():
    """Path to synthetic v2.0 HLD PDF."""
    path = FIXTURES_DIR / "v2" / "AUTOSAR_HLD_v2.0.pdf"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}. Run 'python fixtures/generate_fixtures.py' first.")
    return path


@pytest.fixture
def parsed_v1(v1_pdf_path):
    """Parsed v1.0 document."""
    from ingestion.pdf_parser import parse_pdf
    return parse_pdf(v1_pdf_path, project_id="test_project", version="1.0")


@pytest.fixture
def parsed_v2(v2_pdf_path):
    """Parsed v2.0 document."""
    from ingestion.pdf_parser import parse_pdf
    return parse_pdf(v2_pdf_path, project_id="test_project", version="2.0")


@pytest.fixture
def v1_chunks(parsed_v1):
    """Chunks from v1.0 document."""
    from chunking.hld_chunker import chunk_document
    return chunk_document(parsed_v1)


@pytest.fixture
def v2_chunks(parsed_v2):
    """Chunks from v2.0 document."""
    from chunking.hld_chunker import chunk_document
    return chunk_document(parsed_v2)


@pytest.fixture
def tmp_db_path(tmp_path):
    """Temporary database path for testing."""
    return tmp_path / "test.db"
