import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.models import PageData, DocumentData, DocumentMetadata

logger = logging.getLogger(__name__)

def generate_document_id(filename: str) -> str:
    """Generate a stable document ID from filename.
    Remove extension, lowercase, replace spaces with underscores.
    """
    return filename.rsplit('.', 1)[0].lower().replace(' ', '_')

def create_metadata(document_data: DocumentData) -> DocumentMetadata:
    """Create metadata from parsed document data."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return DocumentMetadata(
        document_id=document_data.document_id,
        filename=document_data.filename,
        project_id=document_data.project_id,
        document_type="PDF",
        version=document_data.version,
        source="local_file",
        ingestion_timestamp=timestamp,
        page_count=len(document_data.pages)
    )

def save_processed_document(document_data: DocumentData, output_dir: Path) -> Path:
    """Save parsed document data as JSON for later processing.
    
    Saves to output_dir / {document_id}_v{version}.json
    Returns the output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{document_data.document_id}_v{document_data.version}.json"
    output_path = output_dir / filename
    
    try:
        data_dict = asdict(document_data)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved processed document to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error saving processed document: {e}")
        raise

def load_processed_document(json_path: Path) -> DocumentData:
    """Load a previously processed document from JSON."""
    if not json_path.exists():
        logger.error(f"File not found: {json_path}")
        raise FileNotFoundError(f"File not found: {json_path}")
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
            
        pages = []
        for p in data_dict.get('pages', []):
            pages.append(PageData(**p))
            
        metadata_dict = data_dict.get('metadata')
        metadata = DocumentMetadata(**metadata_dict) if metadata_dict else None
        
        return DocumentData(
            document_id=data_dict['document_id'],
            filename=data_dict['filename'],
            project_id=data_dict['project_id'],
            version=data_dict['version'],
            pages=pages,
            metadata=metadata
        )
    except Exception as e:
        logger.error(f"Error loading processed document {json_path}: {e}")
        raise
