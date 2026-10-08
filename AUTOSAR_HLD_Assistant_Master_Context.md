# AUTOSAR HLD DOCUMENT ANALYSIS ASSISTANT
## Master Project Context, Requirements, Architecture, Workflow, AI-Agent Instructions, and Phase-by-Phase Plan

**Project name:** AUTOSAR HLD Intelligence & Traceability Assistant  
**Reference case study:** Case Study 1 — AUTOSAR HLD Document Analysis Assistant  
**Domain:** Automotive Engineering + Generative AI + RAG + Document Intelligence  
**Primary UI:** Streamlit  
**Backend:** FastAPI  
**Vector retrieval:** FAISS or ChromaDB; FAISS is preferred for the student implementation because it matches existing experience  
**Embeddings:** BGE / E5 / Sentence Transformers  
**Document parser:** PyMuPDF first; OCR only when needed  
**Structured storage:** SQLite initially; PostgreSQL later if needed  
**Deployment:** Docker

---

# 1. IMPORTANT SOURCE / SCOPE RULE

The official Case Study 1 document is the authoritative source for the **business problem, objectives, scope, users, capabilities, inputs, outputs, risks, governance, metrics, and official implementation phases**.

The implementation details in this file that go beyond the case-study wording are **engineering recommendations**, not additional official requirements.

Do not invent AUTOSAR semantics, architecture relationships, validation rules, or document facts. Any architecture claim made by the application must be supported by the indexed HLD evidence.

The reference Connected Vehicle GenAI repository previously provided is a **reference implementation / learning reference**, not the specification for this HLD project. Reuse useful engineering patterns from it, but do not copy vehicle-telemetry-specific logic into the HLD project.

---

# 2. OFFICIAL CASE-STUDY PURPOSE

The official project overview is to automate the extraction, organization, search, and validation of architectural knowledge from large AUTOSAR High-Level Design documents.

HLD documents may describe:

- software components
- interfaces
- ports
- signals
- dependencies
- functional flows
- integration logic

The business problem is that engineers must manually interpret large and mostly unstructured HLD documents. This makes it difficult to find mismatches, missing dependencies, inconsistent terminology, and incomplete test coverage.

---

# 3. OFFICIAL PROJECT OBJECTIVES

The system should help to:

1. Reduce manual effort required to review HLD documents.
2. Create a structured and searchable repository of architecture knowledge.
3. Improve component, interface, signal, and dependency traceability.
4. Support design reviews, onboarding, impact analysis, and test planning.

---

# 4. OFFICIAL SCOPE

## 4.1 In scope

- PDF and supported document ingestion
- OCR for scanned pages
- Component extraction
- Interface extraction
- Port extraction
- Signal extraction
- Functional-flow extraction
- Natural-language search with citations
- Document comparison
- Inconsistency reporting
- Export of structured findings

## 4.2 Out of scope

- Automatic approval of architecture decisions
- Modification of source HLD documents without review
- Replacement of formal architecture governance

The system is an **engineering assistant**. It must not act as the final authority for architecture decisions.

---

# 5. PRIMARY USERS

The target users defined by the case study are:

- System architects
- AUTOSAR architects
- Software developers
- Integration engineers
- Test engineers
- Engineering managers

The interface should therefore present technical information clearly and traceably rather than behaving like a generic consumer chatbot.

---

# 6. INPUTS

Primary input knowledge sources:

- AUTOSAR HLD documents
- Interface specifications
- Architecture descriptions
- Component catalogues
- Revision history

The application must preserve document identity and version information.

Recommended metadata:

```json
{
  "project_id": "...",
  "document_id": "...",
  "document_name": "HLD_v2.3.pdf",
  "version": "v2.3",
  "source_type": "HLD",
  "approval_status": "approved",
  "page": 52,
  "section": "4.3.1",
  "ingestion_timestamp": "..."
}
```

The exact schema may be changed during implementation, but source/page/section/version traceability must be preserved.

---

# 7. EXPECTED OUTPUTS

The official case study expects outputs including:

- Component inventory
- Interface inventory
- Dependency maps
- Functional-flow summaries
- Searchable Q&A responses
- Potential inconsistency reports
- Structured exports for downstream use

The implementation may additionally expose ports and signals as structured entities because these are explicit target extraction types in the case study.

---

# 8. CORE PROJECT CONCEPT

The project is **NOT** a simple "chat with PDF" application.

The intended architecture is:

```text
Large AUTOSAR HLD documents
        ↓
Document extraction
        ↓
Architecture-aware structure
        ↓
Searchable knowledge
        ↓
Semantic retrieval / RAG
        ↓
AI-assisted analysis
        ↓
Citations + confidence/limitations
        ↓
Engineer review
        ↓
Structured findings / reports
```

The main value is **architecture knowledge + traceability**, not merely text generation.

---

# 9. END-TO-END SYSTEM WORKFLOW

