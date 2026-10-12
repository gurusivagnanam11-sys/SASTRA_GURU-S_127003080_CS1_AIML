# Part 2: Stage 1 Ingestion
def get_stage1():
    return """  <!-- STAGE 1: INGESTION PIPELINE (TOP LANE) -->
  <g transform="translate(60, 160)">
    <rect width="2280" height="300" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="300" rx="4" fill="#4F46E5"/>
    <text x="28" y="34" font-size="16" font-weight="800" fill="#1E1B4B">STAGE 1: DOCUMENT INGESTION, STRUCTURAL CHUNKING &amp; EMBEDDING GENERATION</text>
    <rect x="710" y="18" width="140" height="22" rx="6" fill="#EEF2FF" stroke="#C7D2FE" stroke-width="1"/>
    <text x="718" y="33" font-size="11" font-weight="700" fill="#4338CA">BATCH &amp; ON-DEMAND</text>
    <text x="28" y="54" font-size="12" font-weight="500" fill="#64748B">Parses AUTOSAR High-Level Design PDFs (v1.0 &amp; v2.0), applies table extraction with OCR fallback, classifies architectural semantic blocks, and stores dense embeddings.</text>

    <!-- Node 1.1: PDF Input & Upload -->
    <g transform="translate(28, 72)">
      <rect width="250" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="226" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">1. HLD PDF INGESTION</text>
      <text x="16" y="58" font-size="13" font-weight="700" fill="#0F172A">AUTOSAR HLD Documents</text>
      <text x="16" y="78" font-size="11" font-weight="500" fill="#475569">  AUTOSAR_HLD_v1.0.pdf</text>
      <text x="16" y="96" font-size="11" font-weight="500" fill="#475569">  AUTOSAR_HLD_v2.0.pdf</text>
      <text x="16" y="114" font-size="11" font-weight="500" fill="#475569">  External / Customer Addenda</text>
      <path d="M 16 126 L 234 126" stroke="#E2E8F0" stroke-width="1"/>
      <text x="16" y="144" font-size="11" font-weight="600" fill="#334155">Ingestion Entrypoints:</text>
      <text x="16" y="162" font-size="10.5" font-weight="500" fill="#475569" class="code-text">  POST /documents/upload</text>
      <text x="16" y="178" font-size="10.5" font-weight="500" fill="#475569" class="code-text">  scripts/ingest_document.py</text>
      <text x="16" y="196" font-size="9.5" font-weight="600" fill="#059669">Sanitization &amp; Path Traversal Guard</text>
    </g>

    <path d="M 280 174 L 314 174" stroke="#4F46E5" stroke-width="2" marker-end="url(#arrow-indigo)"/>

    <!-- Node 1.2: Text & Table Extraction -->
    <g transform="translate(316, 72)">
      <rect width="320" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="296" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">2. PARSING &amp; OCR FALLBACK</text>
      <text x="16" y="58" font-size="13" font-weight="700" fill="#0F172A">ingestion/pdf_parser.py</text>
      <text x="16" y="78" font-size="11" font-weight="500" fill="#475569">  <tspan font-weight="700">PyMuPDF (fitz)</tspan> text stream extraction</text>
      <text x="16" y="96" font-size="11" font-weight="500" fill="#475569">  Table matrix extraction (page.find_tables)</text>
      <text x="16" y="114" font-size="11" font-weight="500" fill="#475569">  Heading font-size heuristic detection</text>
      <!-- OCR Fallback callout box -->
      <rect x="14" y="126" width="292" height="66" rx="6" fill="#FFFBEB" stroke="#FDE68A" stroke-width="1"/>
      <rect x="20" y="132" width="76" height="16" rx="4" fill="#FEF3C7"/>
      <text x="24" y="144" font-size="9" font-weight="700" fill="#B45309">CONDITIONAL</text>
      <text x="104" y="144" font-size="9.5" font-weight="600" fill="#B45309">len(raw_text) &lt; 50 Chars</text>
      <text x="20" y="160" font-size="10" font-weight="500" fill="#78350F">  Triggers Tesseract OCR fallback (pytesseract)</text>
      <text x="20" y="174" font-size="10" font-weight="500" fill="#78350F">  Handles scanned diagrams / raster drawings</text>
      <text x="20" y="186" font-size="9" font-weight="500" fill="#92400E">Graceful fallback if OCR binaries missing on host</text>
    </g>

    <path d="M 638 174 L 672 174" stroke="#4F46E5" stroke-width="2" marker-end="url(#arrow-indigo)"/>

    <!-- Node 1.3: Architecture-Aware Chunking -->
    <g transform="translate(674, 72)">
      <rect width="360" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="336" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">3. ARCHITECTURE-AWARE CHUNKING</text>
      <text x="16" y="58" font-size="13" font-weight="700" fill="#0F172A">chunking/hld_chunker.py</text>
      <text x="16" y="78" font-size="11" font-weight="500" fill="#475569">  Window: max 1500 chars (CHUNK_MAX_CHARS)</text>
      <text x="16" y="94" font-size="11" font-weight="500" fill="#475569">  Sentence &amp; table boundary preservation</text>
      <text x="16" y="112" font-size="11" font-weight="600" fill="#334155">Semantic Entity Classification:</text>
      <g transform="translate(16, 120)">
        <rect x="0" y="0" width="60" height="18" rx="4" fill="#E0E7FF"/><text x="6" y="13" font-size="9" font-weight="600" fill="#3730A3">component</text>
        <rect x="66" y="0" width="50" height="18" rx="4" fill="#CFFAFE"/><text x="73" y="13" font-size="9" font-weight="600" fill="#0E7490">interface</text>
        <rect x="122" y="0" width="34" height="18" rx="4" fill="#DCFCE7"/><text x="128" y="13" font-size="9" font-weight="600" fill="#15803D">port</text>
        <rect x="162" y="0" width="42" height="18" rx="4" fill="#FEF3C7"/><text x="168" y="13" font-size="9" font-weight="600" fill="#B45309">signal</text>
        <rect x="210" y="0" width="66" height="18" rx="4" fill="#FCE7F3"/><text x="216" y="13" font-size="9" font-weight="600" fill="#BE185D">dependency</text>
      </g>
      <path d="M 16 148 L 344 148" stroke="#E2E8F0" stroke-width="1"/>
      <text x="16" y="164" font-size="10.5" font-weight="600" fill="#334155">Metadata Attributes Associated:</text>
      <text x="16" y="180" font-size="9.5" font-weight="500" fill="#64748B" class="code-text">chunk_id, doc_id, project_id, version, page,</text>
      <text x="16" y="194" font-size="9.5" font-weight="500" fill="#64748B" class="code-text">section, section_title, chunk_type, entity_hint</text>
    </g>

    <path d="M 1036 174 L 1070 174" stroke="#4F46E5" stroke-width="2" marker-end="url(#arrow-indigo)"/>

    <!-- Node 1.4: Embedding Generation -->
    <g transform="translate(1072, 72)">
      <rect width="350" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="326" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">4. DENSE EMBEDDING MODEL</text>
      <text x="16" y="58" font-size="13" font-weight="700" fill="#0F172A">embeddings/embedder.py</text>
      <text x="16" y="78" font-size="11" font-weight="500" fill="#475569">  Framework: SentenceTransformer</text>
      <text x="16" y="96" font-size="11" font-weight="700" fill="#4F46E5">  Model: BAAI/bge-small-en-v1.5</text>
      <text x="16" y="114" font-size="11" font-weight="700" fill="#059669">  Dimension: 384 Dimensions</text>
      <text x="16" y="132" font-size="11" font-weight="500" fill="#475569">  Normalization: <tspan font-weight="700">L2 Unit Norm</tspan> (||v||=1)</text>
      <text x="16" y="150" font-size="11" font-weight="500" fill="#475569">  Batch Size: 32 chunks per forward pass</text>
      <path d="M 16 162 L 334 162" stroke="#E2E8F0" stroke-width="1"/>
      <text x="16" y="178" font-size="10" font-weight="600" fill="#334155">Offline Cache Policy:</text>
      <text x="16" y="192" font-size="9" font-weight="500" fill="#64748B" class="code-text">HF_HUB_OFFLINE=1, PyTorch CPU Inference</text>
    </g>

    <path d="M 1424 174 L 1454 174" stroke="#4F46E5" stroke-width="2" marker-end="url(#arrow-indigo)"/>

    <!-- Node 1.5: FAISS Vector Index & Storage -->
    <g transform="translate(1456, 72)">
      <rect width="370" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="346" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">5. VECTOR STORE &amp; PERSISTENCE</text>
      <text x="16" y="56" font-size="13" font-weight="700" fill="#0F172A">Dual Storage Architecture</text>
      <g transform="translate(14, 66)">
        <rect width="342" height="60" rx="6" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="12" y="20" font-size="11" font-weight="700" fill="#1E293B">A. Dense Vector Index (FAISS)</text>
        <text x="12" y="36" font-size="10" font-weight="500" fill="#475569">  Type: <tspan class="code-text" fill="#0F172A">faiss.IndexFlatIP</tspan> (Exact Cosine Sim)</text>
        <text x="12" y="50" font-size="9.5" font-weight="500" fill="#64748B" class="code-text">File: data/indexes/hld_index.faiss</text>
      </g>
      <g transform="translate(14, 134)">
        <rect width="342" height="62" rx="6" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
        <text x="12" y="18" font-size="11" font-weight="700" fill="#1E293B">B. Metadata &amp; Document Governance</text>
        <text x="12" y="34" font-size="10" font-weight="500" fill="#475569">  Catalog: <tspan class="code-text">data/indexes/hld_metadata.json</tspan></text>
        <text x="12" y="50" font-size="10" font-weight="500" fill="#475569">  SQLite DB: <tspan class="code-text">data/autosar_hld.db</tspan> (Reviews &amp; Audits)</text>
      </g>
    </g>

    <!-- Node 1.6: Governance Multiplier Policy -->
    <g transform="translate(1850, 72)">
      <rect width="400" height="204" rx="10" fill="#F8FAFC" stroke="#C7D2FE" stroke-width="1.5"/>
      <rect x="12" y="12" width="376" height="24" rx="6" fill="#EEF2FF"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#3730A3">INGESTION VALIDATION &amp; GOVERNANCE</text>
      <text x="16" y="56" font-size="12" font-weight="700" fill="#0F172A">Document Governance Statuses:</text>

      <rect x="16" y="66" width="70" height="18" rx="4" fill="#DCFCE7" stroke="#BBF7D0" stroke-width="1"/>
      <text x="22" y="79" font-size="9" font-weight="700" fill="#166534">APPROVED</text>
      <text x="96" y="80" font-size="10.5" font-weight="500" fill="#475569">(Weight Multiplier: 1.0)</text>

      <rect x="16" y="88" width="56" height="18" rx="4" fill="#FEF3C7" stroke="#FDE68A" stroke-width="1"/>
      <text x="24" y="101" font-size="9" font-weight="700" fill="#92400E">DRAFT</text>
      <text x="96" y="102" font-size="10.5" font-weight="500" fill="#475569">(Weight Multiplier: 0.60)</text>

      <rect x="16" y="110" width="70" height="18" rx="4" fill="#FEE2E2" stroke="#FECACA" stroke-width="1"/>
      <text x="20" y="123" font-size="9" font-weight="700" fill="#991B1B">ARCHIVED</text>
      <text x="96" y="124" font-size="10.5" font-weight="500" fill="#475569">(Weight Multiplier: 0.30)</text>

      <path d="M 16 136 L 384 136" stroke="#E2E8F0" stroke-width="1"/>
      <text x="16" y="152" font-size="11" font-weight="700" fill="#1E293B">Verification Test Suite:</text>
      <text x="16" y="168" font-size="10" font-weight="500" fill="#475569" class="code-text">  tests/test_chunker.py (10+ chunks/doc)</text>
      <text x="16" y="184" font-size="10" font-weight="500" fill="#475569" class="code-text">  tests/test_faiss.py &amp; test_metadata.py</text>
      <text x="16" y="198" font-size="10" font-weight="500" fill="#475569" class="code-text">  tests/test_phase8_ingestion.py</text>
    </g>
  </g>"""
