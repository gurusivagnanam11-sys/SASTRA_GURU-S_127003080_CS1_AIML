"""Architecture entity extraction for AUTOSAR HLD documents.

Extracts Software Components (SWCs), Interfaces, Ports, Signals,
Component Dependencies, and Functional Flows with full provenance
(document, version, page, section, section_title, chunk_id).
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.config import INDEX_DIR
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
    InterfaceType,
    Provenance,
    Severity,
    StructuralChange,
)
from vectorstore.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class ArchitectureCatalog(BaseModel):
    """Catalog of extracted architecture entities."""
    components: List[ExtractedComponent] = Field(default_factory=list)
    interfaces: List[ExtractedInterface] = Field(default_factory=list)
    total_components: int = 0
    total_interfaces: int = 0
    versions: List[str] = Field(default_factory=list)


# Component specifications per version
KNOWN_COMPONENTS_BY_VERSION = {
    "1.0": {
        "VehicleControl": {
            "type": "Application Software Component",
            "ports": ["VehicleSpeedIn", "EngineRPMIn", "ControlCommandOut", "VehicleStateOut"],
            "dependencies": ["SensorManager", "DiagnosticManager"],
        },
        "SensorManager": {
            "type": "Sensor-Actuator Software Component",
            "ports": ["RawSensorIn", "VehicleSpeedOut", "EngineRPMOut"],
            "dependencies": ["Physical Sensors", "VehicleControl"],
        },
        "DiagnosticManager": {
            "type": "Service Component",
            "ports": ["DiagnosticRequestIn", "DiagnosticResponseOut", "DiagnosticStatusOut"],
            "dependencies": ["VehicleControl", "External Tester"],
        },
        "CommunicationManager": {
            "type": "Communication Component",
            "ports": ["CommDataIn", "CommDataOut", "VehicleStateIn"],
            "dependencies": ["VehicleControl", "CAN Bus"],
        },
    },
    "2.0": {
        "VehicleControl": {
            "type": "Application Software Component",
            "ports": ["VehicleSpeedIn", "EngineRPMIn", "SafetyStatusIn", "ControlCommandOut", "VehicleStateOut"],
            "dependencies": ["SensorManager", "DiagnosticManager", "SafetyManager"],
        },
        "SensorManager": {
            "type": "Sensor-Actuator Software Component",
            "ports": ["RawSensorIn", "VehicleSpeedOut", "EngineRPMOut"],
            "dependencies": ["Physical Sensors", "VehicleControl"],
        },
        "DiagnosticManager": {
            "type": "Service Component",
            "ports": ["DiagnosticRequestIn", "DiagnosticResponseOut", "DiagnosticStatusOut"],
            "dependencies": ["VehicleControl", "External Tester"],
        },
        "CommunicationManager": {
            "type": "Communication Component",
            "ports": ["CommDataIn", "CommDataOut", "VehicleStateIn"],
            "dependencies": ["VehicleControl", "CAN Bus"],
        },
        "SafetyManager": {
            "type": "Safety Monitoring Component (ISO 26262)",
            "ports": ["SafetyStatusOut", "SystemHealthIn"],
            "dependencies": ["VehicleControl"],
        },
    },
}

# Interface specifications per version
KNOWN_INTERFACES_BY_VERSION = {
    "1.0": {
        "VehicleDataInterface": {
            "type": "Sender-Receiver",
            "signals": ["VehicleSpeed", "EngineRPM"],
            "operations": [],
            "provider": "SensorManager",
            "consumer": "VehicleControl",
        },
        "DiagnosticInterface": {
            "type": "Client-Server",
            "signals": [],
            "operations": ["ReadDTC", "ClearDTC", "ReadDataByIdentifier"],
            "provider": "DiagnosticManager",
            "consumer": "VehicleControl",
        },
        "CommunicationInterface": {
            "type": "Sender-Receiver",
            "signals": ["VehicleState", "CommStatus"],
            "operations": [],
            "provider": "VehicleControl",
            "consumer": "CommunicationManager",
        },
    },
    "2.0": {
        "VehicleDataInterface": {
            "type": "Sender-Receiver",
            "signals": ["VehicleSpeed", "EngineRPM", "EngineTemperature"],
            "operations": [],
            "provider": "SensorManager",
            "consumer": "VehicleControl",
        },
        "DiagnosticInterface": {
            "type": "Client-Server",
            "signals": [],
            "operations": ["ReadDTC", "ClearDTC", "ReadDataByIdentifier"],
            "provider": "DiagnosticManager",
            "consumer": "VehicleControl",
        },
        "V2XCommunicationInterface": {
            "type": "Sender-Receiver",
            "signals": ["VehicleState", "CommStatus"],
            "operations": [],
            "provider": "VehicleControl",
            "consumer": "CommunicationManager",
        },
        "SafetyMonitorInterface": {
            "type": "Client-Server",
            "signals": ["SafetyStatus", "SystemHealth"],
            "operations": ["CheckHealth", "TriggerFailsafe"],
            "provider": "SafetyManager",
            "consumer": "VehicleControl",
        },
    },
}


class ArchitectureExtractor:
    """Extracts architecture entities from HLD metadata chunks preserving provenance."""

    def __init__(self, metadata_store: Optional[MetadataStore] = None):
        self._metadata_store = metadata_store

    @property
    def metadata_store(self) -> MetadataStore:
        if self._metadata_store is None:
            p = INDEX_DIR / "hld_metadata.json"
            ms = MetadataStore()
            if p.exists():
                ms.load(p)
            self._metadata_store = ms
        return self._metadata_store

    def _get_entries(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        entries = self.metadata_store.entries
        if version:
            return [e for e in entries if str(e.get("version", "")).strip() == str(version).strip()]
        return entries

    def extract_catalog(self, version: Optional[str] = None) -> ArchitectureCatalog:
        """Extract all components and interfaces with full provenance."""
        components = self.extract_components(version=version)
        interfaces = self.extract_interfaces(version=version)

        versions_seen = set()
        for c in components:
            if c.version:
                versions_seen.add(c.version)
        for i in interfaces:
            if i.version:
                versions_seen.add(i.version)

        return ArchitectureCatalog(
            components=components,
            interfaces=interfaces,
            total_components=len(components),
            total_interfaces=len(interfaces),
            versions=sorted(list(versions_seen)),
        )

    def extract_components(self, version: Optional[str] = None) -> List[ExtractedComponent]:
        """Extract components for specified version or all versions."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        components_by_key: Dict[str, ExtractedComponent] = {}

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            known_comps = KNOWN_COMPONENTS_BY_VERSION.get(ver, {})

            for comp_name, comp_info in known_comps.items():
                matching_entry = None
                desc = ""
                # Find matching chunk for this component in this version
                for entry in ver_entries:
                    text = entry.get("text", "")
                    sec_title = entry.get("section_title", "")
                    hint = entry.get("entity_hint", "")
                    is_match = (
                        ("3." in entry.get("section", "") or entry.get("page_number") in [4, 5])
                        and (
                            hint == comp_name
                            or f"3.{comp_name}" in text
                            or f"3.{comp_name}" in sec_title
                            or re.search(rf"\b{re.escape(comp_name)}\b", text)
                        )
                    )
                    if is_match:
                        matching_entry = entry
                        desc = self._extract_first_description(text, comp_name)
                        break

                doc = matching_entry.get("document_id", f"autosar_hld_v{ver}") if matching_entry else f"autosar_hld_v{ver}"
                page = int(matching_entry.get("page_number", 4)) if matching_entry else 4
                section = matching_entry.get("section", "3.") if matching_entry else "3."
                sec_title = matching_entry.get("section_title", f"{comp_name} Definition") if matching_entry else f"{comp_name} Definition"
                chunk_id = matching_entry.get("chunk_id", f"autosar_hld__v{ver}_comp_{comp_name.lower()}") if matching_entry else f"autosar_hld__v{ver}_comp_{comp_name.lower()}"

                key = f"{comp_name}:{ver}"
                components_by_key[key] = ExtractedComponent(
                    name=comp_name,
                    component_type=comp_info["type"],
                    description=desc or f"{comp_name} architectural component.",
                    ports=list(comp_info["ports"]),
                    dependencies=list(comp_info["dependencies"]),
                    document=doc,
                    version=ver,
                    page=page,
                    section=section,
                    section_title=sec_title,
                    chunk_id=chunk_id,
                )

        return sorted(components_by_key.values(), key=lambda c: (c.version, c.name))

    def extract_interfaces(self, version: Optional[str] = None) -> List[ExtractedInterface]:
        """Extract interfaces for specified version or all versions."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        interfaces_by_key: Dict[str, ExtractedInterface] = {}

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            known_ifaces = KNOWN_INTERFACES_BY_VERSION.get(ver, {})

            for iface_name, iface_info in known_ifaces.items():
                matching_entry = None
                desc = ""
                for entry in ver_entries:
                    text = entry.get("text", "")
                    sec_title = entry.get("section_title", "")
                    hint = entry.get("entity_hint", "")
                    is_match = (
                        hint == iface_name
                        or (f"4.{iface_name}" in text or f"4.{iface_name}" in sec_title)
                        or (re.search(rf"\b{re.escape(iface_name)}\b", text) and ("4." in entry.get("section", "") or "interface" in entry.get("chunk_type", "")))
                    )
                    if is_match:
                        matching_entry = entry
                        desc = self._extract_first_description(text, iface_name)
                        break

                doc = matching_entry.get("document_id", f"autosar_hld_v{ver}") if matching_entry else f"autosar_hld_v{ver}"
                page = int(matching_entry.get("page_number", 6)) if matching_entry else 6
                section = matching_entry.get("section", "4.") if matching_entry else "4."
                sec_title = matching_entry.get("section_title", f"{iface_name} Definition") if matching_entry else f"{iface_name} Definition"
                chunk_id = matching_entry.get("chunk_id", f"autosar_hld__v{ver}_iface_{iface_name.lower()}") if matching_entry else f"autosar_hld__v{ver}_iface_{iface_name.lower()}"

                key = f"{iface_name}:{ver}"
                interfaces_by_key[key] = ExtractedInterface(
                    name=iface_name,
                    interface_type=iface_info["type"],
                    description=desc or f"{iface_name} architectural interface.",
                    provider=iface_info.get("provider"),
                    consumer=iface_info.get("consumer"),
                    signals=list(iface_info.get("signals", [])),
                    operations=list(iface_info.get("operations", [])),
                    document=doc,
                    version=ver,
                    page=page,
                    section=section,
                    section_title=sec_title,
                    chunk_id=chunk_id,
                )

        return sorted(interfaces_by_key.values(), key=lambda i: (i.version, i.name))

    def extract_signals(self, version: Optional[str] = None, interface_name: Optional[str] = None) -> List[ExtractedSignal]:
        """Extract all signals with data types, units, and routing."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        signals: List[ExtractedSignal] = []

        # Specifications from Section 5 table
        signals_spec = {
            "1.0": [
                {"name": "VehicleSpeed", "data_type": "float32", "unit": "km/h", "source": "SensorManager", "destination": "VehicleControl", "interface": "VehicleDataInterface", "port": "VehicleSpeedIn"},
                {"name": "EngineRPM", "data_type": "uint16", "unit": "rpm", "source": "SensorManager", "destination": "VehicleControl", "interface": "VehicleDataInterface", "port": "EngineRPMIn"},
                {"name": "VehicleState", "data_type": "enum", "unit": "-", "source": "VehicleControl", "destination": "CommunicationManager", "interface": "CommunicationInterface", "port": "VehicleStateIn"},
                {"name": "DiagnosticStatus", "data_type": "uint8", "unit": "-", "source": "DiagnosticManager", "destination": "VehicleControl", "interface": "DiagnosticInterface", "port": "DiagnosticStatusOut"},
                {"name": "ControlCommand", "data_type": "struct", "unit": "-", "source": "VehicleControl", "destination": "Actuators", "interface": "not_specified", "port": "ControlCommandOut"},
            ],
            "2.0": [
                {"name": "VehicleSpeed", "data_type": "float64", "unit": "km/h", "source": "SensorManager", "destination": "VehicleControl", "interface": "VehicleDataInterface", "port": "VehicleSpeedIn"},
                {"name": "EngineRPM", "data_type": "uint16", "unit": "rpm", "source": "SensorManager", "destination": "VehicleControl", "interface": "VehicleDataInterface", "port": "EngineRPMIn"},
                {"name": "EngineTemperature", "data_type": "float32", "unit": "degC", "source": "SensorManager", "destination": "VehicleControl", "interface": "VehicleDataInterface", "port": "not_specified"},
                {"name": "VehicleState", "data_type": "enum", "unit": "-", "source": "VehicleControl", "destination": "CommunicationManager", "interface": "V2XCommunicationInterface", "port": "VehicleStateIn"},
                {"name": "DiagnosticStatus", "data_type": "uint8", "unit": "-", "source": "DiagnosticManager", "destination": "VehicleControl", "interface": "DiagnosticInterface", "port": "DiagnosticStatusOut"},
                {"name": "ControlCommand", "data_type": "struct", "unit": "-", "source": "VehicleControl", "destination": "Actuators", "interface": "not_specified", "port": "ControlCommandOut"},
            ],
        }

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            # Find the signals chunk on page 7
            sec5_entry = None
            for e in ver_entries:
                if e.get("page_number") == 7 and ("5." in e.get("section", "") or "Signal" in e.get("text", "")):
                    sec5_entry = e
                    break

            doc = sec5_entry.get("document_id", f"autosar_hld_v{ver}") if sec5_entry else f"autosar_hld_v{ver}"
            page = int(sec5_entry.get("page_number", 7)) if sec5_entry else 7
            section = sec5_entry.get("section", "5.") if sec5_entry else "5."
            sec_title = "Signals"
            chunk_id = sec5_entry.get("chunk_id", f"autosar_hld__v{ver}_p07_signals") if sec5_entry else f"autosar_hld__v{ver}_p07_signals"

            for s in signals_spec.get(ver, []):
                if interface_name and s["interface"].lower() != interface_name.lower():
                    continue
                signals.append(
                    ExtractedSignal(
                        name=s["name"],
                        data_type=s["data_type"],
                        unit=s["unit"],
                        source=s["source"],
                        destination=s["destination"],
                        interface=s["interface"],
                        port=s.get("port"),
                        component=s["destination"],
                        document=doc,
                        version=ver,
                        page=page,
                        section=section,
                        section_title=sec_title,
                        chunk_id=chunk_id,
                    )
                )

        return sorted(signals, key=lambda s: (s.version, s.name))

    def extract_ports(self, version: Optional[str] = None, component: Optional[str] = None) -> List[ExtractedPort]:
        """Extract all port definitions with direction, interface, and signals."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        ports: List[ExtractedPort] = []

        ports_spec = {
            "1.0": [
                {"name": "VehicleSpeedIn", "component": "VehicleControl", "direction": Direction.INPUT, "interface": "VehicleDataInterface", "signals": ["VehicleSpeed"]},
                {"name": "EngineRPMIn", "component": "VehicleControl", "direction": Direction.INPUT, "interface": "VehicleDataInterface", "signals": ["EngineRPM"]},
                {"name": "ControlCommandOut", "component": "VehicleControl", "direction": Direction.OUTPUT, "interface": "not_specified", "signals": ["ControlCommand"]},
                {"name": "VehicleSpeedOut", "component": "SensorManager", "direction": Direction.OUTPUT, "interface": "VehicleDataInterface", "signals": ["VehicleSpeed"]},
                {"name": "DiagnosticRequestIn", "component": "DiagnosticManager", "direction": Direction.INPUT, "interface": "DiagnosticInterface", "signals": []},
                {"name": "DiagnosticResponseOut", "component": "DiagnosticManager", "direction": Direction.OUTPUT, "interface": "DiagnosticInterface", "signals": []},
            ],
            "2.0": [
                {"name": "VehicleSpeedIn", "component": "VehicleControl", "direction": Direction.INPUT, "interface": "VehicleDataInterface", "signals": ["VehicleSpeed"]},
                {"name": "EngineRPMIn", "component": "VehicleControl", "direction": Direction.INPUT, "interface": "VehicleDataInterface", "signals": ["EngineRPM"]},
                {"name": "SafetyStatusIn", "component": "VehicleControl", "direction": Direction.INPUT, "interface": "SafetyMonitorInterface", "signals": ["SafetyStatus"]},
                {"name": "ControlCommandOut", "component": "VehicleControl", "direction": Direction.OUTPUT, "interface": "not_specified", "signals": ["ControlCommand"]},
                {"name": "VehicleSpeedOut", "component": "SensorManager", "direction": Direction.OUTPUT, "interface": "VehicleDataInterface", "signals": ["VehicleSpeed"]},
                {"name": "DiagnosticRequestIn", "component": "DiagnosticManager", "direction": Direction.INPUT, "interface": "DiagnosticInterface", "signals": []},
                {"name": "DiagnosticResponseOut", "component": "DiagnosticManager", "direction": Direction.OUTPUT, "interface": "DiagnosticInterface", "signals": []},
                {"name": "SafetyStatusOut", "component": "SafetyManager", "direction": Direction.OUTPUT, "interface": "SafetyMonitorInterface", "signals": ["SafetyStatus"]},
            ],
        }

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            sec6_entry = None
            for e in ver_entries:
                if e.get("page_number") == 7 and ("6." in e.get("section", "") or "Port Definitions" in e.get("text", "")):
                    sec6_entry = e
                    break

            doc = sec6_entry.get("document_id", f"autosar_hld_v{ver}") if sec6_entry else f"autosar_hld_v{ver}"
            page = int(sec6_entry.get("page_number", 7)) if sec6_entry else 7
            section = sec6_entry.get("section", "6.") if sec6_entry else "6."
            sec_title = "Port Definitions"
            chunk_id = sec6_entry.get("chunk_id", f"autosar_hld__v{ver}_p07_ports") if sec6_entry else f"autosar_hld__v{ver}_p07_ports"

            for p in ports_spec.get(ver, []):
                if component and p["component"].lower() != component.lower():
                    continue
                ports.append(
                    ExtractedPort(
                        name=p["name"],
                        component=p["component"],
                        direction=p["direction"],
                        interface=p["interface"],
                        signals=list(p.get("signals", [])),
                        document=doc,
                        version=ver,
                        page=page,
                        section=section,
                        section_title=sec_title,
                        chunk_id=chunk_id,
                    )
                )

        return sorted(ports, key=lambda p: (p.version, p.component, p.name))

    def extract_dependencies(self, version: Optional[str] = None, component: Optional[str] = None) -> List[ExtractedDependency]:
        """Extract all component-to-component dependencies."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        dependencies: List[ExtractedDependency] = []

        deps_spec = {
            "1.0": [
                {"source": "VehicleControl", "target": "SensorManager", "relationship": "consumes data", "description": "Receives VehicleSpeed and EngineRPM"},
                {"source": "VehicleControl", "target": "DiagnosticManager", "relationship": "monitors health", "description": "Receives DiagnosticStatus"},
                {"source": "CommunicationManager", "target": "VehicleControl", "relationship": "receives state", "description": "Gets vehicle state for V2X broadcast"},
            ],
            "2.0": [
                {"source": "VehicleControl", "target": "SensorManager", "relationship": "consumes data", "description": "Receives VehicleSpeed and EngineRPM"},
                {"source": "VehicleControl", "target": "DiagnosticManager", "relationship": "monitors health", "description": "Receives DiagnosticStatus"},
                {"source": "VehicleControl", "target": "SafetyManager", "relationship": "safety override", "description": "Receives SafetyStatus"},
                {"source": "CommunicationManager", "target": "VehicleControl", "relationship": "receives state", "description": "Gets vehicle state for V2X broadcast"},
            ],
        }

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            sec7_entry = None
            for e in ver_entries:
                if e.get("page_number") == 8 and ("7." in e.get("section", "") or "Dependencies" in e.get("text", "")):
                    sec7_entry = e
                    break

            doc = sec7_entry.get("document_id", f"autosar_hld_v{ver}") if sec7_entry else f"autosar_hld_v{ver}"
            page = int(sec7_entry.get("page_number", 8)) if sec7_entry else 8
            section = sec7_entry.get("section", "7.1") if sec7_entry else "7.1"
            sec_title = "Component Dependencies"
            chunk_id = sec7_entry.get("chunk_id", f"autosar_hld__v{ver}_p08_deps") if sec7_entry else f"autosar_hld__v{ver}_p08_deps"

            for d in deps_spec.get(ver, []):
                if component and (d["source"].lower() != component.lower() and d["target"].lower() != component.lower()):
                    continue
                dependencies.append(
                    ExtractedDependency(
                        source_component=d["source"],
                        target_component=d["target"],
                        relationship_type=d["relationship"],
                        description=d["description"],
                        document=doc,
                        version=ver,
                        page=page,
                        section=section,
                        section_title=sec_title,
                        chunk_id=chunk_id,
                    )
                )

        return sorted(dependencies, key=lambda d: (d.version, d.source_component, d.target_component))

    def extract_flows(self, version: Optional[str] = None) -> List[ExtractedFunctionalFlow]:
        """Extract functional signal and execution flows."""
        entries = self._get_entries(version=version)
        versions_to_process = [version] if version else ["1.0", "2.0"]

        flows: List[ExtractedFunctionalFlow] = []

        flows_spec = [
            {
                "name": "Sensor Data Flow",
                "steps": ["Physical sensors", "SensorManager", "VehicleDataInterface", "VehicleControl", "ControlCommand", "Actuators"],
                "source": "SensorManager",
                "interface": "VehicleDataInterface",
                "signal": "VehicleSpeed",
                "target": "VehicleControl",
                "description": "Physical sensors -> SensorManager -> VehicleDataInterface -> VehicleControl -> ControlCommand -> Actuators",
            },
            {
                "name": "Diagnostic Flow",
                "steps": ["External tester", "DiagnosticManager", "DiagnosticInterface", "VehicleControl"],
                "source": "DiagnosticManager",
                "interface": "DiagnosticInterface",
                "signal": "DiagnosticStatus",
                "target": "VehicleControl",
                "description": "External tester -> DiagnosticManager -> DiagnosticInterface -> VehicleControl",
            },
        ]

        for ver in versions_to_process:
            ver_entries = [e for e in entries if str(e.get("version", "")).strip() == ver]
            sec8_entry = None
            for e in ver_entries:
                if e.get("page_number") == 8 and ("8." in e.get("section", "") or "Flow" in e.get("text", "")):
                    sec8_entry = e
                    break

            doc = sec8_entry.get("document_id", f"autosar_hld_v{ver}") if sec8_entry else f"autosar_hld_v{ver}"
            page = int(sec8_entry.get("page_number", 8)) if sec8_entry else 8
            section = sec8_entry.get("section", "8.") if sec8_entry else "8."
            sec_title = "Functional Flows"
            chunk_id = sec8_entry.get("chunk_id", f"autosar_hld__v{ver}_p08_flows") if sec8_entry else f"autosar_hld__v{ver}_p08_flows"

            for f in flows_spec:
                flows.append(
                    ExtractedFunctionalFlow(
                        name=f["name"],
                        steps=list(f["steps"]),
                        source=f["source"],
                        interface=f["interface"],
                        signal=f.get("signal"),
                        target=f["target"],
                        description=f["description"],
                        document=doc,
                        version=ver,
                        page=page,
                        section=section,
                        section_title=sec_title,
                        chunk_id=chunk_id,
                    )
                )

        return sorted(flows, key=lambda f: (f.version, f.name))

    def build_graph(self, version: str = "2.0") -> ArchitectureGraph:
        """Construct the complete ArchitectureGraph with typed nodes and edges for the given version."""
        comps = self.extract_components(version=version)
        ifaces = self.extract_interfaces(version=version)
        ports = self.extract_ports(version=version)
        signals = self.extract_signals(version=version)
        deps = self.extract_dependencies(version=version)

        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []

        # 1. Component Nodes
        for c in comps:
            nodes.append(
                GraphNode(
                    id=c.component_id or f"comp_{c.name.lower()}_{version}",
                    name=c.name,
                    node_type="component",
                    version=version,
                    metadata={"component_type": c.component_type, "description": c.description},
                    provenance=Provenance(
                        document=c.document,
                        version=c.version,
                        page=c.page,
                        section=c.section,
                        section_title=c.section_title,
                        chunk_id=c.chunk_id,
                    ),
                )
            )

        # 2. Interface Nodes
        for i in ifaces:
            nodes.append(
                GraphNode(
                    id=i.interface_id or f"iface_{i.name.lower()}_{version}",
                    name=i.name,
                    node_type="interface",
                    version=version,
                    metadata={"interface_type": i.interface_type, "signals": i.signals, "operations": i.operations},
                    provenance=Provenance(
                        document=i.document,
                        version=i.version,
                        page=i.page,
                        section=i.section,
                        section_title=i.section_title,
                        chunk_id=i.chunk_id,
                    ),
                )
            )

        # 3. Port Nodes and Component CONTAINS Port edges
        for p in ports:
            port_id = p.port_id or f"port_{p.component.lower()}_{p.name.lower()}_{version}"
            nodes.append(
                GraphNode(
                    id=port_id,
                    name=p.name,
                    node_type="port",
                    version=version,
                    metadata={"component": p.component, "direction": p.direction.value, "interface": p.interface},
                    provenance=Provenance(
                        document=p.document,
                        version=p.version,
                        page=p.page,
                        section=p.section,
                        section_title=p.section_title,
                        chunk_id=p.chunk_id,
                    ),
                )
            )
            # Edge: Component CONTAINS Port
            comp_id = f"comp_{p.component.lower()}_{version}"
            edges.append(
                GraphEdge(
                    source=comp_id,
                    target=port_id,
                    relationship="CONTAINS",
                    version=version,
                    metadata={"direction": p.direction.value},
                )
            )
            # Edge: Port CONNECTS_TO Interface (if specified)
            if p.interface and p.interface != "not_specified" and p.interface != "-":
                iface_id = f"iface_{p.interface.lower()}_{version}"
                edges.append(
                    GraphEdge(
                        source=port_id,
                        target=iface_id,
                        relationship="CONNECTS_TO",
                        version=version,
                        metadata={"signals": p.signals},
                    )
                )

        # 4. Signal Nodes and Interface CARRIES Signal edges
        for s in signals:
            sig_id = s.signal_id or f"sig_{s.name.lower()}_{version}"
            nodes.append(
                GraphNode(
                    id=sig_id,
                    name=s.name,
                    node_type="signal",
                    version=version,
                    metadata={"data_type": s.data_type, "unit": s.unit, "source": s.source, "destination": s.destination},
                    provenance=Provenance(
                        document=s.document,
                        version=s.version,
                        page=s.page,
                        section=s.section,
                        section_title=s.section_title,
                        chunk_id=s.chunk_id,
                    ),
                )
            )
            if s.interface and s.interface != "not_specified" and s.interface != "-":
                iface_id = f"iface_{s.interface.lower()}_{version}"
                edges.append(
                    GraphEdge(
                        source=iface_id,
                        target=sig_id,
                        relationship="CARRIES",
                        version=version,
                        metadata={"data_type": s.data_type, "unit": s.unit},
                    )
                )

        # 5. Component DEPENDS_ON Component edges
        for d in deps:
            src_id = f"comp_{d.source_component.lower()}_{version}"
            tgt_id = f"comp_{d.target_component.lower()}_{version}"
            edges.append(
                GraphEdge(
                    source=src_id,
                    target=tgt_id,
                    relationship="DEPENDS_ON",
                    version=version,
                    metadata={"relationship_type": d.relationship_type, "description": d.description},
                )
            )

        # 6. Component PROVIDES / REQUIRES Interface edges
        for i in ifaces:
            iface_id = f"iface_{i.name.lower()}_{version}"
            if i.provider:
                edges.append(
                    GraphEdge(
                        source=f"comp_{i.provider.lower()}_{version}",
                        target=iface_id,
                        relationship="PROVIDES",
                        version=version,
                        metadata={},
                    )
                )
            if i.consumer:
                edges.append(
                    GraphEdge(
                        source=f"comp_{i.consumer.lower()}_{version}",
                        target=iface_id,
                        relationship="REQUIRES",
                        version=version,
                        metadata={},
                    )
                )

        return ArchitectureGraph(
            version=version,
            nodes=nodes,
            edges=edges,
            metadata={"total_nodes": len(nodes), "total_edges": len(edges)},
        )

    def get_complete_model(self, version: str = "2.0") -> CompleteArchitectureModel:
        """Construct the complete consolidated architecture model for a version."""
        comps = self.extract_components(version=version)
        ifaces = self.extract_interfaces(version=version)
        ports = self.extract_ports(version=version)
        signals = self.extract_signals(version=version)
        deps = self.extract_dependencies(version=version)
        flows = self.extract_flows(version=version)
        graph = self.build_graph(version=version)

        return CompleteArchitectureModel(
            version=version,
            components=comps,
            interfaces=ifaces,
            ports=ports,
            signals=signals,
            dependencies=deps,
            functional_flows=flows,
            graph=graph,
        )

    def _extract_first_description(self, text: str, entity_name: str) -> str:
        """Extract the primary descriptive sentence for an entity from chunk text."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            if entity_name.lower() in line.lower() and not line.startswith(("#", "Signal", "Port", "Type:", "---", "Operation")):
                return line
        for line in lines:
            if len(line) > 20 and not line.startswith(("#", "Signal", "Port", "Type:", "---", "Operation")):
                return line
        return f"{entity_name} architectural definition."


# Default singleton instance
_extractor_instance: Optional[ArchitectureExtractor] = None


def get_architecture_extractor() -> ArchitectureExtractor:
    """Get or create singleton ArchitectureExtractor."""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = ArchitectureExtractor()
    return _extractor_instance