```text
ENGINEER
   │
   ▼
STREAMLIT UI
   │
   ▼
FASTAPI SERVICE
   │
   ├── Document ingestion
   ├── Search
   ├── Analysis
   ├── Comparison
   ├── Review workflow
   └── Export
   │
   ▼
DOCUMENT VALIDATION
   │
   ▼
PDF / OCR EXTRACTION
   │
   ▼
SECTION + TABLE + METADATA PRESERVATION
   │
   ▼
ARCHITECTURE-AWARE CHUNKING
   │
   ▼
ENTITY / RELATIONSHIP EXTRACTION
   │
   ▼
BGE / E5 EMBEDDINGS
   │
   ▼
FAISS / CHROMA
   │
   ▼
USER QUERY
   │
   ▼
QUERY EMBEDDING + FILTERS
   │
   ▼
RELEVANT HLD EVIDENCE
   │
   ▼
RAG / AI AGENT
   │
   ├── Q&A
   ├── component report
   ├── interface analysis
   ├── dependency analysis
   ├── functional-flow summary
   ├── version comparison
   └── potential inconsistency / completeness analysis
   │
   ▼
CITATIONS + CONFIDENCE / LIMITATIONS
   │
   ▼
ENGINEER REVIEW
   │
   ├── Accept
   ├── Edit
   └── Reject
   │
   ▼
STRUCTURED STORAGE + EXPORT
```

---

# 10. RECOMMENDED SYSTEM ARCHITECTURE

```text
                           ┌────────────────────┐
                           │    Engineering     │
                           │       User         │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │     Streamlit      │
                           │        UI         │
                           └─────────┬──────────┘
                                     │ HTTP/REST
                                     ▼
                           ┌────────────────────┐
                           │      FastAPI       │
                           │ Application Layer  │
                           └─────────┬──────────┘
                                     │
             ┌───────────────────────┼────────────────────────┐
             │                       │                        │
             ▼                       ▼                        ▼
      ┌──────────────┐       ┌──────────────┐        ┌───────────────┐
      │  Ingestion   │       │  Retrieval   │        │   Workflow    │
      └──────┬───────┘       └──────┬───────┘        └──────┬────────┘
             │                      │                       │
             ▼                      ▼                       ▼
          PyMuPDF              FAISS / Chroma             SQLite
             │                      │
             ▼                      │
      Structure-aware              │
        chunking                   │
             │                     │
             ▼                     │
        BGE / E5                   │
             │                     │
             └──────────────┬──────┘
                            ▼
                    ┌───────────────┐
                    │   RAG / LLM   │
                    │  Orchestration│
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
             Q&A        Extraction    Analysis
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                    Citations / Evidence
                            │
                            ▼
                     Human Review
                            │
                            ▼
                     Export / Storage
```

---

# 11. DOCUMENT INGESTION PIPELINE

## Step 11.1 — Upload

Accept an approved HLD document.

## Step 11.2 — Validate

Validate:

- file type
- project context
- user access
- document version
- approval status

## Step 11.3 — Extract

Extract:

- text
- headings
- sections
- tables where possible
- page numbers
- metadata

Use OCR for scanned pages when necessary.

## Step 11.4 — Preserve source identity

Every processed chunk/entity must retain enough metadata to point back to the original document and page/section.

---

# 12. ARCHITECTURE ENTITY MODEL

The application should recognize these primary architecture entities:

```text
Component
Interface
Port
Signal
Functional Flow
Dependency
```

Recommended conceptual relationships:

```text
Component ──uses──────► Interface
Component ──has───────► Port
Port      ──carries───► Signal
Component ──depends───► Component
Component ──consumes──► Signal
Component ──produces──► Signal
```

These are implementation-level relationship labels. A relationship must be backed by HLD evidence rather than inferred simply because two entities occur near each other.

---

# 13. COMPONENT EXTRACTION

For every detected component, capture where possible:

- component name
- description
- input ports
- output ports
- interfaces
- consumed signals
- produced signals
- dependencies
- functional role
- source references

Example:

```json
{
  "entity_type": "component",
  "name": "VehicleControl",
  "description": "...",
  "ports": [],
  "interfaces": [],
  "signals": [],
  "dependencies": [],
  "sources": []
}
```

Do not fabricate fields that are not supported by the source document.

---

# 14. INTERFACE EXTRACTION

Capture where available:

- interface name
- interface description
- associated components
- ports
- signals
- source page/section

---

# 15. PORT EXTRACTION

Capture where available:

- port name
- component
- interface
- direction
- signals
- source page/section

Do not infer direction from a naming convention unless explicitly supported by the HLD.

---

# 16. SIGNAL EXTRACTION

Capture where available:

- signal name
- interface
- port
- source/destination component
- direction
- data type
- units
- description
- source page/section

Only populate attributes actually present in the source.

---

# 17. DEPENDENCY EXTRACTION

Potential dependency expressions may come from language such as:

- depends on
- uses
- requires
- consumes
- provides
- communicates with
- interfaces with

However, natural-language co-occurrence is not proof of dependency.

A dependency should be represented as:

```json
{
  "source": "ComponentA",
  "relation": "depends_on",
  "target": "ComponentB",
  "evidence": [
    {
      "document": "HLD_v2.pdf",
      "page": 52,
      "section": "4.3.1"
    }
  ]
}
```

---

# 18. CHUNKING STRATEGY

Avoid relying only on fixed-size token chunks.

Prefer structure-aware chunking:

```text
Document
  ↓
Section
  ↓
Subsection
  ↓
Architecture entity/context
  ↓
Chunk
```

Each chunk should contain:

```text
text
page
section
heading
entity type
entity name
component if known
version
source document
```

The goal is that retrieved chunks remain meaningful to an architecture question.

