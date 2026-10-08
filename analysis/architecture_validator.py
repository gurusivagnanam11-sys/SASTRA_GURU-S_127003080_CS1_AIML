"""Architecture consistency and completeness validation engine.

Implements deterministic structural validation rules over the extracted AUTOSAR HLD model.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import collections

from extraction.models import CompleteArchitectureModel, Direction, Provenance


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationCategory(str, Enum):
    UNDEFINED_REFERENCE = "UNDEFINED_REFERENCE"
    MISSING_REFERENCE = "MISSING_REFERENCE"
    ORPHAN_ENTITY = "ORPHAN_ENTITY"
    INVALID_RELATIONSHIP = "INVALID_RELATIONSHIP"
    MISSING_MAPPING = "MISSING_MAPPING"
    INCOMPLETE_ENTITY = "INCOMPLETE_ENTITY"
    DUPLICATE_ENTITY = "DUPLICATE_ENTITY"
    VERSION_INCONSISTENCY = "VERSION_INCONSISTENCY"


class ValidationFinding(BaseModel):
    finding_id: str
    severity: Severity
    category: ValidationCategory
    entity_type: str
    entity_name: str
    related_entity: Optional[str] = None
    message: str
    document_id: str
    version: str
    provenance: Optional[Provenance] = None


class ValidationSummary(BaseModel):
    status: str = "PASS"
    errors: int = 0
    warnings: int = 0
    info: int = 0


class ValidationResult(BaseModel):
    document_id: str
    version: str
    status: str = "PASS"
    errors: List[ValidationFinding] = Field(default_factory=list)
    warnings: List[ValidationFinding] = Field(default_factory=list)
    info: List[ValidationFinding] = Field(default_factory=list)
    summary: ValidationSummary = Field(default_factory=ValidationSummary)
    findings: List[ValidationFinding] = Field(default_factory=list)


class ArchitectureValidator:
    def __init__(self, model: CompleteArchitectureModel):
        self.model = model
        self.version = model.version
        
        self.components_by_name = {c.name: c for c in model.components}
        self.interfaces_by_name = {i.name: i for i in model.interfaces}
        self.signals_by_name = {s.name: s for s in model.signals}
        self.ports_by_name = {p.name: p for p in model.ports}
        self.flows_by_name = {f.name: f for f in model.functional_flows}
        
        # Document defaults from model components if available
        self.document_id = model.components[0].document if model.components else f"autosar_hld_v{self.version}"

        self.findings: List[ValidationFinding] = []
        self._finding_counter = 0

    def _add_finding(
        self,
        severity: Severity,
        category: ValidationCategory,
        entity_type: str,
        entity_name: str,
        message: str,
        related_entity: Optional[str] = None,
        provenance: Optional[Provenance] = None
    ):
        self._finding_counter += 1
        finding_id = f"VAL-{self._finding_counter:04d}"
        
        finding = ValidationFinding(
            finding_id=finding_id,
            severity=severity,
            category=category,
            entity_type=entity_type,
            entity_name=entity_name,
            related_entity=related_entity,
            message=message,
            document_id=self.document_id,
            version=self.version,
            provenance=provenance
        )
        self.findings.append(finding)

    def validate(self) -> ValidationResult:
        self._check_duplicates()
        self._check_undefined_components()
        self._check_undefined_interfaces()
        self._check_undefined_signals()
        self._check_port_consistency()
        self._check_dependency_validation()
        self._check_orphans()
        self._check_flow_completeness()
        self._check_entity_completeness()

        result = ValidationResult(
            document_id=self.document_id,
            version=self.version
        )

        for finding in self.findings:
            result.findings.append(finding)
            if finding.severity == Severity.ERROR:
                result.errors.append(finding)
                result.summary.errors += 1
            elif finding.severity == Severity.WARNING:
                result.warnings.append(finding)
                result.summary.warnings += 1
            elif finding.severity == Severity.INFO:
                result.info.append(finding)
                result.summary.info += 1

        if result.summary.errors > 0:
            result.status = result.summary.status = "ERROR"
        elif result.summary.warnings > 0:
            result.status = result.summary.status = "WARNING"
        else:
            result.status = result.summary.status = "PASS"

        return result

    def _create_provenance(self, entity) -> Optional[Provenance]:
        if hasattr(entity, 'document') and hasattr(entity, 'chunk_id'):
            return Provenance(
                document=entity.document,
                version=entity.version,
                page=entity.page,
                section=entity.section,
                section_title=entity.section_title,
                chunk_id=entity.chunk_id
            )
        return None

    def _check_duplicates(self):
        comp_names = [c.name for c in self.model.components]
        for name, count in collections.Counter(comp_names).items():
            if count > 1:
                self._add_finding(Severity.ERROR, ValidationCategory.DUPLICATE_ENTITY, "Component", name, f"Duplicate component definition: {name}")

        iface_names = [i.name for i in self.model.interfaces]
        for name, count in collections.Counter(iface_names).items():
            if count > 1:
                self._add_finding(Severity.ERROR, ValidationCategory.DUPLICATE_ENTITY, "Interface", name, f"Duplicate interface definition: {name}")

        sig_names = [s.name for s in self.model.signals]
        for name, count in collections.Counter(sig_names).items():
            if count > 1:
                self._add_finding(Severity.ERROR, ValidationCategory.DUPLICATE_ENTITY, "Signal", name, f"Duplicate signal definition: {name}")

    def _check_undefined_components(self):
        for dep in self.model.dependencies:
            if dep.target_component not in self.components_by_name and dep.target_component not in ["Physical Sensors", "External Tester", "CAN Bus", "Actuators"]:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "Dependency",
                    dep.source_component,
                    f"Undefined component reference: {dep.target_component}",
                    related_entity=dep.target_component,
                    provenance=self._create_provenance(dep)
                )

    def _check_undefined_interfaces(self):
        for port in self.model.ports:
            if port.interface and port.interface not in ["not_specified", "-"]:
                if port.interface not in self.interfaces_by_name:
                    self._add_finding(
                        Severity.ERROR,
                        ValidationCategory.UNDEFINED_REFERENCE,
                        "Port",
                        port.name,
                        f"Port {port.name} references undefined interface {port.interface}.",
                        related_entity=port.interface,
                        provenance=self._create_provenance(port)
                    )

    def _check_undefined_signals(self):
        for port in self.model.ports:
            for sig in port.signals:
                if sig not in self.signals_by_name:
                    self._add_finding(
                        Severity.ERROR,
                        ValidationCategory.UNDEFINED_REFERENCE,
                        "Port",
                        port.name,
                        f"Port {port.name} references undefined signal {sig}.",
                        related_entity=sig,
                        provenance=self._create_provenance(port)
                    )

        for iface in self.model.interfaces:
            for sig in iface.signals:
                if sig not in self.signals_by_name:
                    self._add_finding(
                        Severity.ERROR,
                        ValidationCategory.UNDEFINED_REFERENCE,
                        "Interface",
                        iface.name,
                        f"Interface {iface.name} references undefined signal {sig}.",
                        related_entity=sig,
                        provenance=self._create_provenance(iface)
                    )

    def _check_port_consistency(self):
        for port in self.model.ports:
            if port.component not in self.components_by_name:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "Port",
                    port.name,
                    f"Port {port.name} references missing component {port.component}.",
                    related_entity=port.component,
                    provenance=self._create_provenance(port)
                )
            if port.direction == Direction.UNKNOWN:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.INVALID_RELATIONSHIP,
                    "Port",
                    port.name,
                    f"Port {port.name} has an invalid or unknown direction.",
                    provenance=self._create_provenance(port)
                )

    def _check_dependency_validation(self):
        for dep in self.model.dependencies:
            if dep.source_component not in self.components_by_name and dep.source_component not in ["Physical Sensors", "External Tester", "CAN Bus", "Actuators"]:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "Dependency",
                    dep.source_component,
                    f"Dependency from undefined component {dep.source_component}.",
                    related_entity=dep.source_component,
                    provenance=self._create_provenance(dep)
                )
            if dep.source_component == dep.target_component:
                self._add_finding(
                    Severity.WARNING,
                    ValidationCategory.INVALID_RELATIONSHIP,
                    "Dependency",
                    dep.source_component,
                    f"Component {dep.source_component} has a self-dependency.",
                    provenance=self._create_provenance(dep)
                )

    def _check_orphans(self):
        # Orphan Components
        for comp in self.model.components:
            has_port = any(p.component == comp.name for p in self.model.ports)
            has_dep = any(d.source_component == comp.name or d.target_component == comp.name for d in self.model.dependencies)
            has_flow = any(comp.name in f.steps or f.source == comp.name or f.target == comp.name for f in self.model.functional_flows)
            
            if not (has_port or has_dep or has_flow):
                self._add_finding(
                    Severity.WARNING,
                    ValidationCategory.ORPHAN_ENTITY,
                    "Component",
                    comp.name,
                    f"Component {comp.name} appears isolated from the architecture graph.",
                    provenance=self._create_provenance(comp)
                )

        # Orphan Interfaces
        for iface in self.model.interfaces:
            has_port_ref = any(p.interface == iface.name for p in self.model.ports)
            has_flow_ref = any(f.interface == iface.name for f in self.model.functional_flows)
            if not has_port_ref and not has_flow_ref:
                self._add_finding(
                    Severity.WARNING,
                    ValidationCategory.ORPHAN_ENTITY,
                    "Interface",
                    iface.name,
                    f"Interface {iface.name} has no associated port mapping.",
                    provenance=self._create_provenance(iface)
                )

        # Orphan Signals
        for sig in self.model.signals:
            has_port_ref = any(sig.name in p.signals for p in self.model.ports)
            has_iface_ref = any(sig.name in i.signals for i in self.model.interfaces)
            has_flow_ref = any(f.signal == sig.name for f in self.model.functional_flows)
            if not (has_port_ref or has_iface_ref or has_flow_ref):
                self._add_finding(
                    Severity.WARNING,
                    ValidationCategory.ORPHAN_ENTITY,
                    "Signal",
                    sig.name,
                    f"Signal {sig.name} appears unused.",
                    provenance=self._create_provenance(sig)
                )

    def _check_flow_completeness(self):
        for flow in self.model.functional_flows:
            if flow.source not in self.components_by_name and flow.source not in ["Physical Sensors", "External tester"]:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "FunctionalFlow",
                    flow.name,
                    f"Functional flow references undefined component {flow.source}.",
                    related_entity=flow.source,
                    provenance=self._create_provenance(flow)
                )
            if flow.target not in self.components_by_name and flow.target not in ["Actuators"]:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "FunctionalFlow",
                    flow.name,
                    f"Functional flow references undefined component {flow.target}.",
                    related_entity=flow.target,
                    provenance=self._create_provenance(flow)
                )
            if flow.interface and flow.interface not in ["not_specified", "-"]:
                if flow.interface not in self.interfaces_by_name:
                    self._add_finding(
                        Severity.ERROR,
                        ValidationCategory.UNDEFINED_REFERENCE,
                        "FunctionalFlow",
                        flow.name,
                        f"Functional flow references undefined interface {flow.interface}.",
                        related_entity=flow.interface,
                        provenance=self._create_provenance(flow)
                    )
            if flow.signal and flow.signal not in self.signals_by_name:
                self._add_finding(
                    Severity.ERROR,
                    ValidationCategory.UNDEFINED_REFERENCE,
                    "FunctionalFlow",
                    flow.name,
                    f"Functional flow references undefined signal {flow.signal}.",
                    related_entity=flow.signal,
                    provenance=self._create_provenance(flow)
                )

    def _check_entity_completeness(self):
        for comp in self.model.components:
            if not comp.description:
                self._add_finding(
                    Severity.INFO,
                    ValidationCategory.INCOMPLETE_ENTITY,
                    "Component",
                    comp.name,
                    f"Component {comp.name} is missing a description.",
                    provenance=self._create_provenance(comp)
                )


def validate_architecture(model: CompleteArchitectureModel) -> ValidationResult:
    """Validate a complete architecture model and return findings."""
    validator = ArchitectureValidator(model)
    return validator.validate()
