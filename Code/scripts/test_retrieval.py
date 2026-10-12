import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import INDEX_DIR
from app.logging_config import setup_logging
from embeddings.embedder import HLDEmbedder
from vectorstore.faiss_store import FAISSStore
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)

DEFAULT_QUERIES = [
    "What components are associated with VehicleControl?",
    "What interface carries VehicleSpeed?",
    "What ports belong to VehicleControl?",
    "What signals are consumed by VehicleControl?",
    "What changed between version 1.0 and version 2.0?"
]

def main():
    parser = argparse.ArgumentParser(description="Test retrieval from AUTOSAR HLD Assistant index.")
    parser.add_argument("--query", type=str, help="Custom query to run")
    parser.add_argument("--version", type=str, help="Filter by specific version")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    
    args = parser.parse_args()
    setup_logging()
    
    faiss_path = INDEX_DIR / "hld_index.faiss"
    metadata_path = INDEX_DIR / "hld_metadata.json"
    
    if not faiss_path.exists() or not metadata_path.exists():
        logger.error(f"Index files not found in {INDEX_DIR}. Run build_index.py first.")
        sys.exit(1)
        
    embedder = HLDEmbedder()
    _ = embedder.model  # Trigger lazy loading so embedder.dimension is populated
    faiss_store = FAISSStore(embedder.dimension)
    faiss_store.load(faiss_path)
    
    metadata_store = MetadataStore()
    metadata_store.load(metadata_path)
    
    queries_to_run = [args.query] if args.query else DEFAULT_QUERIES
    
    summary_results = []
    
    for query in queries_to_run:
        print(f"\n{'='*60}")
        print(f'QUERY: "{query}"')
        print(f"{'='*60}\n")
        
        query_vector = embedder.embed_query(query)
        
        # Pre-filtering by version if supported by metadata store?
        # Actually, FAISS typically doesn't support pre-filtering without custom work,
        # but we can do post-filtering or ID-mapped filtering.
        # Since metadata filtering might be post-retrieval in our simple implementation:
        
        distances, indices = faiss_store.search(query_vector, args.top_k * 2) # Get extra for filtering
        
        results = []
        for dist, idx in zip(distances, indices):
            if idx == -1: continue
            
            chunk_metadata = metadata_store.get_by_faiss_id(idx)
            if not chunk_metadata: continue
            
            # Apply version filter
            if args.version and chunk_metadata.get('version') != args.version:
                continue
                
            results.append((dist, chunk_metadata))
            if len(results) == args.top_k:
                break
                
        if not results:
            print("No results found.")
            summary_results.append((query, "N/A", "N/A"))
            continue
            
        summary_results.append((query, f"{results[0][0]:.4f}", results[0][1].get("chunk_type", "unknown")))
            
        for rank, (score, metadata) in enumerate(results, 1):
            chunk_id = metadata.get("chunk_id", "N/A")
            doc_id = metadata.get("document_id", "N/A")
            version = metadata.get("version", "N/A")
            page = metadata.get("page_number", "N/A")
            section = metadata.get("section", "N/A")
            section_title = metadata.get("section_title", "N/A")
            chunk_type = metadata.get("chunk_type", "N/A")
            entity_hint = metadata.get("entity_hint", "N/A")
            
            evidence = metadata.get("text", "")
            if len(evidence) > 200:
                evidence = evidence[:197] + "..."
                
            print(f"  Rank {rank} | Score: {score:.4f}")
            print(f"  {'-'*42}")
            print(f"  Chunk ID:     {chunk_id}")
            print(f"  Document:     {doc_id}")
            print(f"  Version:      {version}")
            print(f"  Page:         {page}")
            print(f"  Section:      {section}")
            print(f"  Section Title: {section_title}")
            print(f"  Chunk Type:   {chunk_type}")
            print(f"  Entity Hint:  {entity_hint}")
            print(f"  Evidence:")
            print(f"  \"{evidence}\"\n")
            
    print(f"\n{'='*60}")
    print("RETRIEVAL SUMMARY")
    print(f"{'='*60}")
    print(f"{'Query'.ljust(45)} | {'Top-1 Score'} | {'Top-1 Type'}")
    print(f"{'-'*60}")
    for q, score, ctype in summary_results:
        q_trunc = q[:43] + ".." if len(q) > 45 else q
        print(f"{q_trunc.ljust(45)} | {score.ljust(11)} | {ctype}")

if __name__ == "__main__":
    main()