---

# 19. EMBEDDING STRATEGY

Recommended pilot:

```text
HLD chunk
   ↓
BGE or E5
   ↓
Embedding vector
```

Store vector + text + metadata.

For this student project, prefer a model that can run consistently in the available environment rather than choosing a model only because it is fashionable.

---

# 20. VECTOR DATABASE

Preferred:

**FAISS**

Alternative:

**ChromaDB**

The implementation must support metadata filtering at least conceptually for:

- project
- document
- version
- entity type
- component
- section

Do not mix unrelated project knowledge.

---

# 21. RAG WORKFLOW

For a natural-language architecture query:

```text
User question
   ↓
Query embedding
   ↓
Metadata filters
   ↓
Top-K semantic retrieval
   ↓
Evidence ranking
   ↓
Context assembly
   ↓
LLM
   ↓
Structured response
   ↓
Citation / evidence validation
```

The LLM must use retrieved evidence instead of inventing architectural facts.

If evidence is insufficient, the system should say so explicitly.

---

# 22. NATURAL-LANGUAGE QUERY TYPES

The assistant should support queries such as:

### Component

> What does component X do?

### Dependency

> What are the dependencies of component X?

### Interface

> Which interface does component X use?

### Signal

> Which signals does component X consume?

### Port

> What ports belong to component X?

### Flow

> Summarize the functional flow of subsystem X.

### Traceability

> Where is interface X defined?

### Impact analysis

> What components may be affected if interface X changes?

### Revision comparison

> What changed between HLD v1 and v2?

### Inconsistency

> Are there potentially conflicting definitions of signal X?

---

# 23. STRUCTURED LLM OUTPUT

The internal output should be structured rather than free-form whenever possible.

Recommended conceptual schema:

```json
{
  "query": "...",
  "answer": "...",
  "entities": [],
  "relationships": [],
  "findings": [],
  "citations": [],
  "confidence": "high",
  "limitations": [],
  "review_required": true
}
```

This is an implementation recommendation, not an official case-study schema.

---

# 24. CITATION REQUIREMENT

Every important architectural claim should be traceable to:

```text
Document
Page
Section
Relevant chunk/evidence
```

Example UI:

```text
Source: AUTOSAR_HLD_v2.3.pdf
Section: 4.3.1 VehicleControl
Page: 52
```

A citation is not merely decorative metadata. It is part of the trust model.

---

# 25. CONFIDENCE / LIMITATIONS

Do not present model probability as engineering truth.

Use application-level evidence indicators such as:

### HIGH
Strong direct evidence from approved sources.

### MEDIUM
Multiple pieces of evidence support the answer but some interpretation is involved.

### LOW
Evidence is incomplete or ambiguous.

When evidence is insufficient, explicitly state:

> Insufficient evidence in the indexed HLD documents.

Do not hallucinate.

---

# 26. COMPONENT REPORT

A major feature should be a component profile.

Example:

```text
COMPONENT: VehicleControl

Description
...

Interfaces
- VehicleStatusInterface
- ControlCommandInterface

Input Ports
- VehicleSpeed_In
- BrakeStatus_In

Output Ports
- ControlCommand_Out

Signals
- VehicleSpeed
- BrakeStatus

Dependencies
- VehicleStateProvider
- BrakeManager

Evidence
- HLD_v2.3.pdf, pages 52–61
```

The exact component names above are examples only. They must come from actual project data when used.

---

# 27. INTERFACE / DEPENDENCY MAPPING

The application should be able to produce a structured relationship view.

Conceptually:

```text
VehicleControl
    │
    ├── uses ──────► VehicleStatusInterface
    │
    ├── has ───────► VehicleSpeed_In
    │
    ├── consumes ──► VehicleSpeed
    │
    └── depends ───► VehicleStateProvider
```

Only relationships supported by source evidence should appear as confirmed.

Possible UI labels:

- Confirmed relationship
- Potential relationship
- Evidence insufficient

---

# 28. FUNCTIONAL-FLOW SUMMARIZATION

Where the document contains functional flow information, the system should summarize it in a structured sequence.

Example pattern:

```text
Input
 ↓
Processing component
 ↓
State / decision
 ↓
Control logic
 ↓
Output
```

The generated summary must retain citations.

---

# 29. REVISION COMPARISON

Input:

```text
HLD_v1.pdf
HLD_v2.pdf
```

Process:

```text
Extract v1
Extract v2
     ↓
Normalize entities
     ↓
Match entities
     ↓
Compare attributes
     ↓
Compare relationships
     ↓
Generate change report
```

Classify changes as:

```text
ADDED
REMOVED
MODIFIED
UNCHANGED
POTENTIAL CONFLICT
```

Example:

```text
Component changes
+ Component X
- Component Y

Interface changes
~ Interface Z

Signal changes
+ Signal A

Dependency changes
+ A → B
- C → D
```

Always show evidence for each material change.

---

# 30. INCONSISTENCY DETECTION

The objective is to identify **potential** problems for review, not to declare the architecture wrong.

Possible checks:

- conflicting descriptions
- conflicting relationship statements
- inconsistent signal associations
- duplicate/inconsistent naming
- possible missing dependency
- version mismatch
- contradictory architecture information

Correct output style:

> Potential inconsistency detected; engineer review required.

Incorrect output style:

