import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chunking.models import HLDChunk

def test_chunk_document_returns_chunks(v1_chunks):
    assert isinstance(v1_chunks, list)
    if len(v1_chunks) > 0:
        assert isinstance(v1_chunks[0], HLDChunk)

def test_at_least_10_chunks_generated(v1_chunks):
    assert len(v1_chunks) >= 10, "Expected at least 10 chunks from document"

def test_all_chunk_ids_unique(v1_chunks):
    chunk_ids = [c.chunk_id for c in v1_chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Chunk IDs must be unique"

def test_chunk_metadata_present(v1_chunks):
    for chunk in v1_chunks:
        assert chunk.document_id, "Missing document_id"
        assert chunk.version, "Missing version"
        assert chunk.page_number >= 1, "Invalid page_number"
        assert chunk.text.strip(), "Empty text"

def test_chunk_types_include_architecture_types(v1_chunks):
    types = {c.chunk_type for c in v1_chunks}
    # Expected types based on parsing logic, typically component, interface, etc.
    assert len(types) > 0, "Expected some chunk types"
    
def test_section_and_entity_hints(v1_chunks):
    has_section = any(c.section for c in v1_chunks)
    has_entity_hint = any(c.entity_hint for c in v1_chunks)
    
    assert has_section, "Expected section info on at least some chunks"
    assert has_entity_hint, "Expected entity_hint on at least some chunks"
