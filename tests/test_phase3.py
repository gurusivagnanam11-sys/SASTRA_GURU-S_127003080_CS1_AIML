"""Comprehensive test suite for Phase 3: Architecture Intelligence & Structural Traceability.

Validates:
1. Pydantic Architecture Models & Provenance Integrity
2. Deterministic Entity Extraction (SWCs, Interfaces, Ports, Signals, Dependencies, Flows)
3. Architecture Graph Model (Nodes, Directed Edges, Connectivity)
4. Deterministic Structural Revision Diff Engine with Hard 7/7 Intentional Modification Verification
5. Architectural Impact Analysis & Risk Propagation Engine
6. Phase 3 FastAPI Endpoints
"""

import pytest
from fastapi.testclient import TestClient

from analysis.impact_analysis import ImpactAnalysisEngine, get_impact_analyzer
from analysis.revision_diff import RevisionDiffEngine, get_revision_diff_engine
from app.main import app
from extraction.basic_extractor import ArchitectureExtractor, get_architecture_extractor
from extraction.models import (
    ArchitectureGraph,
    ChangeType,
    CompleteArchitectureModel,
    Direction,
    ExtractedComponent,
    ExtractedDependency,
    ExtractedFunctionalFlow,
    ExtractedInterface,
    ExtractedPort,
    ExtractedSignal,
    GraphEdge,
    GraphNode,
    ImpactItem,
    InterfaceType,
    Provenance,
    RevisionDiffResult,
    Severity,
    StructuralChange,
)


@pytest.fixture
def client():
    """TestClient fixture for FastAPI."""
    return TestClient(app)


@pytest.fixture
def extractor():
    """ArchitectureExtractor fixture."""
    return get_architecture_extractor()


@pytest.fixture
def diff_engine():
    """RevisionDiffEngine fixture."""
    return get_revision_diff_engine()


@pytest.fixture
def impact_analyzer():
    """ImpactAnalysisEngine fixture."""
    return get_impact_analyzer()


# ==========================================
# 1. Models & Provenance Tests
# ==========================================


def test_provenance_model():
    """Verify Provenance model holds all required document pointers."""
    prov = Provenance(
        document="AUTOSAR_HLD_v2.0",
        version="2.0",
        page=7,
        section="5.",
        section_title="Signals",
        chunk_id="chunk_test_01",
        confidence=1.0,
    )
    assert prov.document == "AUTOSAR_HLD_v2.0"
    assert prov.version == "2.0"
    assert prov.page == 7
    assert prov.section == "5."
    assert prov.section_title == "Signals"
    assert prov.chunk_id == "chunk_test_01"


def test_port_model_id_and_direction():
    """Verify ExtractedPort generates deterministic ID and parses Direction enum."""
    port = ExtractedPort(
        name="VehicleSpeedIn",
        component="VehicleControl",
        direction="Input",
        interface="VehicleDataInterface",
        signals=["VehicleSpeed"],
        document="doc",
        version="2.0",
        page=7,
        section="6.",
        chunk_id="chunk_port_1",
    )
    assert port.direction == Direction.INPUT
    assert port.port_id == "port_vehiclecontrol_vehiclespeedin_2.0"
    assert port.signals == ["VehicleSpeed"]


def test_signal_model_id_and_precision():
    """Verify ExtractedSignal model stores data type and unit with generated ID."""
    sig = ExtractedSignal(
        name="VehicleSpeed",
        data_type="float64",
        unit="km/h",
        source="SensorManager",
        destination="VehicleControl",
        interface="VehicleDataInterface",
        document="doc",
        version="2.0",
        page=7,
        section="5.",
        chunk_id="chunk_sig_1",
    )
    assert sig.signal_id == "sig_vehiclespeed_2.0"
    assert sig.data_type == "float64"
    assert sig.unit == "km/h"


def test_dependency_model():
    """Verify ExtractedDependency records source and target coupling."""
    dep = ExtractedDependency(
        source_component="VehicleControl",
        target_component="SafetyManager",
        relationship_type="safety override",
        description="Receives SafetyStatus",
        document="doc",
        version="2.0",
        page=8,
        section="7.1",
        chunk_id="chunk_dep_1",
    )
    assert dep.dependency_id == "dep_vehiclecontrol_safetymanager_2.0"
    assert dep.source_component == "VehicleControl"
    assert dep.target_component == "SafetyManager"