> The architecture is definitely wrong.

---

# 31. COMPLETENESS CHECKING

Possible completeness checks include:

```text
Component exists but associated interface is not found
Interface referenced but no associated port is found
Port is declared but supporting signal information is absent
Dependency is mentioned but source/target relationship is unclear
```

These are signals for engineer review, not automatic architecture rejection.

---

# 32. AI AGENT DESIGN

If an agent is used, it should be an **orchestrator over deterministic tools**, not a single unrestricted LLM.

Recommended tools:

```text
search_hld()
search_entities()
get_component()
get_interface()
get_port()
get_signal()
get_dependencies()
get_source_evidence()
compare_versions()
check_consistency()
check_completeness()
generate_report()
create_finding()
export_report()
```

The agent should decide which tool(s) are needed for a user request and then synthesize the returned evidence.

---

# 33. AGENT QUERY WORKFLOW

For:

> What are the dependencies of VehicleControl?

Agent plan:

```text
1. Identify intent = dependency analysis
2. Identify current project and version
3. Search authorized HLD knowledge
4. Retrieve component/dependency evidence
5. Validate source/version metadata
6. Build relationship list
7. Generate concise answer
8. Attach citations
9. Provide confidence/limitations
10. Flag review only if the output is potentially consequential/ambiguous
```

For:

> Compare VehicleControl between v1 and v2

Agent plan:

```text
1. Locate VehicleControl in v1
2. Locate VehicleControl in v2
3. Compare fields
4. Compare relationships
5. Identify additions/removals/modifications
6. Retrieve source evidence for material changes
7. Generate structured change report
```

---

# 34. WHAT SHOULD BE DETERMINISTIC CODE VS AI

## Deterministic Python should handle

- file validation
- metadata validation
- access/project filtering
- document version filtering
- PDF extraction
- chunking
- embedding creation
- vector indexing/search
- exact entity matching
- deduplication
- structured storage
- deterministic comparison
- audit events
- export

## LLM / agent should handle

- natural-language interpretation
- query planning where useful
- evidence synthesis
- summarization
- explanation
- report generation
- resolving language variations when evidence exists

Never use the LLM as the sole source of truth for database state, file version, or deterministic comparison.

---

# 35. HUMAN-IN-THE-LOOP

Every potentially consequential finding should support:

```text
ACCEPT
EDIT
REJECT
```

Review screen should show:

```text
Finding
Evidence
Citation
Confidence / limitations
Reasoning summary where appropriate
Status
Reviewer
```

Approved artifacts may be stored for future traceability.

---

# 36. DATABASE / STORAGE MODEL

Pilot recommendation: SQLite.

Recommended logical tables:

```text
projects
documents
document_versions
entities
relationships
findings
reviews
approvals
audit_events
```

Example relationship record:

```json
{
  "source_entity_id": "...",
  "relationship": "uses",
  "target_entity_id": "...",
  "document_version": "v2.3",
  "evidence": []
}
```

PostgreSQL can replace SQLite later if required.

---

# 37. OPTIONAL GRAPH LAYER

Neo4j or another graph store is a scaling option for cross-artifact traceability.

Do not make Neo4j mandatory for the first working version unless it provides clear value.

For the student MVP, a relational representation of entities/relationships is sufficient.

---

# 38. SECURITY / GOVERNANCE

The reference case emphasizes:

- approved source material
- controlled access
- project isolation
- document versioning
- citations
- confidence/limitations
- review queues
- human approval
- auditability

Implementation rules:

```text
Never mix project collections.
Never silently use an obsolete document version.
Never use unapproved source documents.
Never fabricate citations.
Never modify the source HLD automatically.
Never present an AI finding as formal architecture approval.
```

---

# 39. REFERENCE REPOSITORY RELATIONSHIP

The previously provided Connected Vehicle GenAI reference repository already demonstrates useful concepts:

```text
Python processing
RAG
LLM integration
structured outputs
retrieval
evaluation
Streamlit-style workflows
human review concepts
automotive engineering context
```

However, do NOT reuse these vehicle-specific modules:

```text
telemetry cleaning
trip segmentation
GPS dejump
DTC event windows
speed/RPM/SOC analysis
vehicle event summaries
```

The HLD project replaces those with:

```text
PDF ingestion
section/heading extraction
table handling
architecture entity extraction
architecture-aware chunking
semantic retrieval
component/interface/port/signal relationships
revision comparison
inconsistency/completeness analysis
```

The previous reference repo's lightweight lexical TF/cosine retrieval is also not the target retrieval approach for this project. The HLD reference solution recommends BGE/E5 embeddings with FAISS/ChromaDB for the pilot.

---

# 40. OFFICIAL IMPLEMENTATION PHASES

The official HLD case study defines four phases:

1. Discovery
2. Pilot
3. Validation
4. Scale

The following subphases translate those official phases into a practical student implementation plan.

---

# 41. PHASE 0 — PROJECT BASELINE / SCOPE LOCK

This is a practical pre-phase before the official Discovery phase.

## Objective

Prevent scope explosion and make the project buildable.

## Tasks

- Confirm project name.
- Confirm official Case Study 1 requirements.
- Create repository structure.
- Define MVP.
- Define supported file types.
- Define entity taxonomy.
- Define output schemas.
- Define technology stack.
- Define acceptance criteria.

