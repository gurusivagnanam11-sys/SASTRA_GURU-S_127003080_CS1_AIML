import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import numpy as np
from embeddings.embedder import HLDEmbedder

@pytest.fixture
def embedder():
    return HLDEmbedder()

def test_embedder_initializes(embedder):
    assert embedder.dimension > 0
    assert embedder.model_name

def test_embed_documents(embedder):
    texts = ["Sample text 1", "Sample text 2"]
    embs = embedder.embed_documents(texts)
    
    assert isinstance(embs, np.ndarray)
    assert embs.shape == (2, embedder.dimension)
    
    # Check normalization
    norms = np.linalg.norm(embs, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-5)

def test_embed_query(embedder):
    query = "Sample query"
    emb = embedder.embed_query(query)
    
    assert isinstance(emb, np.ndarray)
    assert emb.shape == (embedder.dimension,)
    assert abs(np.linalg.norm(emb) - 1.0) < 1e-5

def test_empty_input(embedder):
    embs = embedder.embed_documents([])
    assert isinstance(embs, np.ndarray)
    assert embs.shape == (0, embedder.dimension)