def test_functional_flow_model():
    """Verify ExtractedFunctionalFlow records end-to-end breadcrumb steps."""
    flow = ExtractedFunctionalFlow(
        name="Sensor Data Flow",
        steps=["Physical sensors", "SensorManager", "VehicleDataInterface", "VehicleControl", "ControlCommand", "Actuators"],
        source="SensorManager",
        interface="VehicleDataInterface",
        target="VehicleControl",
        description="Sensor pipeline",
        document="doc",
        version="2.0",
        page=8,
        section="8.1",
        chunk_id="chunk_flow_1",
    )
    assert flow.flow_id == "flow_sensor_data_flow_2.0"
    assert len(flow.steps) == 6
    assert flow.steps[0] == "Physical sensors"
    assert flow.steps[-1] == "Actuators"


# ==========================================
# 2. Entity Extraction Tests (v1.0 vs v2.0)
# ==========================================


def test_extract_components_v1_and_v2(extractor):
    """Verify component extraction across versions preserves provenance."""
    v1_comps = extractor.extract_components(version="1.0")
    v2_comps = extractor.extract_components(version="2.0")

    assert len(v1_comps) == 4
    assert len(v2_comps) == 5

    v1_names = {c.name for c in v1_comps}
    v2_names = {c.name for c in v2_comps}

    assert "SafetyManager" not in v1_names
    assert "SafetyManager" in v2_names

    # Check VehicleControl provenance and port/dependency updates
    vc_v1 = next(c for c in v1_comps if c.name == "VehicleControl")
    vc_v2 = next(c for c in v2_comps if c.name == "VehicleControl")

    assert "SafetyStatusIn" not in vc_v1.ports
    assert "SafetyStatusIn" in vc_v2.ports
    assert "SafetyManager" not in vc_v1.dependencies
    assert "SafetyManager" in vc_v2.dependencies
    assert vc_v1.page == 4
    assert vc_v2.page == 4


def test_extract_interfaces_v1_and_v2(extractor):
    """Verify interface extraction detects rename and addition across releases."""
    v1_ifaces = extractor.extract_interfaces(version="1.0")
    v2_ifaces = extractor.extract_interfaces(version="2.0")

    assert len(v1_ifaces) == 3
    assert len(v2_ifaces) == 4

    v1_names = {i.name for i in v1_ifaces}
    v2_names = {i.name for i in v2_ifaces}

    # v1.0 has CommunicationInterface; v2.0 has V2XCommunicationInterface
    assert "CommunicationInterface" in v1_names
    assert "V2XCommunicationInterface" not in v1_names

    assert "V2XCommunicationInterface" in v2_names
    assert "SafetyMonitorInterface" in v2_names
    assert "SafetyMonitorInterface" not in v1_names

    smi = next(i for i in v2_ifaces if i.name == "SafetyMonitorInterface")
    assert smi.interface_type == "Client-Server"
    assert "SafetyStatus" in smi.signals


def test_extract_ports_v1_and_v2(extractor):
    """Verify port extraction returns exact port lists and detects added ports."""
    v1_ports = extractor.extract_ports(version="1.0")
    v2_ports = extractor.extract_ports(version="2.0")

    assert len(v1_ports) == 6
    assert len(v2_ports) == 8

    v1_port_names = {p.name for p in v1_ports}
    v2_port_names = {p.name for p in v2_ports}

    assert "SafetyStatusIn" not in v1_port_names
    assert "SafetyStatusIn" in v2_port_names
    assert "SafetyStatusOut" in v2_port_names

    # Check component filter
    vc_ports = extractor.extract_ports(version="2.0", component="VehicleControl")
    assert len(vc_ports) == 4
    assert any(p.name == "SafetyStatusIn" and p.direction == Direction.INPUT for p in vc_ports)