## MVP to lock

```text
PDF ingestion
Section-aware chunking
BGE/E5 embeddings
FAISS retrieval
RAG Q&A
Citations
Component/interface/port/signal extraction
Dependency analysis
Basic inconsistency detection
Streamlit UI
Evaluation
```

## Do NOT start with

```text
Kubernetes
Neo4j
enterprise IAM
complex OCR
full graph platform
advanced integrations
```

## Exit criteria

A short design document exists and the project has a fixed MVP.

---

# 42. PHASE 1 — DISCOVERY

**Official phase:** Discovery

## Goal

Understand the HLD documents, define the architecture taxonomy, questions, and success metrics before coding the complete system.

## 42.1 Collect representative HLD data

Prepare a small but meaningful dataset.

For example:

```text
HLD_v1.pdf
HLD_v2.pdf
Interface_Spec.pdf
Component_Catalogue.pdf
```

Only use data that is authorized for the project.

## 42.2 Define taxonomy

Start with:

```text
Component
Interface
Port
Signal
Flow
Dependency
```

Define how each entity is represented.

## 42.3 Define question set

Create at least 20–30 representative questions covering:

- component lookup
- interface lookup
- port lookup
- signal lookup
- dependency lookup
- source citation
- flow explanation
- comparison
- inconsistency

## 42.4 Define gold answers

For the evaluation set, record expected:

- entities
- relevant source pages/sections
- expected relationship where applicable

## 42.5 Define success metrics

Use:

- extraction precision/recall/F1
- retrieval Precision@K / Recall@K / MRR
- citation correctness
- answer groundedness
- confirmed issue discovery
- review-time reduction where measurable

## Exit criteria

```text
✓ representative documents selected
✓ taxonomy defined
✓ benchmark queries defined
✓ expected evidence recorded
✓ metrics defined
```

---

# 43. PHASE 2 — PILOT / INGESTION FOUNDATION

**Official phase:** Pilot

## Goal

Create a working document-to-searchable-knowledge pipeline before adding advanced analysis.

## 43.1 Build PDF ingestion

Implement:

```text
upload
→ validation
→ PyMuPDF extraction
→ page-level records
```

## 43.2 Preserve headings and sections

Build a parser that keeps:

```text
page
heading
section
paragraph/table text
```

## 43.3 Build architecture-aware chunking

Produce chunks with metadata.

## 43.4 Generate embeddings

Use BGE/E5/Sentence Transformers.

## 43.5 Build FAISS index

Store embeddings and metadata.

## 43.6 Implement retrieval API

Example endpoint concepts:

```text
POST /documents/upload
POST /documents/index
POST /search
GET /documents/{id}
GET /documents/{id}/pages/{page}
```

Exact routes are implementation decisions.

## Exit criteria

You must be able to:

```text
Upload HLD
→ extract
→ chunk
→ embed
→ index
→ query
→ retrieve relevant source pages/sections
```

No need for sophisticated agent behavior yet.

---

# 44. PHASE 3 — PILOT / RAG Q&A

Still part of the official Pilot phase.

## Goal

Deliver cited natural-language HLD search.

## Tasks

1. Query embedding.
2. Top-K retrieval.
3. Metadata filtering.
4. Context assembly.
5. LLM prompt.
6. Structured response.
7. Citations.
8. Confidence/limitations.

## Required behavior

If retrieval is poor:

```text
Do not hallucinate.
```

Respond with an evidence limitation.

## Example acceptance test

Input:

> What interfaces are used by component X?

Expected behavior:

- relevant chunks retrieved
- answer cites source pages/sections
- unsupported interfaces are not invented

## Exit criteria

A user can ask architecture questions and receive evidence-backed answers.

---

# 45. PHASE 4 — ARCHITECTURE EXTRACTION

This is a practical expansion of the Pilot phase.

## Goal

Turn HLD content into structured architecture knowledge.

## Tasks

Implement extraction for:

```text
components
interfaces
ports
signals
flows
relationships
```

## Recommended pipeline

```text
Retrieved / parsed HLD context
        ↓
LLM structured extraction
        ↓
Schema validation
        ↓
Deterministic normalization / deduplication
        ↓
Structured storage
```

## Important

LLM extraction should be validated against schemas.

Relationships must retain evidence.

## Exit criteria

Given an HLD, the system can create a structured inventory of the major architecture entity types and their source locations.

---

# 46. PHASE 5 — ARCHITECTURE EXPLORER

Practical expansion of Pilot.

## Goal

Allow an engineer to inspect architecture knowledge without reading the whole PDF.

## Features

```text
Component search
Interface search
Port search
Signal search
Dependency search
Source evidence viewer
```

## Main output

A component report and relationship view.

## Exit criteria

An engineer can search an entity and see its known attributes, relationships, and citations.

---

# 47. PHASE 6 — ANALYSIS: INCONSISTENCY + COMPLETENESS

Practical expansion of Pilot / beginning of Validation.

## Goal

Identify candidate architecture issues for human review.

## Tasks

Implement simple deterministic/AI-assisted checks:

- duplicate names
- conflicting descriptions
- conflicting relationship statements
- missing associated entity
- version-specific relationship changes

## Output

```text
Finding ID
Finding type
Entity
Description
Evidence
Confidence
Review status
```

## Important

Use the phrase:

