import sys
import argparse
import logging
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RAW_DATA_DIR, PROJECT_ID, ensure_directories
from app.logging_config import setup_logging
from ingestion.pdf_parser import parse_pdf
from ingestion.metadata import save_processed_document
from chunking.hld_chunker import chunk_document
from db.repository import HLDRepository

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Ingest PDF documents for AUTOSAR HLD Assistant.")
    parser.add_argument("file_path", nargs="?", help="Specific PDF file to ingest", type=str)
    parser.add_argument("--version", help="Explicit version for the document", type=str, default=None)
    
    args = parser.parse_args()
    
    setup_logging()
    logger.info("Starting ingestion process...")
    ensure_directories()
    
    repo = HLDRepository()
    repo.init_db()
    
    pdfs_to_process = []
    if args.file_path:
        file_path = Path(args.file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            sys.exit(1)
        pdfs_to_process.append(file_path)
    else:
        pdfs_to_process = list(RAW_DATA_DIR.glob("*.pdf"))
        if not pdfs_to_process:
            logger.info(f"No PDFs found in {RAW_DATA_DIR}")
            return

    total_chunks = 0
    total_docs = 0

    for pdf_path in pdfs_to_process:
        logger.info(f"Processing {pdf_path.name}...")
        try:
            # Parse PDF
            start_time = time.time()
            doc_data = parse_pdf(pdf_path, PROJECT_ID, args.version)
            
            # Chunk document
            chunks = chunk_document(doc_data)
            
            # Create metadata if not present
            if not doc_data.metadata:
                from ingestion.metadata import create_metadata
                doc_data.metadata = create_metadata(doc_data)
            
            # Save processed document
            from app.config import PROCESSED_DATA_DIR
            save_processed_document(doc_data, PROCESSED_DATA_DIR)
            
            # Save to DB
            repo.save_document(doc_data.metadata)
            repo.save_chunks(chunks)
            
            total_docs += 1
            total_chunks += len(chunks)
            
            duration = time.time() - start_time
            logger.info(f"Successfully processed {pdf_path.name}: {len(chunks)} chunks in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}", exc_info=True)

    print("\n" + "="*50)
    print("INGESTION SUMMARY")
    print("="*50)
    print(f"Documents processed: {total_docs}")
    print(f"Total chunks created: {total_chunks}")
    print("="*50)

if __name__ == "__main__":
    main()
