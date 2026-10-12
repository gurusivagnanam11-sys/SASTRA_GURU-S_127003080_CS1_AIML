# Part 4: Stage 3 & 4 (Context & Inference)
def get_stage3_and_4():
    return """  <!-- STAGE 3: CONTEXT ASSEMBLY & PROMPTS (LOWER-LEFT) -->
  <g transform="translate(60, 870)">
    <rect width="660" height="370" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="370" rx="4" fill="#0284C7"/>
    <text x="28" y="34" font-size="16" font-weight="800" fill="#0C4A6E">STAGE 3: CONTEXT ASSEMBLY &amp; RIGID PROMPT CONSTRUCTION</text>
    <rect x="520" y="18" width="120" height="22" rx="6" fill="#F0F9FF" stroke="#BAE6FD" stroke-width="1"/>
    <text x="530" y="33" font-size="11" font-weight="700" fill="#0284C7">GOVERNANCE</text>
    <!-- Context Builder -->
    <g transform="translate(24, 60)">
      <rect width="612" height="114" rx="8" fill="#F8FAFC" stroke="#BAE6FD" stroke-width="1.2"/>
      <rect x="10" y="8" width="220" height="20" rx="4" fill="#E0F2FE"/>
      <text x="16" y="22" font-size="10" font-weight="700" fill="#0369A1">9A. CONTEXT BUILDER (rag/context_builder.py)</text>
      <text x="12" y="44" font-size="10.5" font-weight="500" fill="#334155">• Deduplicates chunks and formats standard evidence headers:</text>
      <rect x="12" y="52" width="588" height="52" rx="4" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1"/>
      <text x="20" y="70" font-size="9" font-weight="500" fill="#0369A1" class="code-text">--- CHUNK: {chunk_id} | DOC: {doc} | VER: {ver} | PAGE: {p} | SEC: {sec} | TYPE: {type} ---</text>
      <text x="20" y="86" font-size="9" font-weight="500" fill="#334155" class="code-text">{exact_chunk_text}</text>
      <text x="20" y="98" font-size="8.5" font-weight="600" fill="#059669">Strictly isolates version 1.0 chunks from version 2.0 chunks in context string</text>
    </g>
    <!-- Prompts -->
    <g transform="translate(24, 186)">
      <rect width="612" height="168" rx="8" fill="#F8FAFC" stroke="#BAE6FD" stroke-width="1.2"/>
      <rect x="10" y="8" width="230" height="20" rx="4" fill="#E0F2FE"/>
      <text x="16" y="22" font-size="10" font-weight="700" fill="#0369A1">9B. PROMPT FACTORY (rag/prompts.py)</text>
      <text x="12" y="44" font-size="11" font-weight="700" fill="#0F172A">SYSTEM_PROMPT — 11 Critical Engineering Rules:</text>
      <text x="12" y="60" font-size="9.5" font-weight="500" fill="#475569">1. Grounded Answers Only | 2. No Fabrications | 3. No Extrapolations</text>
      <text x="12" y="74" font-size="9.5" font-weight="500" fill="#475569">4. Insufficient Evidence Abstention | 5. Exact Chunk ID Citations</text>
      <text x="12" y="88" font-size="9.5" font-weight="500" fill="#475569">6. True/False Architecture Distinction | 7. Multi-Version Separate Claims</text>
      <text x="12" y="102" font-size="9.5" font-weight="500" fill="#475569">8. Table Attribute Binding | 9. Architectural Integrity | 10. Prompt Injection Guard</text>
      <text x="12" y="116" font-size="9.5" font-weight="700" fill="#0369A1">11. Rigid Structured JSON Schema Output Only</text>
      <path d="M 12 126 L 600 126" stroke="#E2E8F0" stroke-width="1"/>
      <text x="12" y="144" font-size="10" font-weight="600" fill="#1E293B">build_user_prompt(question, context_str):</text>
      <text x="12" y="158" font-size="9" font-weight="500" fill="#64748B" class="code-text">Injects User Question, Evidence Context &amp; Cross-Version Comparison Directives</text>
    </g>
  </g>

  <!-- Flow Line from Stage 2 Evidence to Stage 3 -->
  <path d="M 1973 850 L 1973 860 L 390 860 L 390 870" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)"/>

  <!-- STAGE 4: MODEL INFERENCE (CENTER-BOTTOM) -->
  <g transform="translate(740, 870)">
    <rect width="470" height="370" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1.5" filter="url(#card-shadow)"/>
    <rect x="0" y="0" width="8" height="370" rx="4" fill="#9333EA"/>
    <text x="28" y="34" font-size="16" font-weight="800" fill="#581C87">STAGE 4: LOCAL &amp; CLOUD MODEL INFERENCE</text>
    <rect x="360" y="18" width="90" height="22" rx="6" fill="#FAF5FF" stroke="#E9D5FF" stroke-width="1"/>
    <text x="368" y="33" font-size="11" font-weight="700" fill="#9333EA">OFFLINE-1ST</text>
    <!-- Provider Factory -->
    <g transform="translate(20, 60)">
      <rect width="430" height="146" rx="8" fill="#F8FAFC" stroke="#E9D5FF" stroke-width="1.2"/>
      <text x="12" y="24" font-size="12" font-weight="700" fill="#0F172A">10. LLM PROVIDER FACTORY (rag/llm_provider.py)</text>
      <g transform="translate(12, 34)">
        <rect width="406" height="46" rx="6" fill="#FAF5FF" stroke="#D8B4FE" stroke-width="1"/>
        <text x="10" y="18" font-size="10.5" font-weight="800" fill="#6B21A8">PRIMARY: Local Ollama (Offline / Private)</text>
        <text x="10" y="34" font-size="9.5" font-weight="500" fill="#581C87">• Model: <tspan class="code-text" font-weight="700">qwen2.5:3b</tspan> | Base URL: http://localhost:11434</text>
      </g>
      <g transform="translate(12, 88)">
        <rect width="406" height="48" rx="6" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1"/>
        <text x="10" y="16" font-size="10" font-weight="700" fill="#334155">CLOUD: Google Gemini Free-Tier (Official google-genai SDK)</text>
        <text x="10" y="30" font-size="9.5" font-weight="500" fill="#475569">• Model: <tspan class="code-text">gemini-3.7-flash</tspan> (503 Fallback: gemini-3.1-flash-lite)</text>
        <text x="10" y="44" font-size="9" font-weight="600" fill="#059669">TEST / CI: MockLLMProvider (Deterministic Offline Evaluation)</text>
      </g>
    </g>
    <!-- Generation Parameters -->
    <g transform="translate(20, 218)">
      <rect width="430" height="136" rx="8" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.2"/>
      <text x="12" y="22" font-size="11" font-weight="700" fill="#1E293B">Configured Generation Parameters:</text>
      <text x="12" y="42" font-size="10.5" font-weight="500" fill="#475569">• Temperature: <tspan class="code-text" font-weight="700">0.1</tspan> (Deterministic Engineering Mode)</text>
      <text x="12" y="60" font-size="10.5" font-weight="500" fill="#475569">• Max Tokens: <tspan class="code-text" font-weight="700">2000</tspan> (<tspan class="code-text">LLM_MAX_OUTPUT_TOKENS</tspan>)</text>
      <text x="12" y="78" font-size="10.5" font-weight="500" fill="#475569">• Timeout: <tspan class="code-text" font-weight="700">180s</tspan> (<tspan class="code-text">LLM_TIMEOUT_SECONDS</tspan>)</text>
      <text x="12" y="96" font-size="10.5" font-weight="500" fill="#475569">• Response Format: <tspan class="code-text" font-weight="700">application/json</tspan> Enforced</text>
      <rect x="12" y="106" width="406" height="22" rx="4" fill="#FAF5FF" stroke="#D8B4FE" stroke-width="1"/>
      <text x="18" y="120" font-size="9.5" font-weight="600" fill="#6B21A8">Zero Hardware Accelerators Needed: CPU-Optimized</text>
    </g>
  </g>
  <path d="M 720 1055 L 740 1055" stroke="#0284C7" stroke-width="2" marker-end="url(#arrow-sky)"/>"""