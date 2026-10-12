"""Engineering report generation engine for AUTOSAR HLD Assistant.

Generates structured Component, Validation, Revision, and Impact reports
by reusing existing Phase 3/7 analysis engines. No duplicate logic.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from extraction.basic_extractor import get_architecture_extractor
from extraction.models import ChangeType
from analysis.architecture_validator import validate_architecture
from analysis.revision_diff import get_revision_diff_engine
from analysis.impact_analysis import get_impact_analyzer

from reports.models import (
    ComponentReport,
    DocumentGovernance,
    DocumentStatus,
    EngineeringFact,
    EvidenceCitation,
    FactType,
    ImpactReport,
    RevisionReport,
    ValidationReport,
)

logger = logging.getLogger(__name__)


# ==============================
# In-memory governance store
# ==============================

_governance_store: Dict[str, DocumentGovernance] = {}


def _init_default_governance():
    """Initialize default governance entries for known documents and persisted DB records."""
    if _governance_store:
        return
    now = datetime.now(timezone.utc).isoformat()
    _governance_store["autosar_hld_v1.0"] = DocumentGovernance(
        document_id="autosar_hld_v1.0",
        document_name="AUTOSAR HLD Specification v1.0",
        version="1.0",
        status=DocumentStatus.APPROVED,
        ingestion_timestamp=now,
        source_type="HLD Specification",
        last_status_change=now,
        changed_by="system",
    )
    _governance_store["autosar_hld_v2.0"] = DocumentGovernance(
        document_id="autosar_hld_v2.0",
        document_name="AUTOSAR HLD Specification v2.0",
        version="2.0",
        status=DocumentStatus.APPROVED,
        ingestion_timestamp=now,
        source_type="HLD Specification",
        last_status_change=now,
        changed_by="system",
    )

    try:
        from db.repository import HLDRepository
        from db.models import GovernanceRecord
        repo = HLDRepository()
        session = repo.SessionFactory()
        records = session.query(GovernanceRecord).order_by(GovernanceRecord.created_at.desc()).all()
        seen = set()
        for r in records:
            if r.document_id not in _governance_store and r.document_id not in seen:
                seen.add(r.document_id)
                status_str = (r.new_status or "DRAFT").upper()
                try:
                    stat_enum = DocumentStatus(status_str)
                except Exception:
                    stat_enum = DocumentStatus.DRAFT
                _governance_store[r.document_id] = DocumentGovernance(
                    document_id=r.document_id,
                    document_name=r.document_id,
                    version="unknown",
                    status=stat_enum,
                    ingestion_timestamp=r.created_at.isoformat() if r.created_at else now,
                    source_type="Uploaded Document",
                    last_status_change=r.created_at.isoformat() if r.created_at else now,
                    changed_by=r.changed_by or "system",
                )
        session.close()
    except Exception as e:
        logger.debug(f"Governance DB init notice: {e}")


def get_all_governance() -> List[DocumentGovernance]:
    _init_default_governance()
    return list(_governance_store.values())


def get_governance(document_id: str) -> Optional[DocumentGovernance]:
    _init_default_governance()
    return _governance_store.get(document_id)


def set_governance_status(
    document_id: str,
    new_status: DocumentStatus,
    changed_by: str = "Engineering Reviewer",
) -> Optional[DocumentGovernance]:
    _init_default_governance()
    gov = _governance_store.get(document_id)
    if gov is None:
        gov = DocumentGovernance(
            document_id=document_id,
            document_name=document_id,
            version="1.0",
            status=new_status,
            ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
            source_type="Uploaded Document",
            last_status_change=datetime.now(timezone.utc).isoformat(),
            changed_by=changed_by,
        )
        _governance_store[document_id] = gov
    else:
        gov.status = new_status
        gov.last_status_change = datetime.now(timezone.utc).isoformat()
        gov.changed_by = changed_by
    return gov


def get_active_version() -> str:
    """Return the latest APPROVED version, defaulting to '2.0'."""
    _init_default_governance()
    approved = [g for g in _governance_store.values() if g.status == DocumentStatus.APPROVED]
    if approved:
        return max(approved, key=lambda g: g.version).version
    return "2.0"


# ==============================
# Component Report Generator
# ==============================


def generate_component_report(
    component_name: str,
    version: Optional[str] = None,
) -> Optional[ComponentReport]:
    """Generate a structured engineering report for a specific SWC.

    Reuses the existing ArchitectureExtractor and ArchitectureValidator.
    Returns None if the component does not exist.
    """
    extractor = get_architecture_extractor()
    ver = version or get_active_version()

    # Get complete model for this version
    model = extractor.get_complete_model(version=ver)

    # Find the component
    comp = next((c for c in model.components if c.name == component_name), None)
    if comp is None:
        return None

    # Governance status
    _init_default_governance()
    gov_key = f"autosar_hld_v{ver}"
    gov = _governance_store.get(gov_key)
    source_status = gov.status.value if gov else "Not available in extracted source."

    # Build citation helper
    def _cite(entity) -> EvidenceCitation:
        return EvidenceCitation(
            document_name=getattr(entity, "document", f"autosar_hld_v{ver}"),
            version=getattr(entity, "version", ver),
            page=getattr(entity, "page", None),
            section=getattr(entity, "section", None),
            chunk_id=getattr(entity, "chunk_id", None),
        )

    evidence: List[EngineeringFact] = []

    # Component fact
    evidence.append(EngineeringFact(
        fact_type=FactType.EXTRACTED,
        description=f"Component '{comp.name}' of type '{comp.component_type}' extracted from source.",
        citation=_cite(comp),
    ))

    # Interfaces connected to this component
    comp_interfaces: List[str] = []
    for iface in model.interfaces:
        if iface.provider == component_name or iface.consumer == component_name:
            comp_interfaces.append(iface.name)
            evidence.append(EngineeringFact(
                fact_type=FactType.EXTRACTED,
                description=f"Interface '{iface.name}' ({iface.interface_type}) connected to {component_name}.",
                citation=_cite(iface),
            ))

    # Ports
    comp_ports = [p for p in model.ports if p.component == component_name]
    port_dicts = []
    for p in comp_ports:
        port_dicts.append({
            "name": p.name,
            "direction": p.direction.value,
            "interface": p.interface,
            "signals": p.signals,
        })
        evidence.append(EngineeringFact(
            fact_type=FactType.EXTRACTED,
            description=f"Port '{p.name}' ({p.direction.value}) on {component_name}.",
            citation=_cite(p),
        ))

    # Signals consumed/produced by this component
    comp_signals = [s for s in model.signals if s.source == component_name or s.destination == component_name]
    signal_dicts = []
    for s in comp_signals:
        signal_dicts.append({
            "name": s.name,
            "data_type": s.data_type,
            "unit": s.unit,
            "source": s.source,
            "destination": s.destination,
            "interface": s.interface,
        })

    # Dependencies
    comp_deps = [d for d in model.dependencies if d.source_component == component_name or d.target_component == component_name]
    dep_dicts = []
    for d in comp_deps:
        dep_dicts.append({
            "source": d.source_component,
            "target": d.target_component,
            "relationship": d.relationship_type,
            "description": d.description,
        })
        evidence.append(EngineeringFact(
            fact_type=FactType.EXTRACTED,
            description=f"Dependency: {d.source_component} → {d.target_component} ({d.relationship_type}).",
            citation=_cite(d),
        ))

    # Related components (unique set from deps)
    related = set()
    for d in comp_deps:
        if d.source_component != component_name:
            related.add(d.source_component)
        if d.target_component != component_name:
            related.add(d.target_component)

    # Functional flows
    comp_flows = [f for f in model.functional_flows if component_name in f.steps or f.source == component_name or f.target == component_name]
    flow_dicts = []
    for f in comp_flows:
        flow_dicts.append({
            "name": f.name,
            "source": f.source,
            "target": f.target,
            "interface": f.interface,
            "signal": f.signal,
            "steps": f.steps,
        })

    # Validation findings
    val_result = validate_architecture(model)
    comp_findings = [
        f for f in val_result.findings
        if f.entity_name == component_name or f.related_entity == component_name
    ]
    finding_dicts = []
    for f in comp_findings:
        finding_dicts.append({
            "finding_id": f.finding_id,
            "severity": f.severity.value,
            "category": f.category.value,
            "message": f.message,
        })
        evidence.append(EngineeringFact(
            fact_type=FactType.VALIDATION,
            description=f"Validation {f.severity.value}: {f.message}",
        ))

    # Revision changes (if available)
    revision_changes: List[Dict[str, Any]] = []
    try:
        diff_engine = get_revision_diff_engine()
        diff_result = diff_engine.compare_versions(base_version="1.0", target_version="2.0")
        for c in diff_result.changes:
            if c.entity_name == component_name:
                revision_changes.append({
                    "change_type": c.change_type.value,
                    "entity_type": c.entity_type,
                    "field": c.field,
                    "old_value": str(c.old_value) if c.old_value is not None else None,
                    "new_value": str(c.new_value) if c.new_value is not None else None,
                    "description": c.description,
                })
                evidence.append(EngineeringFact(
                    fact_type=FactType.DERIVED,
                    description=f"Revision change: {c.description}",
                ))
    except Exception as e:
        logger.warning(f"Could not generate revision info for {component_name}: {e}")

    # Impact information
    impact_info: List[Dict[str, Any]] = []
    try:
        impact_analyzer = get_impact_analyzer()
        impact_report = impact_analyzer.generate_comprehensive_report(base_version="1.0", target_version="2.0")
        for ci in impact_report.impacts_by_change:
            if component_name in ci.affected_components:
                impact_info.append({
                    "change": ci.change.description,
                    "risk_assessment": ci.risk_assessment,
                    "affected_interfaces": ci.affected_interfaces,
                    "affected_signals": ci.affected_signals,
                    "affected_flows": ci.affected_flows,
                })
                evidence.append(EngineeringFact(
                    fact_type=FactType.DERIVED,
                    description=f"Impact: {ci.change.description} — {ci.risk_assessment}",
                ))
    except Exception as e:
        logger.warning(f"Could not generate impact info for {component_name}: {e}")

    limitations = [
        "This report is auto-generated from extracted HLD data. It does not replace formal architecture review.",
        "Provenance citations reference the extracted source chunks, not raw PDF page coordinates.",
    ]

    return ComponentReport(
        component_name=component_name,
        description=comp.description or "Not available in extracted source.",
        source_document=comp.document,
        source_version=ver,
        source_status=source_status,
        interfaces=comp_interfaces,
        ports=port_dicts,
        signals=signal_dicts,
        dependencies=dep_dicts,
        functional_flows=flow_dicts,
        related_components=sorted(list(related)),
        validation_findings=finding_dicts,
        revision_changes=revision_changes,
        impact_information=impact_info,
        evidence=evidence,
        limitations=limitations,
    )


# ==============================
# Validation Report Generator
# ==============================


def generate_validation_report(version: Optional[str] = None) -> ValidationReport:
    """Generate a structured validation report reusing the Phase 7 validator."""
    ver = version or get_active_version()
    extractor = get_architecture_extractor()
    model = extractor.get_complete_model(version=ver)
    val_result = validate_architecture(model)

    findings_dicts = []
    for f in val_result.findings:
        findings_dicts.append({
            "finding_id": f.finding_id,
            "severity": f.severity.value,
            "category": f.category.value,
            "entity_type": f.entity_type,
            "entity_name": f.entity_name,
            "related_entity": f.related_entity,
            "message": f.message,
            "document_id": f.document_id,
            "version": f.version,
        })

    return ValidationReport(
        document_id=val_result.document_id,
        version=ver,
        status=val_result.status,
        error_count=val_result.summary.errors,
        warning_count=val_result.summary.warnings,
        info_count=val_result.summary.info,
        findings=findings_dicts,
        limitations=[
            "Validation operates over extracted entities only.",
            "Does not replace formal AUTOSAR governance or ISO 26262 compliance checks.",
        ],
    )


# ==============================
# Revision Report Generator
# ==============================


def generate_revision_report(
    source_version: str = "1.0",
    target_version: str = "2.0",
) -> RevisionReport:
    """Generate a structured revision comparison report reusing the Phase 3 diff engine."""
    diff_engine = get_revision_diff_engine()
    diff_result = diff_engine.compare_versions(base_version=source_version, target_version=target_version)

    added = []
    removed = []
    modified = []
    renamed = []
    important_changes = []

    for c in diff_result.changes:
        entry = {
            "change_id": c.change_id,
            "entity_type": c.entity_type,
            "entity_name": c.entity_name,
            "field": c.field,
            "old_value": str(c.old_value) if c.old_value is not None else None,
            "new_value": str(c.new_value) if c.new_value is not None else None,
            "severity": c.severity.value,
            "description": c.description,
        }
        if c.change_type == ChangeType.ADDED:
            added.append(entry)
        elif c.change_type == ChangeType.REMOVED:
            removed.append(entry)
        elif c.change_type == ChangeType.MODIFIED:
            modified.append(entry)
        elif c.change_type == ChangeType.RENAMED:
            renamed.append(entry)

        if c.severity.value in ("high", "critical"):
            important_changes.append(c.description)

    return RevisionReport(
        source_version=source_version,
        target_version=target_version,
        total_changes=diff_result.total_changes,
        added_entities=added,
        removed_entities=removed,
        modified_entities=modified,
        renamed_entities=renamed,
        summary_statistics=diff_result.summary,
        important_changes=important_changes,
        all_intentional_detected=diff_result.all_intentional_changes_detected,
        limitations=[
            "Comparison is structural and deterministic.",
            "Does not infer semantic intent behind changes.",
        ],
    )


# ==============================
# Impact Report Generator
# ==============================


def generate_impact_report(
    base_version: str = "1.0",
    target_version: str = "2.0",
) -> ImpactReport:
    """Generate a structured impact analysis report reusing the Phase 3 impact engine."""
    impact_analyzer = get_impact_analyzer()
    report = impact_analyzer.generate_comprehensive_report(
        base_version=base_version, target_version=target_version
    )

    impacts_dicts = []
    for ci in report.impacts_by_change:
        impacts_dicts.append({
            "change": ci.change.description,
            "change_type": ci.change.change_type.value,
            "entity_type": ci.change.entity_type,
            "entity_name": ci.change.entity_name,
            "affected_components": ci.affected_components,
            "affected_interfaces": ci.affected_interfaces,
            "affected_ports": ci.affected_ports,
            "affected_signals": ci.affected_signals,
            "affected_flows": ci.affected_flows,
            "risk_assessment": ci.risk_assessment,
            "impacted_entities": [
                {
                    "entity_type": ie.entity_type,
                    "entity_name": ie.entity_name,
                    "impact_level": ie.impact_level,
                    "rationale": ie.rationale,
                }
                for ie in ci.impacted_entities
            ],
        })

    return ImpactReport(
        base_version=base_version,
        target_version=target_version,
        total_impacts=report.total_impacts,
        changes_analyzed=report.changes_analyzed,
        impacts=impacts_dicts,
        critical_risk_areas=report.summary.get("critical_risk_areas", []),
        limitations=[
            "Impact analysis traces structural propagation only.",
            "Does not model runtime behavior or timing effects.",
        ],
    )
