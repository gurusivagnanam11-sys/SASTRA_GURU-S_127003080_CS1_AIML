# Phase 8: Engineering Reports & Governance

## Overview
Phase 8 introduces enterprise-grade reporting, source governance, and human-in-the-loop review workflows. These features elevate the system from an analytical tool to a comprehensive traceability and compliance support platform.

## Key Features

### 1. Document Source Governance
- **Status Tracking**: Tracks `APPROVED`, `DRAFT`, and `ARCHIVED` statuses for ingested documents.
- **Active Version Resolution**: By default, the system resolves queries and validations against the highest version `APPROVED` specification, ignoring `DRAFT` or `ARCHIVED` documents.
- **Governance Audit Trail**: All status changes are logged with timestamps, users, and reasons in `governance_audit`.

### 2. Engineering Review Workflow
- **Enhanced Review Form**: Captures structured decisions (`ENGINEER_APPROVED`, `ENGINEER_CORRECTED`, `ENGINEER_REJECTED`) for specific reports and analysis findings.
- **Traceability**: Review records are tied back to specific entities, component names, and document versions.

### 3. Comprehensive Structured Reports
The application now exposes REST endpoints and UI tabs for generating standardized markdown and JSON reports:
- **Component Report**: Deep dive into a specific Software Component, its interfaces, dependencies, and impacted flows.
- **Validation Report**: Full architecture validation summary (Phase 7 results).
- **Revision Report**: Deterministic structural diff between two specification versions.
- **Impact Report**: Comprehensive change propagation analysis.

### 4. User Interface
- A new **Engineering Reports** tab in the Streamlit UI.
- Direct downloads of reports in `.md` (Markdown) and `.json` formats.
- Real-time interaction with the Governance API.

## Implementation Details
- **Pydantic Models**: Centralized in `reports/models.py`.
- **Generation Logic**: `reports/generator.py` acts as a facade orchestrating Phase 3 (Extraction) and Phase 7 (Validation) modules.
- **Database**: Two new SQLite models (`EngineeringReviewRecord`, `GovernanceRecord`) added to `db/models.py` without breaking existing schemas.
- **API**: `/reports/*` and `/governance/*` endpoints added to `app/main.py`.

## Validation
- 11 new tests added covering generation, API endpoints, governance changes, and audit trailing.
- Maintained 100% backwards compatibility (164+ tests passing).
- Zero hallucination via strictly deterministic extraction data pipelines.

**Note**: This tool provides decision support. It does not replace formal ISO 26262 functional safety audits or enterprise compliance processes.
