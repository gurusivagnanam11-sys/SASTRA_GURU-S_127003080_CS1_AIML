# Part 6: Final User-Facing Output, Governance Card, and Safety Boundaries
def get_part6():
    return """  <!-- SECTION 4: USER-FACING SYNTHESIS & GOVERNANCE BOUNDARIES -->
  <rect x="40" y="1260" width="2320" height="330" rx="16" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
  <rect x="40" y="1260" width="2320" height="38" rx="16" fill="#F8FAFC"/>
  <rect x="40" y="1290" width="2320" height="8" fill="#F8FAFC"/>
  <text x="64" y="1285" font-size="14" font-weight="800" fill="#0F172A">PHASE 4: RESPONSE SYNTHESIS, TRACEABILITY CITATIONS &amp; GOVERNANCE GATING</text>
  <text x="720" y="1285" font-size="12" font-weight="600" fill="#475569">Final RAGResponse Schema, Streamlit UI Rendering, and Capstone Safety Boundaries</text>

  <!-- Connectors from Stage 5 down to Phase 4 -->
  <path d="M 1520 1240 L 1520 1260" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)"/>
  <path d="M 2110 1240 L 2110 1260" stroke="#EA580C" stroke-width="2.5" stroke-dasharray="6 4" marker-end="url(#arrow-orange)"/>

  <!-- CARD 13A: STRUCTURED RAGRESPONSE SCHEMA -->
  <g transform="translate(64, 1310)">
    <rect width="700" height="260" rx="12" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>
    <rect x="0" y="0" width="6" height="260" rx="3" fill="#0284C7"/>
    <text x="20" y="28" font-size="13.5" font-weight="800" fill="#0F172A">13. STRUCTURED RAGRESPONSE PAYLOAD</text>
    <rect x="540" y="14" width="145" height="20" rx="6" fill="#F0FDF4" stroke="#DCFCE7" stroke-width="1"/>
    <text x="548" y="28" font-size="9.5" font-weight="700" fill="#059669">SCHEMA VERIFIED</text>
    <text x="20" y="46" font-size="10" font-weight="600" fill="#0284C7">app/schemas.py &amp; rag/prompts.py: parse_llm_json_response()</text>
    <rect x="16" y="58" width="668" height="186" rx="8" fill="#0F172A"/>
    <g transform="translate(28, 70)">
      <text x="0" y="16" font-size="10.5" font-weight="500" fill="#94A3B8" class="code-text">{</text>
      <text x="16" y="32" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"answer"<tspan fill="#94A3B8">: </tspan><tspan fill="#FCD34D">"The VehicleSpeed signal is routed via CanIf to Com... [C1][C2]"</tspan><tspan fill="#94A3B8">,</tspan></text>
      <text x="16" y="48" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"sources"<tspan fill="#94A3B8">: [ { </tspan><tspan fill="#A7F3D0">"document"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#FCD34D">"AUTOSAR_EXP_VFB.pdf"</tspan><tspan fill="#94A3B8">, </tspan><tspan fill="#A7F3D0">"page"</tspan><tspan fill="#94A3B8">: 24, </tspan><tspan fill="#A7F3D0">"section"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#FCD34D">"Signal Routing"</tspan><tspan fill="#94A3B8"> } ],</tspan></text>
      <text x="16" y="64" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"grounding_status"<tspan fill="#94A3B8">: </tspan><tspan fill="#34D399">"GROUNDED"</tspan><tspan fill="#94A3B8">,  </tspan><tspan fill="#64748B">// GROUNDED | PARTIALLY_GROUNDED | UNGROUNDED</tspan></text>
      <text x="16" y="80" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"contradiction_detected"<tspan fill="#94A3B8">: </tspan><tspan fill="#F87171">false</tspan><tspan fill="#94A3B8">,</tspan></text>
      <text x="16" y="96" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"review_required"<tspan fill="#94A3B8">: </tspan><tspan fill="#F87171">false</tspan><tspan fill="#94A3B8">,  </tspan><tspan fill="#64748B">// Set to true if confidence &lt; 0.60 or ungrounded</tspan></text>
      <text x="16" y="112" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"retrieval_mode"<tspan fill="#94A3B8">: </tspan><tspan fill="#FCD34D">"hybrid"</tspan><tspan fill="#94A3B8">,  </tspan><tspan fill="#64748B">// hybrid (semantic 0.50 + entity 0.30 + section 0.20)</tspan></text>
      <text x="16" y="128" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"confidence_score"<tspan fill="#94A3B8">: </tspan><tspan fill="#A7F3D0">0.94</tspan><tspan fill="#94A3B8">,</tspan></text>
      <text x="16" y="144" font-size="10.5" font-weight="500" fill="#38BDF8" class="code-text">"latency_ms"<tspan fill="#94A3B8">: </tspan><tspan fill="#A7F3D0">320.5</tspan><tspan fill="#94A3B8">,  </tspan><tspan fill="#A7F3D0">"version_comparison"</tspan><tspan fill="#94A3B8">: </tspan><tspan fill="#FCD34D">"None"</tspan></text>
      <text x="0" y="160" font-size="10.5" font-weight="500" fill="#94A3B8" class="code-text">}</text>
    </g>
  </g>

  <!-- CARD 13B: STREAMLIT UI PRESENTATION LAYER -->
  <g transform="translate(790, 1310)">
    <rect width="740" height="260" rx="12" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>
    <rect x="0" y="0" width="6" height="260" rx="3" fill="#2563EB"/>
    <text x="20" y="28" font-size="13.5" font-weight="800" fill="#0F172A">14. STREAMLIT INTERACTIVE USER INTERFACE</text>
    <rect x="570" y="14" width="150" height="20" rx="6" fill="#EFF6FF" stroke="#DBEAFE" stroke-width="1"/>
    <text x="578" y="28" font-size="9.5" font-weight="700" fill="#2563EB">PORT 8501 FRONTEND</text>
    <text x="20" y="46" font-size="10" font-weight="600" fill="#2563EB">ui/streamlit_app.py: Enterprise Multi-Tab Architecture</text>
    <!-- Feature grid -->
    <g transform="translate(20, 60)">
      <rect x="0" y="0" width="340" height="85" rx="8" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="20" font-size="11" font-weight="700" fill="#1E293B">Tab 1: Q&amp;A Assistant</text>
      <text x="12" y="36" font-size="9.5" font-weight="500" fill="#475569">  Rich Markdown rendered answers with [C1] tags</text>
      <text x="12" y="52" font-size="9.5" font-weight="500" fill="#475569">  Retrieval Mode switcher: Hybrid vs Baseline</text>
      <text x="12" y="68" font-size="9.5" font-weight="500" fill="#475569">  Version filter: All Releases / 4.2 / 4.4 / R20-11</text>

      <rect x="360" y="0" width="340" height="85" rx="8" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="372" y="20" font-size="11" font-weight="700" fill="#1E293B">Tab 2: Source Traceability</text>
      <text x="372" y="36" font-size="9.5" font-weight="500" fill="#475569">  Collapsible expanders for each cited chunk</text>
      <text x="372" y="52" font-size="9.5" font-weight="500" fill="#475569">  Shows exact Doc, Page, Section, and Cosine Score</text>
      <text x="372" y="68" font-size="9.5" font-weight="500" fill="#475569">  Highlighting of matched entities and signals</text>

      <rect x="0" y="95" width="340" height="85" rx="8" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="12" y="115" font-size="11" font-weight="700" fill="#1E293B">Tab 3: Architecture Explorer</text>
      <text x="12" y="131" font-size="9.5" font-weight="500" fill="#475569">  Triggers Architecture Consistency Validation</text>
      <text x="12" y="147" font-size="9.5" font-weight="500" fill="#475569">  Displays SWC topology and orphaned components</text>
      <text x="12" y="163" font-size="9.5" font-weight="500" fill="#475569">  Severity-coded anomaly badges (High/Med/Low)</text>

      <rect x="360" y="95" width="340" height="85" rx="8" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
      <text x="372" y="115" font-size="11" font-weight="700" fill="#1E293B">Tab 4: Governance &amp; Audit</text>
      <text x="372" y="131" font-size="9.5" font-weight="500" fill="#475569">  Human-in-the-Loop review feedback form</text>
      <text x="372" y="147" font-size="9.5" font-weight="500" fill="#475569">  Records approval / correction to SQLite DB</text>
      <text x="372" y="163" font-size="9.5" font-weight="500" fill="#475569">  Displays query latency &amp; token consumption</text>
    </g>
  </g>

  <!-- CARD 13C: CAPSTONE SAFETY & VERIFICATION BOUNDARIES -->
  <g transform="translate(1560, 1310)">
    <rect width="776" height="260" rx="12" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.5"/>
    <rect x="0" y="0" width="6" height="260" rx="3" fill="#D97706"/>
    <text x="20" y="28" font-size="13.5" font-weight="800" fill="#0F172A">15. SAFETY BOUNDARIES &amp; VERIFICATION ASSURANCE</text>
    <rect x="590" y="14" width="166" height="20" rx="6" fill="#FEF3C7" stroke="#FDE68A" stroke-width="1"/>
    <text x="598" y="28" font-size="9.5" font-weight="700" fill="#B45309">CAPSTONE GOVERNANCE</text>
    <text x="20" y="46" font-size="10" font-weight="600" fill="#D97706">Mandatory Regulatory &amp; Architectural Guardrails</text>

    <rect x="18" y="60" width="740" height="88" rx="8" fill="#FFFBEB" stroke="#FDE68A" stroke-width="1.2"/>
    <text x="30" y="80" font-size="11" font-weight="700" fill="#92400E">Automotive Compliance Boundaries (Non-Certified Disclaimer):</text>
    <text x="30" y="98" font-size="9.5" font-weight="500" fill="#78350F">  This system is an engineering research and traceability assistant; it is NOT certified under ISO 26262 ASIL A-D.</text>
    <text x="30" y="114" font-size="9.5" font-weight="500" fill="#78350F">  It does not constitute a qualified tool under ISO 26262-8:2018 Clause 11 (Tool Confidence Level TCL1-3).</text>
    <text x="30" y="130" font-size="9.5" font-weight="500" fill="#78350F">  All generated traceability matrices and architecture assessments require human sign-off before production use.</text>

    <rect x="18" y="156" width="740" height="90" rx="8" fill="#F0FDF4" stroke="#BBF7D0" stroke-width="1.2"/>
    <text x="30" y="176" font-size="11" font-weight="700" fill="#166534">Regression Test Suite Verification Summary:</text>
    <text x="30" y="194" font-size="9.5" font-weight="600" fill="#15803D">  191+ Unit, Integration, Security, and Governance Tests Executed and Passing</text>
    <text x="30" y="210" font-size="9.5" font-weight="500" fill="#166534">  Covering: Chunker (14 tests) | Security Injection &amp; Path Traversal (11 tests) | FAISS Search &amp; Index (13 tests)</text>
    <text x="30" y="226" font-size="9.5" font-weight="500" fill="#166534">  Cross-Version Balanced Retrieval (8 tests) | Phase 8 Governance &amp; Reports (11 tests) | Phase 2b-4 Integration (95 tests)</text>
    <text x="30" y="242" font-size="9" font-weight="700" fill="#0F766E">  Deterministic grounding verification guarantees zero ungrounded responses without review_required=true flag.</text>
  </g>
</svg>"""
