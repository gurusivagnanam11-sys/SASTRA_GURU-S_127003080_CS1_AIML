import sys
from pathlib import Path
import re

main_file = Path("c:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/main.py")
content = main_file.read_text(encoding="utf-8")

# 1. Add imports to FastAPI
content = re.sub(
    r"from fastapi import FastAPI, HTTPException, Query, status, Request",
    r"from fastapi import FastAPI, HTTPException, Query, status, Request, UploadFile, File, Form",
    content
)

# 2. Add dependencies for the route
import_str = """
from app.config import RAW_DATA_DIR, PROJECT_ID, PROCESSED_DATA_DIR
from ingestion.pdf_parser import parse_pdf
from chunking.hld_chunker import chunk_document
import shutil
import time
from db.repository import HLDRepository
from ingestion.metadata import create_metadata, save_processed_document
"""
content = re.sub(
    r"from extraction.basic_extractor import \(",
    import_str + "\n" + r"from extraction.basic_extractor import (",
    content
)

# 3. Add the upload route
upload_route = """

@app.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    version: str = Form(...),
    governance_status: str = Form("DRAFT")
):
    \"\"\"Upload, parse, chunk, and index a new HLD PDF document.\"\"\"
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    filename = Path(file.filename).name
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
        
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DATA_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")
        
    try:
        start_time = time.time()
        # Parse PDF
        doc_data = parse_pdf(file_path, PROJECT_ID, version)
        
        # Chunk document
        chunks = chunk_document(doc_data)
        
        # Metadata
        if not doc_data.metadata:
            doc_data.metadata = create_metadata(doc_data)
            
        # Set governance status
        doc_data.metadata["status"] = governance_status
        
        # Save processed data
        save_processed_document(doc_data, PROCESSED_DATA_DIR)
        
        # Save to DB
        repo = HLDRepository()
        repo.init_db()
        repo.save_document(doc_data.metadata)
        repo.save_chunks(chunks)
        
        # Trigger index rebuild
        index_result = trigger_indexing()
        
        return {
            "status": "indexed",
            "document": filename,
            "version": version,
            "pages": doc_data.metadata.get("pages", 0),
            "chunks": len(chunks),
            "ocr_pages": doc_data.metadata.get("ocr_pages", 0),
            "tables": doc_data.metadata.get("table_count", 0),
            "embedding_status": "created",
            "faiss_status": "updated",
            "message": index_result.get("message", "Index built successfully.")
        }
    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

"""
content = re.sub(
    r"@app.post\(\"/documents/index\"\)",
    upload_route.replace("\\", "\\\\") + r"@app.post(\"/documents/index\")",
    content
)

main_file.write_text(content, encoding="utf-8")
print("Updated app/main.py successfully.")
