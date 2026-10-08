import logging
from pathlib import Path
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

logger = logging.getLogger(__name__)

class FAISSStore:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = None

    def build_index(self, vectors: np.ndarray) -> None:
        """Build a new FAISS IndexFlatIP from vectors."""
        if faiss is None:
            raise ImportError("faiss is required but not installed.")
            
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} does not match expected {self.dimension}")
            
        logger.info(f"Building FAISS IndexFlatIP for {len(vectors)} vectors of dimension {self.dimension}")
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(vectors.astype(np.float32))

    def add_vectors(self, vectors: np.ndarray) -> None:
        """Add vectors to an existing FAISS IndexFlatIP."""
        if self.index is None:
            raise RuntimeError("Index has not been built or loaded.")
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension {vectors.shape[1]} does not match expected {self.dimension}")
            
        logger.info(f"Adding {len(vectors)} vectors to FAISS IndexFlatIP")
        self.index.add(vectors.astype(np.float32))

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> tuple:
        """Search index. Returns (scores, indices) arrays."""
        if self.index is None:
            raise RuntimeError("Index has not been built or loaded.")
            
        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)
            
        if query_vector.shape[1] != self.dimension:
            raise ValueError(f"Query vector dimension {query_vector.shape[1]} != {self.dimension}")

        scores, indices = self.index.search(query_vector.astype(np.float32), top_k)
        return scores[0], indices[0]

    def save(self, path: Path) -> None:
        """Save FAISS index to disk."""
        if self.index is None:
            raise RuntimeError("No index to save.")
            
        logger.info(f"Saving FAISS index to {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    def load(self, path: Path) -> None:
        """Load FAISS index from disk."""
        if faiss is None:
            raise ImportError("faiss is required but not installed.")
            
        if not path.exists():
            raise FileNotFoundError(f"FAISS index file not found at {path}")
            
        logger.info(f"Loading FAISS index from {path}")
        self.index = faiss.read_index(str(path))
        
        if self.index.d != self.dimension:
            raise ValueError(f"Loaded index dimension {self.index.d} does not match expected {self.dimension}")

    @property
    def count(self) -> int:
        """Number of vectors in the index."""
        if self.index is None:
            return 0
        return self.index.ntotal

    def validate(self, expected_count: int) -> None:
        """Validate index integrity."""
        if self.index is None:
            raise RuntimeError("Index is missing.")
            
        if self.count != expected_count:
            raise ValueError(f"Index count {self.count} does not match expected {expected_count}")
        
        logger.info(f"Index validation passed: {self.count} vectors, dimension {self.dimension}")