> Potential inconsistency / potential missing relationship

not:

> Architecture is wrong.

## Exit criteria

The system can produce reviewable candidate findings with evidence.

---

# 48. PHASE 7 — REVISION COMPARISON

Practical expansion of Pilot / Validation.

## Goal

Compare HLD versions.

## Tasks

- index v1 and v2 separately
- extract entities from both
- normalize names
- match entities
- compare attributes
- compare relationships
- create change report

## Exit criteria

Given two HLD versions, the system produces a traceable list of added, removed, and modified architecture items.

---

# 49. PHASE 8 — AGENT ORCHESTRATION

This is where the AI agent becomes useful.

## Goal

Allow the user to issue natural-language tasks instead of navigating every feature manually.

## Agent capabilities

```text
architecture question answering
component lookup
relationship lookup
source evidence lookup
comparison
inconsistency analysis
completeness analysis
report generation
```

## Agent rules

- Never invent tool results.
- Never bypass retrieval for architecture facts.
- Never mix document versions.
- Always preserve evidence.
- Prefer deterministic tools for deterministic operations.
- Escalate uncertain findings to human review.

## Exit criteria

A natural-language user request can be decomposed into tool calls and produce a traceable answer.

---

# 50. PHASE 9 — VALIDATION

**Official phase:** Validation

## Goal

Benchmark the extraction and Q&A behavior against a gold-standard set.

## 50.1 Retrieval evaluation

Measure:

```text
Precision@K
Recall@K
MRR
```

## 50.2 Extraction evaluation

For each entity type:

```text
Component
Interface
Port
Signal
```

measure:

```text
Precision
Recall
F1
```

## 50.3 Answer evaluation

Measure:

- answer correctness
- groundedness
- citation correctness
- unsupported claim rate

## 50.4 Issue detection evaluation

Where possible, have an engineer manually confirm findings.

Measure:

```text
confirmed findings
false positives
```

## 50.5 Efficiency evaluation

If feasible, compare:

```text
manual review time
vs
AI-assisted review time
```

## Exit criteria

The project must have a reproducible evaluation report, not just screenshots of a working chatbot.

---

# 51. PHASE 10 — HARDENING / REVIEW WORKFLOW

## Goal

Make outputs safer and suitable for demonstration as an engineering assistant.

## Tasks

- review queue
- Accept / Edit / Reject
- version labels
- source approval status
- audit logging
- evidence display
- project isolation
- structured exports

## Exit criteria

A reviewer can inspect, approve, edit, or reject AI-generated findings and the decision is stored.

---

# 52. PHASE 11 — DEPLOYMENT

## Goal

Package the project cleanly.

## Tasks

- requirements.txt
- environment configuration
- Dockerfile
- docker-compose.yml if appropriate
- persistent vector index
- persistent database
- README
- setup instructions
- sample data instructions

## Exit criteria

A clean environment can reproduce the application from the repository.

---

# 53. PHASE 12 — SCALE / OPTIONAL FEATURES

**Official phase:** Scale

Only after the MVP is stable consider:

- PostgreSQL
- Neo4j
- advanced graph relationships
- role-based access
- project isolation enforcement
- additional document formats
- advanced OCR
- enterprise integrations
- advanced dashboards
- toolchain integrations

Do not let these delay the MVP.

---

# 54. RECOMMENDED FINAL MVP

The final student-grade MVP should provide:

```text
1. HLD PDF upload
2. Document/version validation
3. PDF text + metadata extraction
4. Section-aware chunking
5. BGE/E5 embeddings
6. FAISS semantic retrieval
7. RAG Q&A
8. Page/section citations
9. Component extraction
10. Interface extraction
11. Port extraction
12. Signal extraction
13. Dependency mapping
14. Component reports
15. Basic inconsistency detection
16. Basic completeness checking
17. v1/v2 revision comparison
18. Human review
19. Structured export
20. Evaluation report
21. Streamlit UI
22. FastAPI backend
23. Docker packaging
```

---

# 55. OPTIONAL FEATURES ONLY AFTER MVP

```text
OCR pipeline
Neo4j
PostgreSQL
RBAC
advanced graph visualization
advanced impact analysis
enterprise portal
multi-project administration
advanced monitoring
```

---

# 56. RECOMMENDED TEST CASES

Create tests for:

## Ingestion

```text
valid PDF
invalid file
empty PDF
scanned PDF if OCR is supported
```

## Retrieval

```text
component query
interface query
signal query
dependency query
version-filtered query
```

## Extraction

```text
component extraction
interface extraction
port extraction
signal extraction
relationship extraction
```

## Analysis

```text
potential conflict
missing relationship
version change
```

## RAG

```text
supported answer
unsupported question
citation presence
insufficient evidence
```

## UI/API

```text
upload
index
query
comparison
review
export
```

---

# 57. ACCEPTANCE CRITERIA FOR EACH MAJOR FEATURE

## Ingestion

Given a valid HLD PDF, the system creates page-aware parsed content.

## Retrieval

Given a benchmark query, relevant evidence should be retrieved.

## Q&A

Answers must cite source pages/sections and avoid unsupported claims.

## Entity extraction

Entities must include source evidence.

## Relationship extraction

Relationships must be evidence-backed.

## Comparison

Changes must identify source versions.

## Inconsistency detection

