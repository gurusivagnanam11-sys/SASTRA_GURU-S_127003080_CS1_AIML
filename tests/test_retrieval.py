import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from embeddings.embedder import HLDEmbedder
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

@pytest.fixture
def populated_stores(v1_chunks):
    embedder = HLDEmbedder()
    texts = [c.text for c in v1_chunks]
    vectors = embedder.embed_documents(texts)
    
    faiss_store = FAISSStore(dimension=embedder.dimension)
    faiss_store.build_index(vectors)
    
    meta_store = MetadataStore()
    for chunk in v1_chunks:
        meta_store.add_chunk(chunk)
        
    return embedder, faiss_store, meta_store, v1_chunks

def test_retrieval_pipeline(populated_stores):
    embedder, faiss_store, meta_store, v1_chunks = populated_stores
    
    query = "VehicleDataInterface"
    q_vec = embedder.embed_query(query)
    
    scores, indices = faiss_store.search(q_vec, top_k=5)
    
    results = []
    for score, idx in zip(scores, indices):
        if idx != -1:
            chunk = meta_store.get_by_faiss_id(idx)
            results.append({
                "score": float(score),
                "chunk": chunk
            })
            
    assert len(results) > 0, "No results returned"
    
    # Check ordering (descending)
    scores_list = [r["score"] for r in results]
    assert scores_list == sorted(scores_list, reverse=True), "Results not sorted by score"
    
    # Check contents
    for res in results:
        assert 0.0 <= res["score"] <= 1.01, "Score out of expected bounds"
        chunk = res["chunk"]
        chunk_id = chunk["chunk_id"] if isinstance(chunk, dict) else chunk.chunk_id
        document_id = chunk["document_id"] if isinstance(chunk, dict) else chunk.document_id
        version = chunk["version"] if isinstance(chunk, dict) else chunk.version
        page_number = chunk["page_number"] if isinstance(chunk, dict) else chunk.page_number
        text = chunk["text"] if isinstance(chunk, dict) else chunk.text
        
        assert chunk_id
        assert document_id
        assert version == "1.0"
        assert page_number >= 1
        assert text

    # At least one result should be relevant
    relevant_found = any(
        "VehicleDataInterface" in (r["chunk"]["text"] if isinstance(r["chunk"], dict) else r["chunk"].text) or 
        "VehicleSpeed" in (r["chunk"]["text"] if isinstance(r["chunk"], dict) else r["chunk"].text)
        for r in results
    )
    assert relevant_found, "Query terms not found in top results"

def test_metadata_filter(populated_stores):
    _, _, meta_store, _ = populated_stores
    
    v1_results = meta_store.filter(version="1.0")
    assert len(v1_results) > 0
    
    v2_results = meta_store.filter(version="2.0")
    assert len(v2_results) == 0
