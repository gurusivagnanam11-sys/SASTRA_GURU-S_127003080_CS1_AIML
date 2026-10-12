# Part 3: Stage 2 Retrieval & Routing
def get_stage2():
    return """  <!-- STAGE 2: RUNTIME QUERY & HYBRID RETRIEVAL (MIDDLE LANE) -->
  <g transform="translate(60, 480)">
    <rect width="2280" height="370" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="370" rx="4" fill="#059669"/>
    <text x="28" y="34" font-size="16" font-weight="800" fill="#064E3B">STAGE 2: QUERY HANDLING, INTENT ROUTING &amp; ARCHITECTURE-AWARE HYBRID RETRIEVAL</text>
    <rect x="740" y="18" width="120" height="22" rx="6" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1"/>
    <text x="748" y="33" font-size="11" font-weight="700" fill="#047857">RUNTIME Q&amp;A</text>
    <text x="28" y="54" font-size="12" font-weight="500" fill="#64748B">Accepts user architectural queries, validates inputs via FastAPI, routes architectural intent, and computes composite multi-signal ranking with version balancing.</text>

    <!-- Node 2.1: User Query / Streamlit UI -->
    <g transform="translate(28, 76)">
      <rect width="260" height="264" rx="10" fill="#F8FAFC" stroke="#A7F3D0" stroke-width="1.5"/>
      <rect x="12" y="12" width="236" height="24" rx="6" fill="#ECFDF5"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#065F46">6. USER QUERY (STREAMLIT)</text>
      <text x="16" y="56" font-size="13" font-weight="700" fill="#0F172A">app/streamlit_app.py</text>
      <text x="16" y="74" font-size="10.5" font-weight="500" fill="#475569">Port 8501 Browser Interface</text>
      <text x="16" y="94" font-size="11" font-weight="600" fill="#334155">Configurable Query Controls:</text>
      <rect x="14" y="102" width="232" height="110" rx="6" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1"/>
      <text x="22" y="120" font-size="10" font-weight="500" fill="#1E293B">  Question Input Box (5000 chars)</text>
      <text x="22" y="136" font-size="10" font-weight="500" fill="#1E293B">  Version: All / 1.0 / 2.0</text>
      <text x="22" y="152" font-size="10" font-weight="700" fill="#059669">  Mode: Hybrid / Baseline</text>
      <text x="22" y="168" font-size="10" font-weight="500" fill="#1E293B">  Provider: Ollama / Gemini / Mock</text>
      <text x="22" y="184" font-size="10" font-weight="500" fill="#1E293B">  Top-K: Default = 5 (slider 1-50)</text>
      <text x="22" y="200" font-size="9.5" font-weight="600" fill="#047857">Live KPI Metrics &amp; Audit Trace</text>
      <text x="16" y="232" font-size="9" font-weight="500" fill="#64748B" class="code-text">API_BASE_URL=http://hld-api:8000</text>
    </g>

    <path d="M 288 208 L 328 208" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)"/>

    <!-- Node 2.2: FastAPI Request Handling -->
    <g transform="translate(330, 76)">
      <rect width="270" height="264" rx="10" fill="#F8FAFC" stroke="#A7F3D0" stroke-width="1.5"/>
      <rect x="12" y="12" width="246" height="24" rx="6" fill="#ECFDF5"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#065F46">7. FASTAPI REST SERVICE</text>
      <text x="16" y="56" font-size="13" font-weight="700" fill="#0F172A">app/main.py (Port 8000)</text>
      <text x="16" y="74" font-size="10.5" font-weight="700" fill="#059669">  POST /query</text>
      <text x="16" y="92" font-size="10.5" font-weight="500" fill="#475569">  Pydantic schema validation:</text>
      <text x="20" y="108" font-size="9.5" font-weight="500" fill="#64748B" class="code-text">APIQueryRequest(question,...)</text>
      <rect x="14" y="122" width="242" height="90" rx="6" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1"/>
      <text x="20" y="138" font-size="10.5" font-weight="700" fill="#334155">Security &amp; Resilience Guards:</text>
      <text x="20" y="154" font-size="9.5" font-weight="500" fill="#475569">  Empty/whitespace query rejection</text>
      <text x="20" y="170" font-size="9.5" font-weight="500" fill="#475569">  Oversized input bound (5000 ch)</text>
      <text x="20" y="186" font-size="9.5" font-weight="500" fill="#475569">  Request-ID header: X-Request-ID</text>
      <text x="20" y="202" font-size="9.5" font-weight="500" fill="#475569">  CORS policy enabled</text>
      <path d="M 16 222 L 254 222" stroke="#E2E8F0" stroke-width="1"/>
      <text x="16" y="238" font-size="9" font-weight="600" fill="#334155">End-to-End Orchestrator:</text>
      <text x="16" y="252" font-size="8.5" font-weight="500" fill="#64748B" class="code-text">rag/pipeline.py :: RAGPipeline.ask()</text>
    </g>

    <path d="M 600 208 L 640 208" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)"/>

    <!-- Node 2.3: Query Router & Abstention Guard -->
    <g transform="translate(642, 76)">
      <rect width="320" height="264" rx="10" fill="#F8FAFC" stroke="#A7F3D0" stroke-width="1.5"/>
      <rect x="12" y="12" width="296" height="24" rx="6" fill="#ECFDF5"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#065F46">QUERY ROUTER &amp; ABSTENTION</text>
      <text x="16" y="56" font-size="13" font-weight="700" fill="#0F172A">rag/query_router.py</text>
      <text x="16" y="74" font-size="10.5" font-weight="500" fill="#475569">  Classifies engineering question intent</text>
      <text x="16" y="90" font-size="10.5" font-weight="500" fill="#475569">  Extracts entity hints &amp; target sections</text>
      <rect x="14" y="102" width="292" height="66" rx="6" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1"/>
      <text x="20" y="118" font-size="10" font-weight="700" fill="#334155">Detected Intent Categories:</text>
      <text x="20" y="132" font-size="9.5" font-weight="500" fill="#047857">  ARCHITECTURE / SWC / INTERFACE</text>
      <text x="20" y="146" font-size="9.5" font-weight="500" fill="#047857">  PORT ($6) / SIGNAL ($5) / FLOW</text>
      <text x="20" y="160" font-size="9.5" font-weight="500" fill="#047857">  REVISION_QUERY (Cross-Version Diff)</text>
      <!-- Abstention Callout -->
      <rect x="14" y="174" width="292" height="74" rx="6" fill="#FEF2F2" stroke="#FECACA" stroke-width="1"/>
      <rect x="20" y="180" width="80" height="16" rx="4" fill="#FEE2E2"/>
      <text x="24" y="192" font-size="9" font-weight="700" fill="#DC2626">CONDITIONAL</text>
      <text x="106" y="192" font-size="9.5" font-weight="600" fill="#991B1B">Unsupported Query</text>
      <text x="20" y="208" font-size="9.5" font-weight="500" fill="#7F1D1D">Adversarial &amp; Hardware Abstention:</text>
      <text x="20" y="222" font-size="9" font-weight="500" fill="#991B1B">  Microcontroller part #, CAN baud rate,</text>
      <text x="20" y="234" font-size="9" font-weight="500" fill="#991B1B">  Clock frequency, non-HLD ECU specs</text>
      <text x="20" y="244" font-size="8.5" font-weight="600" fill="#B91C1C">Immediate Grounded Abstention Response</text>
    </g>

    <path d="M 962 208 L 1002 208" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)"/>

    <!-- Node 2.4: Retrieval Branching (Baseline vs Hybrid) -->
    <g transform="translate(1004, 76)">
      <rect width="660" height="264" rx="10" fill="#F8FAFC" stroke="#A7F3D0" stroke-width="1.5"/>
      <rect x="12" y="12" width="636" height="24" rx="6" fill="#ECFDF5"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#065F46">8. RETRIEVAL ENGINE: BASELINE VS ARCHITECTURE-AWARE HYBRID</text>

      <!-- Branch A: Baseline -->
      <rect x="14" y="44" width="632" height="54" rx="6" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="24" y="62" font-size="10.5" font-weight="700" fill="#475569">BRANCH A: BASELINE</text>
      <text x="160" y="62" font-size="10" font-weight="600" fill="#334155">Dense Semantic Search Alone (BaselineRetriever)</text>
      <text x="24" y="78" font-size="9.5" font-weight="500" fill="#64748B">  Encodes query with BGE-small embedding model &#8594; FAISS L2/Cosine search</text>
      <text x="24" y="92" font-size="9.5" font-weight="500" fill="#64748B">  Pool size: search_k = min(N, max(top_k * 5, 25)) with version/project filter</text>

      <!-- Branch B: Hybrid -->
      <rect x="14" y="104" width="632" height="148" rx="6" fill="#F0FDF4" stroke="#86EFAC" stroke-width="1.2"/>
      <text x="24" y="122" font-size="11" font-weight="800" fill="#15803D">BRANCH B: HYBRID (DEFAULT)</text>
      <text x="190" y="122" font-size="10" font-weight="600" fill="#166534">Multi-Signal Architectural Fusion (HybridRetriever)</text>
      <!-- Formula box -->
      <rect x="24" y="130" width="612" height="26" rx="4" fill="#DCFCE7"/>
      <text x="32" y="148" font-size="10.5" font-weight="700" fill="#14532D">Composite Score = ( 0.50 &#215; Semantic + 0.30 &#215; Entity + 0.20 &#215; Section ) &#215; GovMultiplier</text>
      <text x="24" y="172" font-size="9.5" font-weight="500" fill="#166534">  Entity: SWC, Port, Signal, Interface match | Section: &#167;6 (Ports), &#167;5 (Signals), &#167;7 (Deps), &#167;4 (Interfaces)</text>
      <!-- Cross Version Balancing -->
      <path d="M 24 180 L 626 180" stroke="#BBF7D0" stroke-width="1"/>
      <text x="24" y="196" font-size="10" font-weight="700" fill="#14532D">Cross-Version Starvation Prevention &amp; Completeness Check:</text>
      <text x="24" y="210" font-size="9.5" font-weight="500" fill="#166534">  For revision queries across versions, enforces balanced top-k representation for both v1.0 and v2.0</text>
      <text x="24" y="224" font-size="9.5" font-weight="500" fill="#166534">  [Conditional] If evidence for either version is missing &#8594; Abstains rather than hallucinating comparison</text>
      <text x="24" y="240" font-size="9" font-weight="600" fill="#047857">Candidate Pool: candidate_pool = min(N, max(top_k * 20, 100))</text>
    </g>

    <path d="M 1664 208 L 1704 208" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)"/>

    <!-- Node 2.5: Retrieved Evidence Pool -->
    <g transform="translate(1706, 76)">
      <rect width="534" height="264" rx="10" fill="#F8FAFC" stroke="#A7F3D0" stroke-width="1.5"/>
      <rect x="12" y="12" width="510" height="24" rx="6" fill="#ECFDF5"/>
      <text x="20" y="28" font-size="11" font-weight="700" fill="#065F46">RETRIEVED EVIDENCE POOL &amp; EVALUATION</text>
      <text x="16" y="56" font-size="13" font-weight="700" fill="#0F172A">Ranked ContextChunk Objects</text>

      <!-- Candidate Record Structure Box -->
      <g transform="translate(14, 68)">
        <rect width="506" height="88" rx="6" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1"/>
        <text x="12" y="18" font-size="10.5" font-weight="700" fill="#1E293B">Candidate Record Structure:</text>
        <text x="12" y="34" font-size="10" font-weight="500" fill="#475569" class="code-text">  chunk_id: "autosar_hld__v2.0_p08_c34"</text>
        <text x="12" y="50" font-size="10" font-weight="500" fill="#475569" class="code-text">  document: "autosar_hld_v2.0", version: "2.0", page: 8</text>
        <text x="12" y="66" font-size="10" font-weight="500" fill="#475569" class="code-text">  section: "7.1", section_title: "Component Dependencies"</text>
        <text x="12" y="80" font-size="10" font-weight="500" fill="#475569" class="code-text">  text: "VehicleControl depends on PowertrainInterface..."</text>
      </g>

      <path d="M 14 166 L 520 166" stroke="#E2E8F0" stroke-width="1"/>
      <text x="14" y="184" font-size="11" font-weight="700" fill="#1E293B">Retrieval Benchmark Results (Empirical Verification):</text>
      <text x="14" y="202" font-size="10" font-weight="500" fill="#059669">  Baseline: Precision@5 = 0.583 | Recall@5 = 0.683 | MRR = 0.722</text>
      <text x="14" y="218" font-size="10" font-weight="700" fill="#047857">  Hybrid:   Precision@5 = 0.817 | Recall@5 = 0.917 | MRR = 0.958</text>
      <text x="14" y="234" font-size="9.5" font-weight="600" fill="#047857">+40.1% Hit Rate Improvement across Architectural Benchmarks</text>
      <text x="14" y="248" font-size="9" font-weight="500" fill="#64748B" class="code-text">Verified via tests/test_retrieval.py &amp; test_phase4.py</text>
    </g>
  </g>
  <path d="M 1641 460 L 1641 480" stroke="#4F46E5" stroke-width="2.5" stroke-dasharray="5 3" marker-end="url(#arrow-indigo)"/>"""