Findings must be marked as potential issues and sent through review.

## Human review

Reviewer can Accept/Edit/Reject.

## Export

Approved findings can be exported in structured form.

---

# 58. AGENT NON-NEGOTIABLE RULES

```text
RULE 1:
Do not turn this into a generic PDF chatbot.

RULE 2:
Preserve page/section/version metadata from ingestion to final answer.

RULE 3:
Do not invent AUTOSAR relationships.

RULE 4:
Use retrieval evidence for architecture claims.

RULE 5:
Use deterministic code for deterministic comparisons/validation.

RULE 6:
Use the LLM for interpretation, synthesis, and explanation.

RULE 7:
Treat uncertain findings as review candidates.

RULE 8:
Never automatically approve architecture decisions.

RULE 9:
Never modify the original HLD automatically.

RULE 10:
Never silently mix document versions.

RULE 11:
Never fabricate citations.

RULE 12:
Keep project data isolated.

RULE 13:
Do not add large infrastructure components before the MVP works.

RULE 14:
Every phase must have working outputs and tests before moving on.

RULE 15:
Clearly distinguish official requirements from implementation choices.
```

---

# 59. RECOMMENDED IMPLEMENTATION ORDER

Build in this exact order:

```text
STEP 1
Repository skeleton

STEP 2
Configuration + environment management

STEP 3
PDF ingestion

STEP 4
Page/section/metadata preservation

STEP 5
HLD-aware chunker

STEP 6
Embedding model integration

STEP 7
FAISS indexing

STEP 8
Retriever

STEP 9
RAG Q&A

STEP 10
Citation handling

STEP 11
Structured architecture entity extraction

STEP 12
Entity normalization + storage

STEP 13
Dependency/interface analysis

STEP 14
Component explorer

STEP 15
Inconsistency/completeness checks

STEP 16
Version comparison

STEP 17
Human review workflow

STEP 18
Agent orchestration

STEP 19
Evaluation suite

STEP 20
Streamlit polish

STEP 21
Docker

STEP 22
README + demo + final cleanup
```

Do not start Step 18 before the underlying tools work independently.

---

# 60. SUGGESTED REPOSITORY STRUCTURE

```text
autosar_hld_assistant/
│
├── app/
│   ├── main.py
│   └── settings.py
│
├── api/
│   ├── documents.py
│   ├── search.py
│   ├── analysis.py
│   ├── comparison.py
│   ├── review.py
│   └── export.py
│
├── ingestion/
│   ├── pdf_parser.py
│   ├── ocr.py
│   └── metadata.py
│
├── chunking/
│   └── hld_chunker.py
│
├── embeddings/
│   └── embedder.py
│
├── retrieval/
│   ├── index.py
│   └── retriever.py
│
├── extraction/
│   ├── components.py
│   ├── interfaces.py
│   ├── ports.py
│   ├── signals.py
│   ├── flows.py
│   └── relationships.py
│
├── rag/
│   ├── prompts.py
│   ├── context.py
│   ├── generator.py
│   └── citations.py
│
├── analysis/
│   ├── consistency.py
│   ├── completeness.py
│   └── comparison.py
│
├── agent/
│   ├── agent.py
│   ├── planner.py
│   └── tools.py
│
├── db/
│   ├── models.py
│   └── repository.py
│
├── frontend/
│   └── streamlit_app.py
│
├── evaluation/
│   ├── retrieval_eval.py
│   ├── extraction_eval.py
│   ├── groundedness_eval.py
│   └── benchmark.json
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── indexes/
│
├── exports/
├── tests/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

This structure is a recommendation. Keep it simple if a smaller structure is more maintainable.

---

# 61. API CONCEPTS

Suggested API capabilities:

```text
POST /documents/upload
POST /documents/{id}/index
GET  /documents
GET  /documents/{id}
POST /search
POST /ask
GET  /components/{name}
GET  /interfaces/{name}
GET  /signals/{name}
GET  /dependencies/{name}
POST /compare
POST /analyze/consistency
POST /analyze/completeness
POST /findings/{id}/review
POST /export
```

These endpoint names are implementation suggestions, not official requirements.

---

# 62. STREAMLIT UI CONCEPT

Recommended sections:

```text
Dashboard
Documents
Architecture Explorer
AI Assistant
Version Comparison
Findings / Review
Exports
Evaluation
```

## Dashboard

Show:

```text
Current project
Current version
Documents indexed
Components
Interfaces
Ports
Signals
Open findings
```

## Documents

Upload and index HLD files.

## Architecture Explorer

Search entities and inspect evidence.

## AI Assistant

Natural-language architecture questions.

## Version Comparison

Compare two document versions.

## Findings / Review

Accept/Edit/Reject findings.

## Exports

JSON/CSV/report output.

## Evaluation

Show benchmark metrics.

---

# 63. EXAMPLE END-TO-END DEMO

Use a real approved sample HLD.

### Demo sequence

1. Upload HLD v1.
2. Upload HLD v2.
3. Index both.
4. Open Architecture Explorer.
5. Search a component.
6. Display component report.
7. Ask a dependency question.
8. Show retrieved evidence.
9. Show cited LLM answer.
10. Compare component between v1 and v2.
11. Show added/removed/modified relationships.
12. Run potential inconsistency analysis.
13. Display finding with evidence.
14. Accept/Edit/Reject.
15. Export structured report.
16. Display evaluation metrics.

This demonstrates the complete engineering workflow rather than only the chatbot.

---

# 64. WHAT NOT TO CLAIM IN README / RESUME

Do not claim:

- production deployment unless actually deployed
- complete AUTOSAR standard understanding
- autonomous architecture validation
- perfect hallucination prevention
- 100% extraction accuracy without evaluation
- enterprise-scale platform if only a student prototype exists
- full formal verification of architecture

Use accurate wording such as:

> AI-assisted AUTOSAR HLD document analysis prototype

> Source-grounded architecture Q&A with page/section citations

> Automated extraction of architecture entities with reviewable findings

> Prototype revision comparison and potential inconsistency detection

---

# 65. SUGGESTED RESUME DESCRIPTION

### Project title

**AUTOSAR HLD Intelligence & Traceability Assistant**

### Bullet 1

Built an AI-powered AUTOSAR HLD analysis assistant using Python, FastAPI, Streamlit, BGE/E5 embeddings, FAISS, and RAG for source-grounded architecture search and analysis.

### Bullet 2

Implemented structured extraction and traceability for components, interfaces, ports, signals, and dependencies with page/section citations and human-reviewable findings.

### Bullet 3

Added HLD revision comparison, potential inconsistency detection, and retrieval/entity-evaluation workflows to support architecture review and impact analysis.

These bullets describe the intended implementation. Only keep features that are actually implemented and tested.

---

# 66. FINAL PROJECT STORY

The project should tell this story:

```text
Problem:
Large AUTOSAR HLDs are difficult to manually search and trace.

