import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import numpy as np
from vectorstore.faiss_store import FAISSStore

@pytest.fixture
def dim():
    return 128

@pytest.fixture
def store(dim):
    return FAISSStore(dimension=dim)

@pytest.fixture
def sample_vectors(dim):
    np.random.seed(42)
    vecs = np.random.randn(10, dim).astype('float32')
    # normalize
    vecs = vecs / np.linalg.norm(vecs, axis=1)[:, np.newaxis]
    return vecs

def test_faiss_store_build_and_count(store, sample_vectors):
    store.build_index(sample_vectors)
    assert store.count == 10

def test_faiss_search(store, sample_vectors, dim):
    store.build_index(sample_vectors)
    query = sample_vectors[0]
    
    scores, indices = store.search(query, top_k=3)
    assert len(scores) == 3
    assert len(indices) == 3
    # The first result should be the query itself with score ~ 1.0
    assert indices[0] == 0
    assert abs(scores[0] - 1.0) < 1e-4

def test_save_and_load_roundtrip(store, sample_vectors, tmp_path):
    store.build_index(sample_vectors)
    path = tmp_path / "index.faiss"
    
    store.save(path)
    assert path.exists()
    
    new_store = FAISSStore(dimension=store.dimension)
    new_store.load(path)
    
    assert new_store.count == 10

def test_validate(store, sample_vectors):
    store.build_index(sample_vectors)
    store.validate(10)
    
    with pytest.raises(Exception):
        store.validate(9)

def test_dimension_mismatch(store):
    bad_vecs = np.random.randn(5, store.dimension + 1).astype('float32')
    with pytest.raises(Exception):
        store.build_index(bad_vecs)