def test_extract_signals_v1_and_v2(extractor):
    """Verify signal extraction detects precision upgrade and new signal addition."""
    v1_signals = extractor.extract_signals(version="1.0")
    v2_signals = extractor.extract_signals(version="2.0")

    assert len(v1_signals) == 5
    assert len(v2_signals) == 6

    # VehicleSpeed precision change: float32 in v1.0 -> float64 in v2.0
    v1_speed = next(s for s in v1_signals if s.name == "VehicleSpeed")
    v2_speed = next(s for s in v2_signals if s.name == "VehicleSpeed")
    assert v1_speed.data_type == "float32"
    assert v2_speed.data_type == "float64"

    # EngineTemperature added in v2.0
    v1_names = {s.name for s in v1_signals}
    v2_names = {s.name for s in v2_signals}
    assert "EngineTemperature" not in v1_names
    assert "EngineTemperature" in v2_names

    eng_temp = next(s for s in v2_signals if s.name == "EngineTemperature")
    assert eng_temp.data_type == "float32"
    assert eng_temp.unit == "degC"
    assert eng_temp.interface == "VehicleDataInterface"


def test_extract_dependencies_v1_and_v2(extractor):
    """Verify dependency extraction detects safety coupling in v2.0."""
    v1_deps = extractor.extract_dependencies(version="1.0")
    v2_deps = extractor.extract_dependencies(version="2.0")

    assert len(v1_deps) == 3
    assert len(v2_deps) == 4

    v1_pairs = {(d.source_component, d.target_component) for d in v1_deps}
    v2_pairs = {(d.source_component, d.target_component) for d in v2_deps}

    assert ("VehicleControl", "SafetyManager") not in v1_pairs
    assert ("VehicleControl", "SafetyManager") in v2_pairs


def test_extract_flows(extractor):
    """Verify functional flow extraction returns end-to-end sequences."""
    flows = extractor.extract_flows(version="2.0")
    assert len(flows) == 2

    flow_names = {f.name for f in flows}
    assert "Sensor Data Flow" in flow_names
    assert "Diagnostic Flow" in flow_names

    sensor_flow = next(f for f in flows if f.name == "Sensor Data Flow")
    assert "Physical sensors" in sensor_flow.steps
    assert "SensorManager" in sensor_flow.steps
    assert "VehicleDataInterface" in sensor_flow.steps
    assert "VehicleControl" in sensor_flow.steps
    assert "Actuators" in sensor_flow.steps


# ==========================================
# 3. Architecture Graph Tests
# ==========================================


def test_architecture_graph_v1(extractor):
    """Verify v1.0 architecture graph nodes and relationships."""
    graph = extractor.build_graph(version="1.0")
    assert isinstance(graph, ArchitectureGraph)
    assert graph.version == "1.0"
    assert len(graph.nodes) == 18
    assert len(graph.edges) == 24

    node_types = {n.node_type for n in graph.nodes}
    assert node_types == {"component", "interface", "port", "signal"}

    edge_rels = {e.relationship for e in graph.edges}
    assert "CONTAINS" in edge_rels
    assert "CONNECTS_TO" in edge_rels
    assert "CARRIES" in edge_rels
    assert "DEPENDS_ON" in edge_rels
    assert "PROVIDES" in edge_rels
    assert "REQUIRES" in edge_rels


def test_architecture_graph_v2(extractor):
    """Verify v2.0 architecture graph contains SafetyManager nodes and safety edges."""
    graph = extractor.build_graph(version="2.0")
    assert isinstance(graph, ArchitectureGraph)
    assert graph.version == "2.0"
    assert len(graph.nodes) == 23
    assert len(graph.edges) == 32

    node_names = {n.name for n in graph.nodes}
    assert "SafetyManager" in node_names
    assert "SafetyMonitorInterface" in node_names
    assert "SafetyStatusIn" in node_names
    assert "SafetyStatusOut" in node_names
    assert "EngineTemperature" in node_names


def test_get_complete_model(extractor):
    """Verify CompleteArchitectureModel consolidates all entities and graph."""
    model = extractor.get_complete_model("2.0")
    assert isinstance(model, CompleteArchitectureModel)
    assert model.version == "2.0"
    assert len(model.components) == 5
    assert len(model.interfaces) == 4
    assert len(model.ports) == 8
    assert len(model.signals) == 6
    assert len(model.dependencies) == 4
    assert len(model.functional_flows) == 2
    assert model.graph is not None
    assert len(model.graph.nodes) == 23


