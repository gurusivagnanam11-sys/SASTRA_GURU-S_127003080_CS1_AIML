import sys
import logging
from pathlib import Path
import time
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import ensure_directories, INDEX_DIR
from app.logging_config import setup_logging
from db.repository import HLDRepository
from embeddings.embedder import HLDEmbedder
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)

def main():
    setup_logging()
    logger.info("Starting index building process...")
    ensure_directories()
    
    # Load chunks
    repo = HLDRepository()
    repo.init_db()
    
    logger.info("Loading chunks from SQLite...")
    chunks = repo.get_chunks()
    
    if not chunks:
        logger.error("No chunks found in database. Run ingest_document.py first.")
        sys.exit(1)
        
    logger.info(f"Loaded {len(chunks)} chunks.")
    
    # Initialize components
    embedder = HLDEmbedder()
    _ = embedder.model  # Trigger lazy-loading to set dimension
    faiss_store = FAISSStore(embedder.dimension)
    metadata_store = MetadataStore()
    
    logger.info(f"Generating embeddings using {embedder.model_name} (dimension: {embedder.dimension})...")
    start_time = time.time()
    
    # Generate embeddings
    texts = [chunk["text"] if isinstance(chunk, dict) else chunk.text for chunk in chunks]
    vectors = embedder.embed_documents(texts)
    
    # Build stores
    logger.info("Building FAISS index...")
    faiss_store.build_index(vectors)
    
    logger.info("Building metadata store...")
    for chunk in chunks:
        metadata_store.add_chunk(chunk)
        
    # Validate
    logger.info("Validating stores...")
    faiss_store.validate(metadata_store.count)
        
    # Save
    faiss_path = INDEX_DIR / "hld_index.faiss"
    metadata_path = INDEX_DIR / "hld_metadata.json"
    
    logger.info(f"Saving FAISS index to {faiss_path}...")
    faiss_store.save(faiss_path)
    
    logger.info(f"Saving metadata to {metadata_path}...")
    metadata_store.save(metadata_path)
    
    duration = time.time() - start_time
    
    # Get stats
    stats = repo.get_stats()
    
    # Summary
    print("\n" + "="*50)
    print("INDEX BUILD SUMMARY")
    print("="*50)
    print(f"Documents indexed:     {stats.get('total_documents', 0)}")
    print(f"Document versions:     {stats.get('total_versions', 0)}")
    print(f"Total chunks/vectors:  {metadata_store.count}")
    print(f"Embedding model:       {embedder.model_name}")
    print(f"Model dimension:       {embedder.dimension}")
    print(f"Index type:            FAISS L2")
    if faiss_path.exists():
        print(f"FAISS index size:      {os.path.getsize(faiss_path) / (1024*1024):.2f} MB")
    if metadata_path.exists():
        print(f"Metadata store size:   {os.path.getsize(metadata_path) / (1024*1024):.2f} MB")
    print(f"Build time:            {duration:.2f} seconds")
    print("="*50)

if __name__ == "__main__":
    main()
