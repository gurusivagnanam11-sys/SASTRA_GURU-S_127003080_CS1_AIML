import re
import logging
from typing import List, Dict, Optional

# Assuming models and config are available in the project structure
from ingestion.models import DocumentData, PageData
from chunking.models import HLDChunk

try:
    from app.config import CHUNK_MAX_CHARS
except ImportError:
    CHUNK_MAX_CHARS = 1500

logger = logging.getLogger(__name__)

def _classify_chunk_type(text: str, section: str, section_title: str) -> str:
    """Classify a text block's architecture type using heuristics.
    
    Heuristic priority:
    1. Section heading context
    2. Keywords in text
    3. Default to 'general'
    """
    text_lower = text.lower()
    section_lower = (section_title or "").lower()

    # 1. Component
    if 'component' in section_lower or 'swc' in section_lower:
        return 'component'
    if 'software component' in text_lower or 'swc' in text_lower:
        return 'component'

    # 2. Interface
    if 'interface' in section_lower:
        return 'interface'
    if any(kw in text_lower for kw in ['interface', 'client-server', 'sender-receiver']):
        return 'interface'

    # 3. Port
    if 'port' in section_lower:
        return 'port'
    if any(kw in text_lower for kw in ['port', 'input port', 'output port', 'require port', 'provide port']):
        return 'port'

    # 4. Signal
    if 'signal' in section_lower:
        return 'signal'
    if 'signal' in text_lower or 'data element' in text_lower:
        return 'signal'

    # 5. Dependency
    if any(kw in text_lower for kw in ['depends on', 'requires', 'dependency', 'consumes', 'produces', 'communicates with']):
        return 'dependency'

    # 6. Flow
    if any(kw in text_lower for kw in ['functional flow', 'data flow', 'control flow', 'sequence']):
        return 'flow'

    # 7. Table
    if text.strip().startswith('TABLE:') or '|' in text:
        return 'table'

    # 8. Architecture
    if any(kw in text_lower for kw in ['architecture', 'system design', 'layer']):
        return 'architecture'

    # 9. General/Unknown
    return 'general'

def _extract_entity_hint(text: str) -> str:
    """Extract the most prominent AUTOSAR entity name from text.
    
    Looks for CamelCase patterns and known architecture terms.
    """
    # Regex for CamelCase (e.g. VehicleControl, VehicleDataInterface)
    pattern = r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b'
    matches = re.findall(pattern, text)
    if matches:
        # Return the first or most frequent one; returning first for simplicity
        return matches[0]
    return ''

def _split_oversized_block(text: str, max_chars: int) -> List[str]:
    """Split an oversized block at paragraph or sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    # Try paragraph splitting first
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        if len(para) > max_chars:
            # If a single paragraph is too large, split by sentences
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_sent_chunk = ""
            for sent in sentences:
                if len(current_sent_chunk) + len(sent) + 1 <= max_chars:
                    current_sent_chunk = (current_sent_chunk + " " + sent).strip()
                else:
                    if current_sent_chunk:
                        chunks.append(current_sent_chunk)
                    # If single sentence is larger than max_chars, force split it
                    if len(sent) > max_chars:
                        # force split at max_chars
                        for i in range(0, len(sent), max_chars):
                            chunks.append(sent[i:i+max_chars])
                        current_sent_chunk = ""
                    else:
                        current_sent_chunk = sent
            if current_sent_chunk:
                chunks.append(current_sent_chunk)
        else:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk = (current_chunk + "\n\n" + para).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def _split_page_into_blocks(page: PageData) -> List[Dict]:
    """Split a page's text into logical blocks at heading and paragraph boundaries,
    and include extracted tables as separate blocks.
    """
    blocks = []
    
    # Split raw text by paragraph boundaries and numbered headings
    lines = page.raw_text.splitlines()
    current_block_lines = []
    
    for line in lines:
        l_str = line.strip()
        if not l_str:
            if current_block_lines:
                blocks.append({
                    'text': '\n'.join(current_block_lines),
                    'block_type': 'general',
                    'headings': page.headings
                })
                current_block_lines = []
            continue
            
        # Check if line looks like a heading
        if re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', l_str) and current_block_lines:
            blocks.append({
                'text': '\n'.join(current_block_lines),
                'block_type': 'general',
                'headings': page.headings
            })
            current_block_lines = [line]
        else:
            current_block_lines.append(line)
            
    if current_block_lines:
        full_text = '\n'.join(current_block_lines).strip()
        if full_text:
            b_type = 'table' if (full_text.startswith('TABLE:') or '|' in full_text) else 'general'
            blocks.append({
                'text': full_text,
                'block_type': b_type,
                'headings': page.headings
            })
        
    # Also add extracted tables if they are not already in raw text
    for tbl in (page.tables or []):
        tbl_strip = tbl.strip()
        if tbl_strip and not any(tbl_strip[:40] in b['text'] for b in blocks):
            blocks.append({
                'text': tbl_strip,
                'block_type': 'table',
                'headings': page.headings
            })
        
    return blocks

def chunk_document(document: DocumentData) -> List[HLDChunk]:
    """Chunk an entire parsed document into architecture-aware chunks.
    
    Args:
        document: Parsed document data
        
    Returns:
        List of HLDChunk objects with full provenance
    """
    chunks = []
    chunk_counter = 1
    # Create safe doc_id_short by sanitizing filename/id
    clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', document.document_id)
    doc_id_short = clean_id[:12]
    
    for page in document.pages:
        blocks = _split_page_into_blocks(page)
        
        for block in blocks:
            # Table chunks are preserved as whole if possible, otherwise split
            text_splits = _split_oversized_block(block['text'], CHUNK_MAX_CHARS)
            
            for split_text in text_splits:
                if not split_text.strip():
                    continue
                    
                chunk_type = _classify_chunk_type(
                    split_text, 
                    page.section or "", 
                    page.section_title or ""
                )
                
                # If block was already identified as table in split_page, keep it
                if block.get('block_type') == 'table':
                    chunk_type = 'table'
                    
                entity_hint = _extract_entity_hint(split_text)
                
                chunk_id = f"{doc_id_short}_v{document.version}_p{page.page_number:02d}_c{chunk_counter:02d}"
                
                content_type = 'table' if chunk_type == 'table' else ('ocr' if page.extraction_method == 'ocr' else 'text')
                
                hld_chunk = HLDChunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    project_id=document.project_id,
                    version=document.version,
                    page_number=page.page_number,
                    section=page.section or "",
                    section_title=page.section_title or "",
                    chunk_type=chunk_type,
                    entity_hint=entity_hint,
                    text=split_text,
                    extraction_method=getattr(page, 'extraction_method', 'text'),
                    content_type=content_type
                )
                chunks.append(hld_chunk)
                chunk_counter += 1
                
    return chunks
