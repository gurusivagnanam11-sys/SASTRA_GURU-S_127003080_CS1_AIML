# Part 1: Header and Defs
def get_header_and_defs():
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 1620" width="2400" height="1620">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap');
      text { font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      .code-text { font-family: 'JetBrains Mono', Consolas, monospace; }
    </style>
    <filter id="card-shadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.06"/>
      <feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#0f172a" flood-opacity="0.04"/>
    </filter>
    <marker id="arrow-indigo" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#4f46e5"/></marker>
    <marker id="arrow-emerald" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#059669"/></marker>
    <marker id="arrow-sky" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#0284c7"/></marker>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#9333ea"/></marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#2563eb"/></marker>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#ea580c"/></marker>
    <linearGradient id="header-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0f172a"/><stop offset="60%" stop-color="#1e293b"/><stop offset="100%" stop-color="#334155"/>
    </linearGradient>
    <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#d97706"/><stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><circle cx="20" cy="20" r="1" fill="#E2E8F0"/></pattern>
  </defs>
  <rect width="2400" height="1620" fill="#F8FAFC"/><rect width="2400" height="1620" fill="url(#grid)" opacity="0.6"/>
  <g transform="translate(60, 40)">
    <rect width="2280" height="96" rx="16" fill="url(#header-grad)" filter="url(#card-shadow)"/>
    <rect x="0" y="90" width="2280" height="6" rx="3" fill="url(#gold-grad)"/>
    <text x="36" y="44" font-size="24" font-weight="800" fill="#F8FAFC" letter-spacing="-0.02em">AUTOSAR HLD Intelligence &amp; Traceability Assistant — End-to-End RAG Architecture</text>
    <text x="36" y="72" font-size="14" font-weight="500" fill="#94A3B8">Production Workflow: Multi-Version Ingestion, Hybrid Retrieval Fusion, Structured LLM Generation, Deterministic Grounding &amp; Architecture Validation</text>
    <g transform="translate(1420, 26)">
      <rect x="0" y="0" width="820" height="44" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <rect x="16" y="14" width="16" height="16" rx="4" fill="#4F46E5"/><text x="38" y="27" font-size="11" font-weight="600" fill="#E2E8F0">1. Ingestion</text>
      <rect x="120" y="14" width="16" height="16" rx="4" fill="#059669"/><text x="142" y="27" font-size="11" font-weight="600" fill="#E2E8F0">2. Retrieval</text>
      <rect x="224" y="14" width="16" height="16" rx="4" fill="#0284C7"/><text x="246" y="27" font-size="11" font-weight="600" fill="#E2E8F0">3. Context</text>
      <rect x="316" y="14" width="16" height="16" rx="4" fill="#9333EA"/><text x="338" y="27" font-size="11" font-weight="600" fill="#E2E8F0">4. Inference</text>
      <rect x="416" y="14" width="16" height="16" rx="4" fill="#D97706"/><text x="438" y="27" font-size="11" font-weight="600" fill="#E2E8F0">5. Validation</text>
      <rect x="520" y="14" width="16" height="16" rx="4" fill="#2563EB"/><text x="542" y="27" font-size="11" font-weight="600" fill="#E2E8F0">6. Output</text>
      <rect x="610" y="14" width="16" height="16" rx="4" fill="#EA580C"/><text x="632" y="27" font-size="11" font-weight="600" fill="#E2E8F0">Dedicated Module</text>
      <circle cx="760" cy="22" r="6" fill="#F59E0B"/><text x="774" y="26" font-size="11" font-weight="600" fill="#FDE68A">Offline-1st</text>
    </g>
  </g>"""