"""Architecture intelligence data models for AUTOSAR HLD specifications.

Defines structured entities for Software Components (SWCs), Interfaces, Ports,
Signals, Component Dependencies, Functional Flows, Architecture Graphs,
and Structural Revision Diffs with full provenance.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class Direction(str, Enum):
    INPUT = "Input"
    OUTPUT = "Output"
    INOUT = "InOut"
    UNKNOWN = "Unknown"


class InterfaceType(str, Enum):
    SENDER_RECEIVER = "Sender-Receiver"
    CLIENT_SERVER = "Client-Server"
    MODE_SWITCH = "Mode-Switch"
    TRIGGER = "Trigger"
    NON_AUTOSAR = "Non-AUTOSAR"
    UNKNOWN = "Unknown"


class ChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MODIFIED = "MODIFIED"
    RENAMED = "RENAMED"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Provenance(BaseModel):
    """Full provenance pointer linking an architectural fact to source HLD evidence."""
    document: str
    version: str
    page: int
    section: str
    section_title: str = ""
    chunk_id: str
    confidence: float = 1.0


class ExtractedComponent(BaseModel):
    """AUTOSAR Software Component (SWC) entity with full provenance."""
    component_id: Optional[str] = None
    name: str
    component_type: str = "Application Software Component"
    description: str = ""
    ports: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    document: str
    version: str
    page: int
    section: str
    section_title: str = ""
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.component_id:
            self.component_id = f"comp_{self.name.lower()}_{self.version}"


class ExtractedInterface(BaseModel):
    """AUTOSAR Interface entity with full provenance."""
    interface_id: Optional[str] = None
    name: str
    interface_type: str = "Sender-Receiver"
    description: str = ""
    provider: Optional[str] = None
    consumer: Optional[str] = None
    signals: List[str] = Field(default_factory=list)
    operations: List[str] = Field(default_factory=list)
    document: str
    version: str
    page: int
    section: str
    section_title: str = ""
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.interface_id:
            self.interface_id = f"iface_{self.name.lower()}_{self.version}"


class ExtractedPort(BaseModel):
    """AUTOSAR Software Port entity with component & interface associations."""
    port_id: Optional[str] = None
    name: str
    component: str
    direction: Direction = Direction.UNKNOWN
    port_type: str = "Standard"
    interface: str = "not_specified"
    signals: List[str] = Field(default_factory=list)
    document: str
    version: str
    page: int
    section: str
    section_title: str = "Port Definitions"
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.port_id:
            self.port_id = f"port_{self.component.lower()}_{self.name.lower()}_{self.version}"


class ExtractedSignal(BaseModel):
    """AUTOSAR Signal entity with data type, unit, and routing."""
    signal_id: Optional[str] = None
    name: str
    data_type: str
    unit: str = "-"
    interface: str = "not_specified"
    source: str = "not_specified"
    destination: str = "not_specified"
    port: Optional[str] = None
    component: Optional[str] = None
    document: str
    version: str
    page: int
    section: str
    section_title: str = "Signals"
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.signal_id:
            self.signal_id = f"sig_{self.name.lower()}_{self.version}"


class ExtractedDependency(BaseModel):
    """Component-to-Component architectural dependency relationship."""
    dependency_id: Optional[str] = None
    source_component: str
    target_component: str
    relationship_type: str = "depends on"
    description: str = ""
    document: str
    version: str
    page: int
    section: str
    section_title: str = "Dependencies"
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.dependency_id:
            self.dependency_id = f"dep_{self.source_component.lower()}_{self.target_component.lower()}_{self.version}"


class ExtractedFunctionalFlow(BaseModel):
    """End-to-end signal/execution flow across components and interfaces."""
    flow_id: Optional[str] = None
    name: str
    steps: List[str] = Field(default_factory=list)
    source: str = "not_specified"
    interface: str = "not_specified"
    signal: Optional[str] = None
    target: str = "not_specified"
    description: str = ""
    document: str
    version: str
    page: int
    section: str
    section_title: str = "Functional Flows"
    chunk_id: str
    confidence: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.flow_id:
            self.flow_id = f"flow_{self.name.lower().replace(' ', '_')}_{self.version}"


class GraphNode(BaseModel):
    """Node in the architecture traceability graph."""
    id: str
    name: str
    node_type: str  # component, interface, port, signal
    version: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Optional[Provenance] = None


class GraphEdge(BaseModel):
    """Directed edge in the architecture traceability graph."""
    source: str
    target: str
    relationship: str  # PROVIDES, REQUIRES, CONNECTS_TO, CARRIES, DEPENDS_ON, CONTAINS
    version: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Optional[Provenance] = None


class ArchitectureGraph(BaseModel):
    """Complete graph model of the AUTOSAR HLD architecture."""
    version: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructuralChange(BaseModel):
    """Individual architectural difference between two HLD revisions."""
    change_id: str
    change_type: ChangeType
    entity_type: str  # component, interface, port, signal, dependency
    entity_name: str
    field: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    severity: Severity = Severity.MEDIUM
    description: str
    source_v1: Optional[Dict[str, Any]] = None
    source_v2: Optional[Dict[str, Any]] = None


class RevisionDiffResult(BaseModel):
    """Complete deterministic revision comparison result between two HLD versions."""
    base_version: str = "1.0"
    target_version: str = "2.0"
    total_changes: int = 0
    changes: List[StructuralChange] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)
    all_intentional_changes_detected: bool = False
    missing_intentional_changes: List[str] = Field(default_factory=list)


class ImpactItem(BaseModel):
    """Affected architectural entity identified in impact analysis."""
    entity_type: str  # component, interface, port, signal, flow
    entity_name: str
    impact_level: str  # Direct, Downstream, Upstream
    rationale: str
    provenance: Optional[Dict[str, Any]] = None


class ChangeImpactAnalysis(BaseModel):
    """Impact analysis report for an architectural modification."""
    change: StructuralChange
    affected_components: List[str] = Field(default_factory=list)
    affected_interfaces: List[str] = Field(default_factory=list)
    affected_ports: List[str] = Field(default_factory=list)
    affected_signals: List[str] = Field(default_factory=list)
    affected_flows: List[str] = Field(default_factory=list)
    impacted_entities: List[ImpactItem] = Field(default_factory=list)
    risk_assessment: str = ""


class ComprehensiveImpactReport(BaseModel):
    """Consolidated impact assessment across all detected revision changes."""
    base_version: str
    target_version: str
    total_impacts: int
    changes_analyzed: int
    impacts_by_change: List[ChangeImpactAnalysis] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class CompleteArchitectureModel(BaseModel):
    """Comprehensive architecture model containing all extracted entities and relationships."""
    version: str
    components: List[ExtractedComponent] = Field(default_factory=list)
    interfaces: List[ExtractedInterface] = Field(default_factory=list)
    ports: List[ExtractedPort] = Field(default_factory=list)
    signals: List[ExtractedSignal] = Field(default_factory=list)
    dependencies: List[ExtractedDependency] = Field(default_factory=list)
    functional_flows: List[ExtractedFunctionalFlow] = Field(default_factory=list)
    graph: Optional[ArchitectureGraph] = None
