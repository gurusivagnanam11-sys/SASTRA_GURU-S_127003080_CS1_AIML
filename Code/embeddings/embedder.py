import logging
import os
from typing import List
import numpy as np
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Try importing sentence_transformers, handle gracefully if missing
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from app.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class HLDEmbedder:
    def __init__(self, model_name: str = None):
        """Initialize with configurable model."""
        self.model_name = model_name or EMBEDDING_MODEL
        self._model = None
        self._dimension = None

    @property
    def dimension(self) -> int:
        """Get embedding dimension, loading model if needed."""
        if self._dimension is None:
            _ = self.model
        return self._dimension

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError("sentence-transformers is required but not installed.")
            
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as err:
                logger.warning(f"Initial load for {self.model_name} failed ({err}). Trying local cache...")
                try:
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception as e:
                    logger.error(f"Failed to load embedding model {self.model_name}: {e}")
                    raise
            
            # Getting dimension using a dummy input
            dummy_embed = self._model.encode(["test"])
            self._dimension = dummy_embed.shape[1]
            logger.info(f"Model loaded successfully. Dimension: {self._dimension}")
        return self._model

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of document texts. Returns L2-normalized vectors."""
        if not texts:
            logger.warning("Empty text list provided to embed_documents.")
            return np.empty((0, self.dimension or 384))
        
        logger.info(f"Embedding {len(texts)} documents with batch size {batch_size}...")
        embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)
        
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10 # Prevent division by zero
        normalized_embeddings = embeddings / norms
        return normalized_embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query. Returns L2-normalized vector."""
        if not query.strip():
            logger.warning("Empty query provided to embed_query.")
            return np.zeros(self.dimension or 384)
            
        embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm == 0:
            norm = 1e-10
        normalized_embedding = embedding / norm
        return normalized_embedding