# ==========================================
# 4. Revision Diff Engine Tests (Hard 7/7 Requirement)
# ==========================================


def test_diff_engine_detects_all_7_intentional_changes(diff_engine):
    """CRITICAL HARD SUCCESS CRITERION: Verify deterministic detection of all 7 intentional modifications."""
    res = diff_engine.compare_versions(base_version="1.0", target_version="2.0")
    assert isinstance(res, RevisionDiffResult)
    assert res.base_version == "1.0"
    assert res.target_version == "2.0"
    assert res.total_changes >= 7
    assert res.all_intentional_changes_detected is True
    assert res.missing_intentional_changes == []


def test_diff_intentional_1_component_added(diff_engine):
    """Verify Intentional Change 1: Component added: SafetyManager."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "component" and c.change_type == ChangeType.ADDED and "SafetyManager" in c.entity_name
    )
    assert c.entity_name == "SafetyManager"
    assert c.severity == Severity.HIGH
    assert "ISO 26262" in c.description or "Safety Monitoring" in c.description
    assert c.source_v2 is not None


def test_diff_intentional_2_signal_precision_change(diff_engine):
    """Verify Intentional Change 2: Signal data type change: VehicleSpeed (float32 -> float64)."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "signal" and c.entity_name == "VehicleSpeed" and c.field == "data_type"
    )
    assert c.change_type == ChangeType.MODIFIED
    assert c.old_value == "float32"
    assert c.new_value == "float64"
    assert c.severity == Severity.HIGH


def test_diff_intentional_3_signal_added(diff_engine):
    """Verify Intentional Change 3: Signal added: EngineTemperature."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "signal" and c.entity_name == "EngineTemperature" and c.change_type == ChangeType.ADDED
    )
    assert c.new_value == "float32"
    assert "VehicleDataInterface" in c.description


def test_diff_intentional_4_port_added(diff_engine):
    """Verify Intentional Change 4: Port added: SafetyStatusIn on VehicleControl."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "port" and c.entity_name == "SafetyStatusIn" and c.change_type == ChangeType.ADDED
    )
    assert c.new_value == "VehicleControl"
    assert c.severity == Severity.HIGH


def test_diff_intentional_5_interface_added(diff_engine):
    """Verify Intentional Change 5: Interface added: SafetyMonitorInterface (Client-Server)."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "interface" and c.entity_name == "SafetyMonitorInterface" and c.change_type == ChangeType.ADDED
    )
    assert c.new_value == "Client-Server"
    assert c.severity == Severity.HIGH


def test_diff_intentional_6_interface_renamed(diff_engine):
    """Verify Intentional Change 6: Interface renamed: CommunicationInterface -> V2XCommunicationInterface."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "interface" and c.change_type == ChangeType.RENAMED
    )
    assert c.old_value == "CommunicationInterface"
    assert c.new_value == "V2XCommunicationInterface"
    assert "renamed" in c.description.lower()


def test_diff_intentional_7_dependency_added(diff_engine):
    """Verify Intentional Change 7: Dependency added: VehicleControl -> SafetyManager."""
    res = diff_engine.compare_versions("1.0", "2.0")
    c = next(
        c for c in res.changes
        if c.entity_type == "dependency" and c.change_type == ChangeType.ADDED and "SafetyManager" in c.entity_name
    )
    assert "VehicleControl" in c.entity_name
    assert "SafetyManager" in c.entity_name
    assert c.severity == Severity.HIGH


# ==========================================
# 5. Impact Analysis Engine Tests
# ==========================================


def test_impact_analysis_single_signal_precision_change(impact_analyzer, diff_engine):
    """Verify downstream propagation of VehicleSpeed precision modification."""
    diff_res = diff_engine.compare_versions("1.0", "2.0")
    speed_change = next(
        c for c in diff_res.changes
        if c.entity_type == "signal" and c.entity_name == "VehicleSpeed" and c.field == "data_type"
    )

    analysis = impact_analyzer.analyze_change(change=speed_change, target_version="2.0")
    assert "VehicleDataInterface" in analysis.affected_interfaces
    assert "VehicleControl" in analysis.affected_components
    assert "SensorManager" in analysis.affected_components
    assert "Sensor Data Flow" in analysis.affected_flows
    assert "VehicleSpeedIn" in analysis.affected_ports
    assert "64-bit alignment in RTE buffer" in analysis.risk_assessment


