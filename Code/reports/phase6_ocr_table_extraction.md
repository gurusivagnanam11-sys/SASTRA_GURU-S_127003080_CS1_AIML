# Phase 6: OCR and Table Extraction

## 1. Objective
The objective of Phase 6 was to implement OCR fallback for scanned or image-only PDF pages and introduce robust table extraction capabilities without rebuilding the application or altering the existing RAG and FastAPI structures.

## 2. Existing Ingestion Architecture
The existing ingestion architecture parsed PDFs page by page, tracking section titles using heuristic-based font sizing, and created `PageData` objects. The text chunks were then routed through chunking logic, resulting in highly granular `HLDChunk` objects stored natively within SQLite and FAISS.

## 3. OCR Approach
An OCR integration strategy was deployed utilizing `pytesseract` linked with PyMuPDF's (`fitz`) native pixel rendering map. OCR acts strictly as a non-mandatory fallback to preserve computational efficiency, executing only when a page lacks substantial selectable text content. The library dependency remains fully local.

## 4. OCR Fallback Logic
The system inspects the textual character length extracted natively. If the character count (excluding whitespaces) falls below 50, the document is categorized as potentially image-based or scanned. The OCR pipeline then reads the internal image array, generating `pytesseract` readable characters. If the resulting text is larger, it replaces the native text extract.

## 5. Table Extraction Approach
PyMuPDF's `find_tables()` engine was leveraged to natively read line boundaries and construct standard multi-row architectures. The extracted tables are mapped directly, discarding empty noise headers and retaining clean row architectures.

## 6. Table Data Model
Tables are structured in a deterministic representation explicitly formatted to align with the FAISS nearest neighbor model mapping architecture. Empty cells are discarded while standard formatting preserves keys to structure headers against values.

Example implementation logic outputs tables as:
```text
TABLE:
Header1: Value1
Header2: Value2

Header1: Value3
Header2: Value4
```

## 7. Table-Aware Chunking
Tables are retained as unified chunks by categorizing strings beginning with `TABLE:` and tagging their semantic architecture class natively as `table`. Table integrity is verified recursively by preserving lines to prevent splitting logical groups. The `HLDChunk` and `Chunk` database model properties were enhanced with both `extraction_method` and `content_type` tracking schemas.

## 8. RAG Integration
Tables have been unified into FAISS by embedding their deterministic textual structures. Queries requesting granular mapping (e.g., interface assignments or port routing maps) locate tables effectively. The standard hybrid FAISS + Semantic retriever integrates these metrics naturally with no prompt adjustment requirements.

## 9. Citation/Provenance Handling
By routing `extraction_method` and `content_type` attributes straight from the `PageData` parsing stage to chunking mapping strategies (including metadata dictionary insertion), RAG automatically traces evidence provenance to tables and OCR sources. Page and table boundaries operate identically to section citations.

## 10. Security Considerations
OCR and structural reading methodologies inherit existing Path Traversal prevention rules from Phase 5. The PyMuPDF byte mapping and internal validation strategies execute directly inside RAM to minimize filesystem I/O footprint vulnerability, remaining compliant with existing architectural audits.

## 11. Tests Added
Four comprehensive behavioral test schemas were added to `tests/test_phase6.py`:
- `test_mixed_pdf_processing`: Confirms normal text skips OCR, image pages trigger OCR, and tables map natively.
- `test_ocr_failure_graceful`: Checks graceful skipping of missing dependency or failed processing logic returning safe empty strings.
- `test_table_extraction_format`: Verifies tabular structured strings map deterministic patterns efficiently.
- `test_chunking_preserves_provenance`: Verifies chunk extraction methodologies retain `ocr` and `table` schemas explicitly in `chunk_type` and `extraction_method`.

## 12. Regression Results
All original evaluation and unit tests ran comprehensively in the pytest module:
- Total tests passed: **151**
- Tests Failed: **0**
- Baseline performance and regression stability remain securely at **100%**.

## 13. Performance Observations
Normal extraction methodologies remain aggressively fast, bypassing OCR unless manually triggered via size discrepancy. OCR introduces slight page-by-page mapping delays native to Python image-to-string translation models but only when an image page requires evaluation. Table mapping operates synchronously and is incredibly performant, presenting near-zero latency degradation.

## 14. Limitations
- Tesseract Dependency: Requires an active, locally installed `tesseract` OCR binary executable in PATH.
- Complex Formatting: Scanned architectural schemas lacking structural borders cannot be dynamically categorized as tables by standard boundary detectors and fall back accurately to OCR strings.

## 15. Final Verdict
Phase 6 securely addresses mixed PDF architecture mapping and nested structural engineering extraction boundaries. Table provenance effectively surfaces within vector responses alongside granular RAG architecture, concluding this phase successfully.
