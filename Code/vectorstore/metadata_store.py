import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from chunking.models import HLDChunk

logger = logging.getLogger(__name__)

class MetadataStore:
    def __init__(self):
        self.entries: List[dict] = []  # index position = FAISS ID

    def add_chunk(self, chunk: Any) -> int:
        """Add a chunk's metadata. Returns the FAISS ID (index position)."""
        faiss_id = len(self.entries)
        
        if isinstance(chunk, dict):
            entry = {
                "faiss_id": faiss_id,
                "chunk_id": chunk.get("chunk_id", ""),
                "document_id": chunk.get("document_id", ""),
                "project_id": chunk.get("project_id", ""),
                "version": chunk.get("version", ""),
                "page_number": chunk.get("page_number", 1),
                "section": chunk.get("section", ""),
                "section_title": chunk.get("section_title", ""),
                "chunk_type": chunk.get("chunk_type", "general"),
                "entity_hint": chunk.get("entity_hint", ""),
                "text": chunk.get("text", "")
            }
        else:
            entry = {
                "faiss_id": faiss_id,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "project_id": getattr(chunk, "project_id", ""),
                "version": chunk.version,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "section_title": chunk.section_title,
                "chunk_type": chunk.chunk_type,
                "entity_hint": chunk.entity_hint,
                "text": chunk.text
            }
        self.entries.append(entry)
        return faiss_id

    def get_by_faiss_id(self, faiss_id: int) -> dict:
        """Get chunk metadata by FAISS index position."""
        if faiss_id < 0 or faiss_id >= len(self.entries):
            raise IndexError(f"FAISS ID {faiss_id} out of bounds.")
        return self.entries[faiss_id]

    def get_by_chunk_id(self, chunk_id: str) -> Optional[dict]:
        """Get chunk metadata by chunk_id."""
        for entry in self.entries:
            if entry.get("chunk_id") == chunk_id:
                return entry
        return None

    def filter(self, **kwargs) -> List[int]:
        """Return FAISS IDs matching filter criteria.
        
        Supports: version, document_id, project_id, chunk_type, section
        """
        result_ids = []
        for entry in self.entries:
            match = True
            for k, v in kwargs.items():
                if entry.get(k) != v:
                    match = False
                    break
            if match:
                result_ids.append(entry["faiss_id"])
        return result_ids

    def save(self, path: Path) -> None:
        """Save metadata to JSON file."""
        logger.info(f"Saving {len(self.entries)} metadata entries to {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def load(self, path: Path) -> None:
        """Load metadata from JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found at {path}")
            
        logger.info(f"Loading metadata from {path}")
        with open(path, 'r', encoding='utf-8') as f:
            self.entries = json.load(f)
            
        logger.info(f"Loaded {len(self.entries)} metadata entries.")

    @property
    def count(self) -> int:
        return len(self.entries)
