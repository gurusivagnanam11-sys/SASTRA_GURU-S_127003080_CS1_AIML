# Part 5: Stage 5 Validation & Dedicated Architecture Validator
def get_stage5_and_validator():
    return """  <!-- STAGE 5: GROUNDING & VALIDATION (RIGHT-MIDDLE) -->
  <g transform="translate(1230, 870)">
    <rect width="630" height="370" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="370" rx="4" fill="#D97706"/>
    <text x="28" y="34" font-size="16" font-weight="800" fill="#78350F">STAGE 5: DETERMINISTIC GROUNDING &amp; CITATION VALIDATION</text>
    <rect x="520" y="18" width="90" height="22" rx="6" fill="#FFFBEB" stroke="#FDE68A" stroke-width="1"/>
    <text x="528" y="33" font-size="11" font-weight="700" fill="#B45309">DETERMINISTIC</text>
    <!-- Sub-node 5.1: JSON Repair & Parser -->
    <g transform="translate(20, 60)">
      <rect width="280" height="142" rx="8" fill="#F8FAFC" stroke="#FDE68A" stroke-width="1.2"/>
      <rect x="8" y="8" width="180" height="18" rx="4" fill="#FEF3C7"/>
      <text x="12" y="21" font-size="9.5" font-weight="700" fill="#92400E">11A. STRUCTURED PARSER</text>
      <text x="12" y="44" font-size="11" font-weight="700" fill="#1E293B">rag/pipeline.py :: _parse_llm_json</text>
      <text x="12" y="60" font-size="9.5" font-weight="500" fill="#475569">• Fenced markdown JSON extraction</text>
      <text x="12" y="74" font-size="9.5" font-weight="500" fill="#475569">• Stack-based auto-repair for truncated</text>
      <text x="18" y="88" font-size="9.5" font-weight="500" fill="#475569">tokens (unclosed braces/quotes)</text>
      <text x="12" y="104" font-size="9.5" font-weight="500" fill="#475569">• Regex field recovery fallback</text>
      <text x="12" y="122" font-size="9.5" font-weight="600" fill="#059669">Safe fallback prevents raw syntax leak</text>
    </g>
    <!-- Sub-node 5.2: Citation Validator -->
    <g transform="translate(316, 60)">
      <rect width="294" height="142" rx="8" fill="#F8FAFC" stroke="#FDE68A" stroke-width="1.2"/>
      <rect x="8" y="8" width="180" height="18" rx="4" fill="#FEF3C7"/>
      <text x="12" y="21" font-size="9.5" font-weight="700" fill="#92400E">11B. CITATION VALIDATOR</text>
      <text x="12" y="44" font-size="11" font-weight="700" fill="#1E293B">rag/citation_validator.py</text>
      <text x="12" y="60" font-size="9.5" font-weight="500" fill="#475569">• Validates cited exact <tspan class="code-text">chunk_id</tspan> against</text>
      <text x="18" y="74" font-size="9.5" font-weight="500" fill="#475569">retrieved evidence set</text>
      <text x="12" y="88" font-size="9.5" font-weight="500" fill="#475569">• Checks doc, ver, page metadata</text>
      <text x="12" y="104" font-size="9.5" font-weight="600" fill="#DC2626">• Disallows fabricated citation IDs</text>
      <text x="12" y="122" font-size="9.5" font-weight="600" fill="#B45309">Citation Coverage &amp; Precision Check</text>
    </g>
    <!-- Sub-node 5.3: Grounding Checker -->
    <g transform="translate(20, 214)">
      <rect width="590" height="140" rx="8" fill="#FFFBEB" stroke="#FDE68A" stroke-width="1.2"/>
      <rect x="8" y="8" width="260" height="18" rx="4" fill="#FEF3C7"/>
      <text x="12" y="21" font-size="9.5" font-weight="700" fill="#92400E">11C. DETERMINISTIC GROUNDING CHECKER</text>
      <text x="12" y="44" font-size="11" font-weight="700" fill="#0F172A">rag/grounding_checker.py (No Extra LLM Call - 100% Deterministic Python)</text>
      <g transform="translate(12, 54)">
        <text x="0" y="14" font-size="10" font-weight="600" fill="#78350F">1. Token Support Ratio:</text>
        <text x="130" y="14" font-size="9.5" font-weight="500" fill="#475569">Filters English &amp; reporting stopwords; requires &gt;= 60% content word support in cited chunk</text>
        <text x="0" y="32" font-size="10" font-weight="600" fill="#78350F">2. Version Alignment:</text>
        <text x="130" y="32" font-size="9.5" font-weight="500" fill="#475569">Prevents claims stating version 2.0 properties from citing version 1.0 chunks</text>
        <text x="0" y="50" font-size="10" font-weight="600" fill="#78350F">3. Contradiction Guard:</text>
        <text x="130" y="50" font-size="9.5" font-weight="500" fill="#475569"><tspan class="code-text">check_claim_contradictions</tspan>: Validates signal datatypes (e.g. VehicleSpeed float32 vs float64)</text>
        <text x="0" y="68" font-size="10" font-weight="600" fill="#78350F">4. Confidence Rating:</text>
        <text x="130" y="68" font-size="9.5" font-weight="700" fill="#047857">HIGH (Score&gt;=0.85 &amp; Sim&gt;=0.60) | MEDIUM | LOW (Grounding&lt;0.60 or Citation Invalid)</text>
      </g>
    </g>
  </g>
  <path d="M 1210 1055 L 1230 1055" stroke="#9333EA" stroke-width="2" marker-end="url(#arrow-purple)"/>

  <!-- DEDICATED MODULE: ARCHITECTURE VALIDATOR & GOVERNANCE (FAR-RIGHT) -->
  <g transform="translate(1880, 870)">
    <rect width="460" height="370" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="370" rx="4" fill="#EA580C"/>
    <text x="24" y="34" font-size="15" font-weight="800" fill="#7C2D12">12. ARCHITECTURE VALIDATOR &amp; GOVERNANCE</text>
    <rect x="330" y="18" width="116" height="22" rx="6" fill="#FFF7ED" stroke="#FFEDD5" stroke-width="1"/>
    <text x="338" y="33" font-size="10" font-weight="700" fill="#EA580C">DEDICATED MODULE</text>
    <text x="24" y="56" font-size="11" font-weight="600" fill="#C2410C">analysis/architecture_validator.py</text>
    <text x="24" y="72" font-size="10" font-weight="500" fill="#64748B">Triggered via <tspan class="code-text" fill="#0F172A">GET /architecture/validate</tspan> or UI Explorer tab. <tspan font-weight="700" fill="#7C2D12">(NOT triggered per standard Q&amp;A query!)</tspan></text>
    <!-- Structural Consistency Rules -->
    <rect x="18" y="84" width="424" height="168" rx="8" fill="#FFF7ED" stroke="#FED7AA" stroke-width="1.2"/>
    <text x="26" y="104" font-size="11" font-weight="700" fill="#9A3412">8 Deterministic Consistency Checks:</text>
    <g transform="translate(26, 114)">
      <text x="0" y="14" font-size="9.5" font-weight="500" fill="#7C2D12">• UNDEFINED_REFERENCE: Ports referencing unmapped SWC</text>
      <text x="0" y="30" font-size="9.5" font-weight="500" fill="#7C2D12">• MISSING_REFERENCE: Interfaces lacking valid signals</text>
      <text x="0" y="46" font-size="9.5" font-weight="500" fill="#7C2D12">• ORPHAN_ENTITY: Isolated components with 0 ports/deps</text>
      <text x="0" y="62" font-size="9.5" font-weight="500" fill="#7C2D12">• INVALID_RELATIONSHIP: Inconsistent port directions</text>
      <text x="0" y="78" font-size="9.5" font-weight="500" fill="#7C2D12">• MISSING_MAPPING: Unmapped signals / interfaces</text>
      <text x="0" y="94" font-size="9.5" font-weight="500" fill="#7C2D12">• INCOMPLETE_ENTITY / DUPLICATE_ENTITY</text>
      <text x="0" y="110" font-size="9.5" font-weight="500" fill="#7C2D12">• VERSION_INCONSISTENCY: Cross-release anomalies</text>
      <text x="0" y="130" font-size="9.5" font-weight="700" fill="#C2410C">Outputs Findings: finding_id, severity, provenance</text>
    </g>
    <!-- Review Submission Box -->
    <rect x="18" y="260" width="424" height="96" rx="8" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
    <text x="26" y="280" font-size="11" font-weight="700" fill="#1E293B">Human-in-the-Loop Governance:</text>
    <text x="26" y="298" font-size="10" font-weight="500" fill="#475569">• Gating flag: <tspan class="code-text" font-weight="700">review_required = true</tspan> on low confidence,</text>
    <text x="32" y="312" font-size="10" font-weight="500" fill="#475569">insufficient evidence, or detected contradictions</text>
    <text x="26" y="328" font-size="10" font-weight="500" fill="#475569">• Engineer Review Recording: <tspan class="code-text">POST /reports/reviews</tspan></text>
    <text x="26" y="344" font-size="9.5" font-weight="600" fill="#059669">Audit trail persisted in SQLite (tests/test_phase8_reports_governance.py)</text>
  </g>
  <path d="M 1860 1055 L 1880 1055" stroke="#EA580C" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#arrow-orange)"/>
  <rect x="1814" y="1030" width="112" height="18" rx="4" fill="#FFF7ED" stroke="#FFEDD5" stroke-width="1"/>
  <text x="1820" y="1042" font-size="8.5" font-weight="700" fill="#C2410C">Optional Audit</text>"""