Solution:
Convert approved HLDs into structured, searchable architecture knowledge.

AI:
Use embeddings + RAG + LLM/agent for natural-language analysis.

Engineering control:
Keep evidence, source citations, versions, deterministic checks,
and human review in the loop.

Output:
Faster architecture understanding, structured traceability,
potential issue discovery, and reusable review artifacts.
```

---

# 67. THE FINAL ONE-LINE DESCRIPTION

> **An evidence-grounded AI assistant that converts AUTOSAR HLD documents into searchable and traceable architecture knowledge, enabling natural-language analysis, entity/dependency extraction, revision comparison, and reviewable inconsistency findings.**

---

# 68. DEFINITION OF DONE

The project is considered complete when all of the following are true:

```text
✓ Official Case Study 1 scope is implemented or intentionally marked as later scope.
✓ HLD PDFs can be ingested.
✓ Page/section/version metadata is preserved.
✓ Embeddings are generated.
✓ FAISS/Chroma retrieval works.
✓ RAG Q&A works.
✓ Answers contain valid source citations.
✓ Unsupported questions do not cause hallucinated architecture claims.
✓ Components/interfaces/ports/signals can be extracted.
✓ Relationships carry evidence.
✓ Component reports work.
✓ Version comparison works at least for the supported entity types.
✓ Potential inconsistencies can be generated.
✓ Findings can be reviewed.
✓ Results can be exported.
✓ Evaluation is reproducible.
✓ Tests pass.
✓ The project runs from a clean setup.
✓ README explains setup, architecture, scope, limitations, and evaluation.
✓ No unsupported claims are made about production readiness or formal architecture approval.
```

---

# 69. OFFICIAL CASE-STUDY ALIGNMENT SUMMARY

The implementation must remain aligned with these official themes:

```text
HLD document ingestion
Architecture entity extraction
Architecture search
Interface/dependency mapping
Cited Q&A
Revision comparison
Potential inconsistency/completeness analysis
Structured findings
Human review
Traceability
Approved sources
Version control
Project isolation
```

The official case study also recommends a secure/private AI architecture using an approved LLM, local vector storage, Python services, and a simple engineering web UI.

---

# 70. AGENT INSTRUCTION AT THE END OF THIS FILE

When continuing development:

1. Read this file before making architecture changes.
2. Check which implementation phase is currently complete.
3. Do not skip required acceptance tests.
4. Inspect existing files before deleting or replacing them.
5. Preserve working components from earlier phases.
6. Do not silently expand scope.
7. When a requirement is ambiguous, implement the smallest defensible interpretation and document it.
8. When a feature cannot be truthfully implemented from the available HLD data, mark it as unsupported instead of fabricating results.
9. Run targeted tests after every major change.
10. At the end of each phase, report:
   - what was implemented
   - files changed
   - tests run
   - test results
   - known limitations
   - next phase

---

# PROJECT STATUS TEMPLATE

Use this section to track the live implementation status.

```text
Phase 0 — Scope Lock:          [ ]
Phase 1 — Discovery:           [ ]
Phase 2 — Ingestion:           [ ]
Phase 3 — RAG Q&A:             [ ]
Phase 4 — Entity Extraction:   [ ]
Phase 5 — Architecture Explorer:[ ]
Phase 6 — Analysis:            [ ]
Phase 7 — Comparison:          [ ]
Phase 8 — Agent:               [ ]
Phase 9 — Validation:          [ ]
Phase 10 — Review/Security:    [ ]
Phase 11 — Deployment:         [ ]
Phase 12 — Scale/Optional:     [ ]
```

For every completed phase, record evidence such as test output, screenshots, benchmark results, or demo behavior.

---

# END OF MASTER CONTEXT
