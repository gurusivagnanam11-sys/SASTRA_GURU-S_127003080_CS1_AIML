"""Structured export utilities for engineering reports.

Supports JSON, Markdown, and CSV export formats.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from reports.models import (
    ComponentReport,
    ImpactReport,
    RevisionReport,
    ValidationReport,
)


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ==============================
# JSON Export
# ==============================


def export_report_json(report: Any) -> str:
    """Export any Pydantic report model to formatted JSON."""
    if hasattr(report, "model_dump"):
        data = report.model_dump()
    else:
        data = dict(report)
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# ==============================
# Markdown Export
# ==============================


def export_component_report_md(report: ComponentReport) -> str:
    """Export ComponentReport to engineering Markdown."""
    lines = [
        "# Component Engineering Report",
        "",
        f"- **Component:** {report.component_name}",
        f"- **Generated:** {report.generated_at}",
        f"- **Source Document:** {report.source_document}",
        f"- **Source Version:** {report.source_version}",
        f"- **Source Status:** {report.source_status}",
        "",
        "## Description",
        "",
        report.description,
        "",
    ]

    # Interfaces
    lines.extend(["## Interfaces", ""])
    if report.interfaces:
        for iface in report.interfaces:
            lines.append(f"- {iface}")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Ports
    lines.extend(["## Ports", ""])
    if report.ports:
        lines.append("| Port | Direction | Interface | Signals |")
        lines.append("|---|---|---|---|")
        for p in report.ports:
            sigs = ", ".join(p.get("signals", []))
            lines.append(f"| {p['name']} | {p['direction']} | {p['interface']} | {sigs} |")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Signals
    lines.extend(["## Signals", ""])
    if report.signals:
        lines.append("| Signal | Data Type | Unit | Source | Destination | Interface |")
        lines.append("|---|---|---|---|---|---|")
        for s in report.signals:
            lines.append(f"| {s['name']} | {s['data_type']} | {s['unit']} | {s['source']} | {s['destination']} | {s['interface']} |")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Dependencies
    lines.extend(["## Dependencies", ""])
    if report.dependencies:
        lines.append("| Source | Target | Relationship | Description |")
        lines.append("|---|---|---|---|")
        for d in report.dependencies:
            lines.append(f"| {d['source']} | {d['target']} | {d['relationship']} | {d['description']} |")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Functional Flows
    lines.extend(["## Functional Flows", ""])
    if report.functional_flows:
        for f in report.functional_flows:
            lines.append(f"- **{f['name']}**: {f['source']} → {f['target']} via {f['interface']}")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Related Components
    lines.extend(["## Related Components", ""])
    if report.related_components:
        for rc in report.related_components:
            lines.append(f"- {rc}")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Validation Findings
    lines.extend(["## Validation Findings", ""])
    if report.validation_findings:
        lines.append("| ID | Severity | Category | Message |")
        lines.append("|---|---|---|---|")
        for vf in report.validation_findings:
            lines.append(f"| {vf['finding_id']} | {vf['severity']} | {vf['category']} | {vf['message']} |")
    else:
        lines.append("No validation findings for this component.")
    lines.append("")

    # Revision Changes
    lines.extend(["## Revision Changes", ""])
    if report.revision_changes:
        for rc in report.revision_changes:
            lines.append(f"- **{rc['change_type']}** ({rc['entity_type']}): {rc['description']}")
    else:
        lines.append("Not available in extracted source.")
    lines.append("")

    # Evidence
    lines.extend(["## Evidence & Citations", ""])
    if report.evidence:
        for ev in report.evidence:
            cite_str = ev.citation.format() if ev.citation else "N/A"
            lines.append(f"- [{ev.fact_type.value}] {ev.description} {cite_str}")
    else:
        lines.append("No evidence available.")
    lines.append("")

    # Limitations
    lines.extend(["## Limitations", ""])
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")

    return "\n".join(lines)


def export_validation_report_md(report: ValidationReport) -> str:
    """Export ValidationReport to Markdown."""
    lines = [
        "# Architecture Validation Report",
        "",
        f"- **Generated:** {report.generated_at}",
        f"- **Document:** {report.document_id}",
        f"- **Version:** {report.version}",
        f"- **Status:** {report.status}",
        f"- **Errors:** {report.error_count}",
        f"- **Warnings:** {report.warning_count}",
        f"- **Info:** {report.info_count}",
        "",
    ]

    if report.findings:
        lines.extend(["## Findings", ""])
        lines.append("| ID | Severity | Category | Entity | Message |")
        lines.append("|---|---|---|---|---|")
        for f in report.findings:
            entity = f"{f['entity_type']}: {f['entity_name']}"
            lines.append(f"| {f['finding_id']} | {f['severity']} | {f['category']} | {entity} | {f['message']} |")
    else:
        lines.extend(["## Findings", "", "No findings detected."])
    lines.append("")

    lines.extend(["## Limitations", ""])
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")

    return "\n".join(lines)


def export_revision_report_md(report: RevisionReport) -> str:
    """Export RevisionReport to Markdown."""
    lines = [
        "# Revision Comparison Report",
        "",
        f"- **Generated:** {report.generated_at}",
        f"- **Source Version:** {report.source_version}",
        f"- **Target Version:** {report.target_version}",
        f"- **Total Changes:** {report.total_changes}",
        f"- **All Intentional Detected:** {'Yes' if report.all_intentional_detected else 'No'}",
        "",
    ]

    lines.extend(["## Summary Statistics", ""])
    for k, v in report.summary_statistics.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("")

    if report.important_changes:
        lines.extend(["## Important Changes", ""])
        for ic in report.important_changes:
            lines.append(f"- {ic}")
        lines.append("")

    for section_name, entries in [
        ("Added Entities", report.added_entities),
        ("Modified Entities", report.modified_entities),
        ("Renamed Entities", report.renamed_entities),
        ("Removed Entities", report.removed_entities),
    ]:
        lines.extend([f"## {section_name}", ""])
        if entries:
            for e in entries:
                lines.append(f"- [{e['entity_type']}] {e['entity_name']}: {e['description']}")
        else:
            lines.append("None.")
        lines.append("")

    lines.extend(["## Limitations", ""])
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")

    return "\n".join(lines)


def export_impact_report_md(report: ImpactReport) -> str:
    """Export ImpactReport to Markdown."""
    lines = [
        "# Change Impact Analysis Report",
        "",
        f"- **Generated:** {report.generated_at}",
        f"- **Base Version:** {report.base_version}",
        f"- **Target Version:** {report.target_version}",
        f"- **Total Impacts:** {report.total_impacts}",
        f"- **Changes Analyzed:** {report.changes_analyzed}",
        "",
    ]

    if report.critical_risk_areas:
        lines.extend(["## Critical Risk Areas", ""])
        for risk in report.critical_risk_areas:
            lines.append(f"- ⚠️ {risk}")
        lines.append("")

    lines.extend(["## Impact Details", ""])
    for imp in report.impacts:
        lines.append(f"### {imp['change']}")
        lines.append(f"- **Risk:** {imp['risk_assessment']}")
        lines.append(f"- **Affected Components:** {', '.join(imp.get('affected_components', [])) or 'None'}")
        lines.append(f"- **Affected Interfaces:** {', '.join(imp.get('affected_interfaces', [])) or 'None'}")
        lines.append(f"- **Affected Signals:** {', '.join(imp.get('affected_signals', [])) or 'None'}")
        lines.append(f"- **Affected Flows:** {', '.join(imp.get('affected_flows', [])) or 'None'}")
        lines.append("")

    lines.extend(["## Limitations", ""])
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")

    return "\n".join(lines)


def export_report_md(report: Any) -> str:
    """Auto-detect report type and export to Markdown."""
    if isinstance(report, ComponentReport):
        return export_component_report_md(report)
    elif isinstance(report, ValidationReport):
        return export_validation_report_md(report)
    elif isinstance(report, RevisionReport):
        return export_revision_report_md(report)
    elif isinstance(report, ImpactReport):
        return export_impact_report_md(report)
    else:
        return f"# Report\n\n```json\n{export_report_json(report)}\n```\n"


# ==============================
# CSV Export
# ==============================


def export_validation_findings_csv(report: ValidationReport) -> str:
    """Export validation findings to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Finding ID", "Severity", "Category", "Entity Type", "Entity Name", "Related Entity", "Message", "Document", "Version"])
    for f in report.findings:
        writer.writerow([
            f.get("finding_id", ""),
            f.get("severity", ""),
            f.get("category", ""),
            f.get("entity_type", ""),
            f.get("entity_name", ""),
            f.get("related_entity", ""),
            f.get("message", ""),
            f.get("document_id", ""),
            f.get("version", ""),
        ])
    return output.getvalue()


def export_revision_changes_csv(report: RevisionReport) -> str:
    """Export revision changes to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Change ID", "Change Type", "Entity Type", "Entity Name", "Field", "Old Value", "New Value", "Severity", "Description"])
    all_changes = report.added_entities + report.modified_entities + report.renamed_entities + report.removed_entities
    for c in all_changes:
        writer.writerow([
            c.get("change_id", ""),
            c.get("entity_type", ""),  # will use the section we put it in
            c.get("entity_name", ""),
            c.get("entity_name", ""),
            c.get("field", ""),
            c.get("old_value", ""),
            c.get("new_value", ""),
            c.get("severity", ""),
            c.get("description", ""),
        ])
    return output.getvalue()
