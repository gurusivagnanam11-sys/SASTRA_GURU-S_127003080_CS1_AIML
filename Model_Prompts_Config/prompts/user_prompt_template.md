# User Prompt Template Specification — AUTOSAR HLD Engineering Analysis Assistant

## 1. Overview & Architectural Role

The user prompt template assembles the incoming natural language query with the retrieved, structured High-Level Design (HLD) evidence context before dispatching to the LLM.

- **Source Module**: [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py)
- **Builder Function**: `build_user_prompt(question: str, context_str: str) -> str`
- **Context Provider**: [`rag/context_builder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/context_builder.py) (`ContextBuilder.format_context_for_prompt()`)
- **Invocation**: Called in [`rag/pipeline.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/pipeline.py) line 249 during `RAGPipeline.ask()`

---

## 2. Production User Prompt Template

The exact string template implemented in [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py) is:

```text
USER QUESTION:
{question}

RETRIEVED HLD EVIDENCE CONTEXT:
{context_str}

Please analyze the evidence above and provide your response as a valid JSON object matching the requested schema.
When answering queries comparing or asking about multiple versions (e.g., v1.0 and v2.0), analyze each version's evidence independently. State the specific value/type for each version and generate separate claims citing the corresponding chunk for that version.
```

---

## 3. Dynamic Fields & Parameter Injection

The user prompt contains two dynamic placeholders injected at runtime:

### 3.1. `{{ question }}`
The validated natural language query submitted by the user through the Streamlit UI or the FastAPI REST API (`POST /query`).
- **Input Type**: `str`
- **Validation**: Enforced by `APIQueryRequest` in [`app/main.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/main.py):
  - Cannot be empty or whitespace-only (triggers 400 or immediate fallback response).
  - Maximum length bound: 5,000 characters.

### 3.2. `{{ context_str }}`
The formatted string of top-K retrieved evidence chunks produced by [`rag/context_builder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/context_builder.py).

Each retrieved chunk is formatted with a standardized metadata header line:
```text
--- CHUNK: {chunk_id} | DOC: {document_id} | VER: {version} | PAGE: {page_number} | SEC: {section} | TYPE: {chunk_type} ---
{text}
```

#### Example Formatted Context Structure:
```text
--- CHUNK: autosar_hld__v1.0_p06_c24 | DOC: autosar_hld_v1.0 | VER: 1.0 | PAGE: 6 | SEC: 5.1 | TYPE: signal ---
Section 5.1 Signal Matrix:
VehicleSpeed: float32, km/h, Source: VehicleControl, Destination: DashDisplay, Interface: VehicleDataInterface.
EngineRPM: uint16, rpm, Source: EngineControl, Destination: DashDisplay, Interface: VehicleDataInterface.

--- CHUNK: autosar_hld__v2.0_p06_c28 | DOC: autosar_hld_v2.0 | VER: 2.0 | PAGE: 6 | SEC: 5.1 | TYPE: signal ---
Section 5.1 Signal Matrix (Revision 2.0):
VehicleSpeed: float64, km/h, Source: VehicleControl, Destination: DashDisplay, Interface: VehicleDataInterface.
EngineRPM: uint16, rpm, Source: EngineControl, Destination: DashDisplay, Interface: VehicleDataInterface.
BatteryStateOfCharge: uint8, %, Source: BatteryManagement, Destination: PowertrainControl, Interface: EnergyDataInterface.
```

---

## 4. Context Assembly Pipeline

The sequence for building `context_str` before user prompt creation:

1. **Retrieval**: `HybridRetriever.retrieve()` returns top-K `(score, metadata_dict)` tuples.
2. **Context Model Transformation**: [`rag/context_builder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/context_builder.py) converts raw metadata into a list of `ContextChunk` objects:
   ```python
   context_chunks: List[ContextChunk] = self.context_builder.build_context(retrieved_raw)
   ```
3. **Deduplication & Filtering**: Chunks with duplicate `chunk_id` values are discarded.
4. **Header Formatting**: `format_context_for_prompt(context_chunks)` applies the standard header format for each chunk.
5. **Cross-Version Completeness Check**: If the query is detected as a cross-version comparison (e.g. `QueryType.REVISION_QUERY`), the pipeline verifies that both `v1.0` and `v2.0` chunks are present. If either is missing, the pipeline abstains before LLM invocation, preventing hallucinated comparative claims.

---

## 5. Maintenance & Safe Update Protocol

1. **Modifying the Template**: Edit `build_user_prompt` in [`rag/prompts.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/prompts.py).
2. **Modifying Chunk Headers**: Edit `format_context_for_prompt` in [`rag/context_builder.py`](file:///C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/rag/context_builder.py). Note that changing header formats requires updating regex pattern matching in downstream tests.
3. **Verification**:
   ```powershell
   & .venv/Scripts/python.exe -m pytest tests/test_rag.py::test_context_construction tests/test_vehiclespeed_cross_version.py -v
   ```