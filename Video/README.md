# Demonstration Video - AUTOSAR HLD Intelligence Assistant

This directory contains the access information, agenda, and technical walkthrough documentation for the **AUTOSAR HLD Intelligence & Traceability Assistant** demonstration video.

---

## 1. Demonstration Video Links

- **Video Stream / Download:** `[Link to Video / Demonstration Recording]`
- **Format:** MP4 (1080p, 60fps)
- **Duration:** ~10-15 Minutes
- **Speaker:** GURU S (127003080)

*(Note: Per submission instructions, large video media files may be submitted via institutional cloud storage or bundled in the final submission package).*

---

## 2. Demonstration Agenda & Key Highlights

| Timestamp | Module Demonstrated | Key Engineering Feature |
| :---: | :--- | :--- |
| **00:00 - 02:00** | Introduction & Problem Context | Complexity of multi-release AUTOSAR HLD specifications (v1.0 vs v2.0) and limitations of standard LLM chatbots. |
| **02:00 - 04:30** | Document Ingestion & Governance | Ingesting `AUTOSAR_HLD_v1.0.pdf` and `v2.0.pdf`, setting document status (Draft/Approved), and viewing metadata. |
| **04:30 - 07:30** | Architecture-Aware Hybrid Retrieval | Demonstrating retrieval of `VehicleControl` dependencies and signal routing with Dense vs. Hybrid comparison. |
| **07:30 - 09:45** | Grounding Checker & Citation Verification | Inspecting cited chunks (`[Sec 4.1]`, `[Sec 5.2]`), provenance validation, and claim-level grounding scores. |
| **09:45 - 11:30** | Architecture Explorer & AST Validation | Running deterministic model validation, viewing component topology, port mappings, and version diffs. |
| **11:30 - 13:00** | Adversarial Abstention & Low-Confidence Engine | Submitting out-of-scope automotive queries; showing clean abstention and `review_required=True` behavior. |
| **13:00 - 14:30** | Engineering Reports & Compliance Export | Generating Markdown/PDF compliance summaries, traceability matrices, and audit logs. |