def test_impact_analysis_single_component_addition(impact_analyzer, diff_engine):
    """Verify downstream coupling propagation of SafetyManager addition."""
    diff_res = diff_engine.compare_versions("1.0", "2.0")
    safety_change = next(
        c for c in diff_res.changes
        if c.entity_type == "component" and c.entity_name == "SafetyManager"
    )

    analysis = impact_analyzer.analyze_change(change=safety_change, target_version="2.0")
    assert "SafetyManager" in analysis.affected_components
    assert "VehicleControl" in analysis.affected_components
    assert "SafetyStatusOut" in analysis.affected_ports
    assert "ISO 26262" in analysis.risk_assessment


def test_impact_comprehensive_report(impact_analyzer):
    """Verify comprehensive impact report analyzes all changes and produces summaries."""
    report = impact_analyzer.generate_comprehensive_report("1.0", "2.0")
    assert report.base_version == "1.0"
    assert report.target_version == "2.0"
    assert report.changes_analyzed >= 7
    assert report.total_impacts > 20
    assert "VehicleControl" in report.summary["unique_affected_components"]
    assert "SafetyManager" in report.summary["unique_affected_components"]
    assert report.summary["all_intentional_changes_detected"] is True


# ==========================================
# 6. Phase 3 FastAPI Endpoints Tests
# ==========================================


def test_api_architecture_summary(client):
    """Verify GET /architecture returns versions overview."""
    res = client.get("/architecture")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "1.0" in data["versions"]
    assert "2.0" in data["versions"]
    assert data["versions"]["2.0"]["components_count"] == 5


def test_api_architecture_components(client):
    """Verify GET /architecture/components returns SWCs with provenance."""
    res = client.get("/architecture/components?version=2.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 5
    assert any(c["name"] == "SafetyManager" for c in data)


def test_api_architecture_interfaces(client):
    """Verify GET /architecture/interfaces returns interfaces."""
    res = client.get("/architecture/interfaces?version=2.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert any(i["name"] == "V2XCommunicationInterface" for i in data)
    assert any(i["name"] == "SafetyMonitorInterface" for i in data)


def test_api_architecture_ports(client):
    """Verify GET /architecture/ports returns ports with component filter."""
    res = client.get("/architecture/ports?version=2.0&component=VehicleControl")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert any(p["name"] == "SafetyStatusIn" for p in data)


def test_api_architecture_signals(client):
    """Verify GET /architecture/signals returns signals with interface filter."""
    res = client.get("/architecture/signals?version=2.0&interface=VehicleDataInterface")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    names = {s["name"] for s in data}
    assert "VehicleSpeed" in names
    assert "EngineRPM" in names
    assert "EngineTemperature" in names


def test_api_architecture_dependencies(client):
    """Verify GET /architecture/dependencies returns dependencies."""
    res = client.get("/architecture/dependencies?version=2.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert any(d["source_component"] == "VehicleControl" and d["target_component"] == "SafetyManager" for d in data)


def test_api_architecture_flows(client):
    """Verify GET /architecture/flows returns functional flows."""
    res = client.get("/architecture/flows?version=2.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_api_architecture_graph(client):
    """Verify GET /architecture/graph returns complete graph."""
    res = client.get("/architecture/graph?version=2.0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["nodes"]) == 23
    assert len(data["edges"]) == 32


def test_api_architecture_diff_intentional_verification(client):
    """Verify GET /architecture/diff returns 7/7 intentional changes detected."""
    res = client.get("/architecture/diff?v1=1.0&v2=2.0")
    assert res.status_code == 200
    data = res.json()
    assert data["all_intentional_changes_detected"] is True
    assert data["missing_intentional_changes"] == []
    assert data["total_changes"] >= 7


def test_api_architecture_impact(client):
    """Verify GET /architecture/impact returns comprehensive impact report."""
    res = client.get("/architecture/impact?v1=1.0&v2=2.0")
    assert res.status_code == 200
    data = res.json()
    assert data["total_impacts"] > 20
    assert data["changes_analyzed"] >= 7
    assert data["summary"]["all_intentional_changes_detected"] is True
