"""Benchmark evaluation dataset for AUTOSAR HLD Intelligence & Traceability.

Contains 25 grounded architectural benchmark queries and 10 adversarial/unsupported
queries based strictly on the synthetic AUTOSAR HLD fixtures (v1.0 and v2.0).
Zero LLM-hallucinated ground truth: all expected evidence and entities are derived
directly from the verified HLD specification AST.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationQuery(BaseModel):
    """Ground truth benchmark query item for retrieval and answer evaluation."""
    id: str
    question: str
    query_type: str  # ARCHITECTURE_QUERY, REVISION_QUERY, IMPACT_QUERY, DOCUMENT_QA, UNSUPPORTED_QUERY
    expected_answer: str
    expected_entities: List[str] = Field(default_factory=list)
    expected_chunks: List[str] = Field(default_factory=list)
    expected_version: Optional[str] = None  # '1.0', '2.0', or None/both
    expected_section: Optional[str] = None
    expected_keywords: List[str] = Field(default_factory=list)
    is_unsupported: bool = False
    unsupported_topic: Optional[str] = None

    @property
    def query_id(self) -> str:
        return self.id

    @property
    def query(self) -> str:
        return self.question

    @property
    def category(self) -> str:
        return self.query_type

    @property
    def rationale(self) -> str:
        return self.unsupported_topic or self.expected_answer



# 25 Grounded HLD Architectural Benchmark Queries
BENCHMARK_QUERIES: List[EvaluationQuery] = [
    EvaluationQuery(
        id="eval_01",
        question="What interface carries VehicleSpeed?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="VehicleSpeed is carried by VehicleDataInterface between SensorManager and VehicleControl.",
        expected_entities=["VehicleDataInterface", "VehicleSpeed", "SensorManager", "VehicleControl"],
        expected_chunks=["autosar_hld__v1.0_p06_c23", "autosar_hld__v2.0_p06_c24", "autosar_hld__v1.0_p07_c27", "autosar_hld__v2.0_p07_c30"],
        expected_version=None,
        expected_section="4.1",
        expected_keywords=["VehicleDataInterface", "VehicleSpeed"],
    ),
    EvaluationQuery(
        id="eval_02",
        question="What is the datatype of VehicleSpeed in version 1.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 1.0, VehicleSpeed has data type float32 with unit km/h.",
        expected_entities=["VehicleSpeed"],
        expected_chunks=["autosar_hld__v1.0_p07_c27", "autosar_hld__v1.0_p06_c23", "autosar_hld__v1.0_p04_c17"],
        expected_version="1.0",
        expected_section="5.",
        expected_keywords=["float32", "km/h", "VehicleSpeed"],
    ),
    EvaluationQuery(
        id="eval_03",
        question="What is the datatype of VehicleSpeed in version 2.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 2.0, VehicleSpeed has data type float64 with unit km/h for increased precision.",
        expected_entities=["VehicleSpeed"],
        expected_chunks=["autosar_hld__v2.0_p07_c30", "autosar_hld__v2.0_p06_c24", "autosar_hld__v2.0_p04_c18"],
        expected_version="2.0",
        expected_section="5.",
        expected_keywords=["float64", "km/h", "VehicleSpeed"],
    ),
    EvaluationQuery(
        id="eval_04",
        question="Which component provides VehicleDataInterface?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="SensorManager provides VehicleDataInterface to broadcast vehicle sensor dynamics.",
        expected_entities=["SensorManager", "VehicleDataInterface"],
        expected_chunks=["autosar_hld__v1.0_p06_c23", "autosar_hld__v2.0_p06_c24", "autosar_hld__v1.0_p04_c17", "autosar_hld__v2.0_p04_c18"],
        expected_version=None,
        expected_section="4.1",
        expected_keywords=["SensorManager", "VehicleDataInterface", "Provider"],
    ),
    EvaluationQuery(
        id="eval_05",
        question="Which component requires VehicleDataInterface?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="VehicleControl requires (consumes) VehicleDataInterface to receive telemetry data.",
        expected_entities=["VehicleControl", "VehicleDataInterface"],
        expected_chunks=["autosar_hld__v1.0_p06_c23", "autosar_hld__v2.0_p06_c24", "autosar_hld__v1.0_p04_c16", "autosar_hld__v2.0_p04_c17"],
        expected_version=None,
        expected_section="4.1",
        expected_keywords=["VehicleControl", "VehicleDataInterface", "Consumer"],
    ),
    EvaluationQuery(
        id="eval_06",
        question="What signals are carried by VehicleDataInterface in version 1.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 1.0, VehicleDataInterface carries VehicleSpeed and EngineRPM.",
        expected_entities=["VehicleDataInterface", "VehicleSpeed", "EngineRPM"],
        expected_chunks=["autosar_hld__v1.0_p06_c23", "autosar_hld__v1.0_p07_c27"],
        expected_version="1.0",
        expected_section="4.1",
        expected_keywords=["VehicleSpeed", "EngineRPM"],
    ),
    EvaluationQuery(
        id="eval_07",
        question="What signals are carried by VehicleDataInterface in version 2.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 2.0, VehicleDataInterface carries VehicleSpeed, EngineRPM, and EngineTemperature.",
        expected_entities=["VehicleDataInterface", "VehicleSpeed", "EngineRPM", "EngineTemperature"],
        expected_chunks=["autosar_hld__v2.0_p06_c24", "autosar_hld__v2.0_p07_c30"],
        expected_version="2.0",
        expected_section="4.1",
        expected_keywords=["VehicleSpeed", "EngineRPM", "EngineTemperature"],
    ),
    EvaluationQuery(
        id="eval_08",
        question="What ports belong to VehicleControl in version 1.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 1.0, VehicleControl has input ports VehicleSpeedIn, EngineRPMIn and output ports ControlCommandOut, VehicleStateOut.",
        expected_entities=["VehicleControl", "VehicleSpeedIn", "EngineRPMIn", "ControlCommandOut"],
        expected_chunks=["autosar_hld__v1.0_p07_c28", "autosar_hld__v1.0_p04_c16"],
        expected_version="1.0",
        expected_section="6.",
        expected_keywords=["VehicleSpeedIn", "EngineRPMIn", "ControlCommandOut"],
    ),
    EvaluationQuery(
        id="eval_09",
        question="What ports belong to VehicleControl in version 2.0?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="In version 2.0, VehicleControl has input ports VehicleSpeedIn, EngineRPMIn, SafetyStatusIn and output ports ControlCommandOut, VehicleStateOut.",
        expected_entities=["VehicleControl", "VehicleSpeedIn", "EngineRPMIn", "SafetyStatusIn", "ControlCommandOut"],
        expected_chunks=["autosar_hld__v2.0_p07_c31", "autosar_hld__v2.0_p04_c17"],
        expected_version="2.0",
        expected_section="6.",
        expected_keywords=["VehicleSpeedIn", "EngineRPMIn", "SafetyStatusIn", "ControlCommandOut"],
    ),
    EvaluationQuery(
        id="eval_10",
        question="What component was added in version 2.0?",
        query_type="REVISION_QUERY",
        expected_answer="SafetyManager was added in version 2.0 for functional safety monitoring (ISO 26262 ASIL-D).",
        expected_entities=["SafetyManager"],
        expected_chunks=["autosar_hld__v2.0_p05_c22", "autosar_hld__v2.0_p03_c11", "autosar_hld__v2.0_p02_c06"],
        expected_version="2.0",
        expected_section="3.5",
        expected_keywords=["SafetyManager", "ISO 26262", "ASIL-D"],
    ),
    EvaluationQuery(
        id="eval_11",
        question="What interface was renamed between version 1.0 and version 2.0?",
        query_type="REVISION_QUERY",
        expected_answer="CommunicationInterface was renamed to V2XCommunicationInterface in version 2.0.",
        expected_entities=["CommunicationInterface", "V2XCommunicationInterface"],
        expected_chunks=["autosar_hld__v1.0_p06_c25", "autosar_hld__v2.0_p06_c27", "autosar_hld__v2.0_p05_c21"],
        expected_version=None,
        expected_section="4.3",
        expected_keywords=["CommunicationInterface", "V2XCommunicationInterface"],
    ),
    EvaluationQuery(
        id="eval_12",
        question="What dependency was added in version 2.0?",
        query_type="REVISION_QUERY",
        expected_answer="In version 2.0, VehicleControl depends on SafetyManager for safety override commands.",
        expected_entities=["VehicleControl", "SafetyManager"],
        expected_chunks=["autosar_hld__v2.0_p08_c34", "autosar_hld__v2.0_p04_c17"],
        expected_version="2.0",
        expected_section="7.1",
        expected_keywords=["VehicleControl", "SafetyManager", "safety override"],
    ),
    EvaluationQuery(
        id="eval_13",
        question="What changed in VehicleSpeed between versions?",
        query_type="REVISION_QUERY",
        expected_answer="The data type of VehicleSpeed changed from float32 in version 1.0 to float64 in version 2.0.",
        expected_entities=["VehicleSpeed"],
        expected_chunks=["autosar_hld__v1.0_p07_c27", "autosar_hld__v2.0_p07_c30"],
        expected_version=None,
        expected_section="5.",
        expected_keywords=["float32", "float64", "VehicleSpeed"],
    ),
    EvaluationQuery(
        id="eval_14",
        question="What is SafetyMonitorInterface?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="SafetyMonitorInterface is a Client-Server interface introduced in v2.0 carrying SafetyStatus and SystemHealth signals.",
        expected_entities=["SafetyMonitorInterface", "SafetyStatus", "SystemHealth"],
        expected_chunks=["autosar_hld__v2.0_p06_c28"],
        expected_version="2.0",
        expected_section="4.4",
        expected_keywords=["SafetyMonitorInterface", "Client-Server", "SafetyStatus"],
    ),
    EvaluationQuery(
        id="eval_15",
        question="Which component depends on SafetyManager?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="VehicleControl depends on SafetyManager for emergency safety override commands.",
        expected_entities=["VehicleControl", "SafetyManager"],
        expected_chunks=["autosar_hld__v2.0_p08_c34", "autosar_hld__v2.0_p04_c17"],
        expected_version="2.0",
        expected_section="7.1",
        expected_keywords=["VehicleControl", "SafetyManager", "override"],
    ),
    EvaluationQuery(
        id="eval_16",
        question="What functional flows exist in the system?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="Two functional flows exist: 8.1 Sensor Data Flow and 8.2 Diagnostic Flow.",
        expected_entities=["Sensor Data Flow", "Diagnostic Flow"],
        expected_chunks=["autosar_hld__v1.0_p08_c33", "autosar_hld__v1.0_p08_c34", "autosar_hld__v2.0_p08_c36", "autosar_hld__v2.0_p08_c37"],
        expected_version=None,
        expected_section="8.",
        expected_keywords=["Sensor Data Flow", "Diagnostic Flow"],
    ),
    EvaluationQuery(
        id="eval_17",
        question="What are the steps of the Sensor Data Flow?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="Physical sensors -> SensorManager -> VehicleDataInterface -> VehicleControl -> ControlCommand -> Actuators.",
        expected_entities=["Sensor Data Flow", "SensorManager", "VehicleDataInterface", "VehicleControl"],
        expected_chunks=["autosar_hld__v1.0_p08_c33", "autosar_hld__v2.0_p08_c36"],
        expected_version=None,
        expected_section="8.1",
        expected_keywords=["Physical sensors", "SensorManager", "VehicleDataInterface", "VehicleControl", "Actuators"],
    ),
    EvaluationQuery(
        id="eval_18",
        question="What are the steps of the Diagnostic Flow?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="External tester -> DiagnosticManager -> DiagnosticInterface -> VehicleControl.",
        expected_entities=["Diagnostic Flow", "DiagnosticManager", "DiagnosticInterface", "VehicleControl"],
        expected_chunks=["autosar_hld__v1.0_p08_c34", "autosar_hld__v2.0_p08_c37"],
        expected_version=None,
        expected_section="8.2",
        expected_keywords=["External tester", "DiagnosticManager", "DiagnosticInterface", "VehicleControl"],
    ),
    EvaluationQuery(
        id="eval_19",
        question="What is the purpose of DiagnosticManager?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="DiagnosticManager handles on-board diagnostic operations, DTC management, and diagnostic service requests.",
        expected_entities=["DiagnosticManager", "DiagnosticInterface"],
        expected_chunks=["autosar_hld__v1.0_p05_c19", "autosar_hld__v2.0_p05_c20"],
        expected_version=None,
        expected_section="3.3",
        expected_keywords=["DiagnosticManager", "DTC", "OBD"],
    ),
    EvaluationQuery(
        id="eval_20",
        question="What operations does DiagnosticInterface support?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="DiagnosticInterface supports ReadDTC, ClearDTC, and ReadDataByIdentifier operations.",
        expected_entities=["DiagnosticInterface"],
        expected_chunks=["autosar_hld__v1.0_p06_c24", "autosar_hld__v2.0_p06_c26"],
        expected_version=None,
        expected_section="4.2",
        expected_keywords=["ReadDTC", "ClearDTC", "ReadDataByIdentifier"],
    ),
    EvaluationQuery(
        id="eval_21",
        question="What components are associated with VehicleControl?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="VehicleControl is associated with SensorManager, DiagnosticManager, CommunicationManager, and in v2.0 SafetyManager.",
        expected_entities=["VehicleControl", "SensorManager", "DiagnosticManager", "SafetyManager"],
        expected_chunks=["autosar_hld__v1.0_p08_c31", "autosar_hld__v2.0_p08_c34", "autosar_hld__v1.0_p04_c16", "autosar_hld__v2.0_p04_c17"],
        expected_version=None,
        expected_section="7.1",
        expected_keywords=["VehicleControl", "SensorManager", "DiagnosticManager"],
    ),
    EvaluationQuery(
        id="eval_22",
        question="What components may be affected by VehicleSpeed changing datatype?",
        query_type="IMPACT_QUERY",
        expected_answer="Changing VehicleSpeed from float32 to float64 impacts SensorManager (producer), VehicleControl (consumer), VehicleDataInterface, and the Sensor Data Flow.",
        expected_entities=["VehicleSpeed", "SensorManager", "VehicleControl", "VehicleDataInterface"],
        expected_chunks=["autosar_hld__v2.0_p07_c30", "autosar_hld__v1.0_p07_c27", "autosar_hld__v2.0_p06_c24"],
        expected_version="2.0",
        expected_section="5.",
        expected_keywords=["SensorManager", "VehicleControl", "VehicleDataInterface"],
    ),
    EvaluationQuery(
        id="eval_23",
        question="What are the three architecture layers in the AUTOSAR overview?",
        query_type="DOCUMENT_QA",
        expected_answer="The software architecture follows a three-tier model: Application Layer (SWCs), Runtime Environment (RTE), and Basic Software (BSW).",
        expected_entities=["Application Layer", "RTE", "BSW"],
        expected_chunks=["autosar_hld__v1.0_p03_c09", "autosar_hld__v2.0_p03_c10"],
        expected_version=None,
        expected_section="2.1",
        expected_keywords=["Application Layer", "Runtime Environment", "Basic Software"],
    ),
    EvaluationQuery(
        id="eval_24",
        question="What safety standard does SafetyManager adhere to?",
        query_type="ARCHITECTURE_QUERY",
        expected_answer="SafetyManager adheres to the ISO 26262 ASIL-D functional safety standard.",
        expected_entities=["SafetyManager"],
        expected_chunks=["autosar_hld__v2.0_p05_c22", "autosar_hld__v2.0_p02_c07", "autosar_hld__v2.0_p03_c11"],
        expected_version="2.0",
        expected_section="3.5",
        expected_keywords=["ISO 26262", "ASIL-D", "SafetyManager"],
    ),
    EvaluationQuery(
        id="eval_25",
        question="What changed between version 1.0 and version 2.0?",
        query_type="REVISION_QUERY",
        expected_answer="Version 2.0 adds SafetyManager, upgrades VehicleSpeed to float64, adds EngineTemperature, adds SafetyStatusIn, adds SafetyMonitorInterface, renames CommunicationInterface to V2XCommunicationInterface, and adds VehicleControl->SafetyManager dependency.",
        expected_entities=["SafetyManager", "VehicleSpeed", "EngineTemperature", "SafetyStatusIn", "SafetyMonitorInterface", "V2XCommunicationInterface"],
        expected_chunks=["autosar_hld__v2.0_p03_c11", "autosar_hld__v2.0_p02_c06", "autosar_hld__v1.0_p03_c10"],
        expected_version=None,
        expected_section="2.2",
        expected_keywords=["SafetyManager", "version 2.0", "five primary software components"],
    ),
]


# 10 Adversarial / Unsupported Questions (Testing Hallucination & Abstention)
UNSUPPORTED_QUERIES: List[EvaluationQuery] = [
    EvaluationQuery(
        id="eval_unsupported_01",
        question="What is the CAN bus baud rate used by CommunicationManager?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="CAN baud rate",
    ),
    EvaluationQuery(
        id="eval_unsupported_02",
        question="What processor architecture or microcontroller does VehicleControl run on?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="Microcontroller / CPU",
    ),
    EvaluationQuery(
        id="eval_unsupported_03",
        question="What AUTOSAR OS release version and scheduling algorithm are configured?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="AUTOSAR OS release",
    ),
    EvaluationQuery(
        id="eval_unsupported_04",
        question="What is the flash memory size allocated for DiagnosticManager DTC storage?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="Flash memory size",
    ),
    EvaluationQuery(
        id="eval_unsupported_05",
        question="What encryption algorithm is used for V2X message authentication?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="Encryption algorithm",
    ),
    EvaluationQuery(
        id="eval_unsupported_06",
        question="What is the Ethernet MAC address and physical layer transceiver used?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="Ethernet MAC / PHY",
    ),
    EvaluationQuery(
        id="eval_unsupported_07",
        question="What MISRA C:2012 checker rule enforcement level is mandated?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="MISRA compliance rules",
    ),
    EvaluationQuery(
        id="eval_unsupported_08",
        question="What is the maximum stack depth and heap allocation for SensorManager tasks?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="Stack / Heap limits",
    ),
    EvaluationQuery(
        id="eval_unsupported_09",
        question="What is the ASIL safety rating assigned to CommunicationManager?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="CommunicationManager ASIL level",
    ),
    EvaluationQuery(
        id="eval_unsupported_10",
        question="What supply voltage and power management IC regulates the ECU hardware?",
        query_type="UNSUPPORTED_QUERY",
        expected_answer="The HLD evidence provided does not specify this.",
        is_unsupported=True,
        unsupported_topic="PMIC / Power supply voltage",
    ),
]


def get_benchmark_dataset() -> List[EvaluationQuery]:
    """Get the full set of 25 grounded architectural benchmark queries."""
    return BENCHMARK_QUERIES


def get_unsupported_dataset() -> List[EvaluationQuery]:
    """Get the 10 adversarial/unsupported queries for abstention evaluation."""
    return UNSUPPORTED_QUERIES


def get_full_evaluation_dataset() -> List[EvaluationQuery]:
    """Get all 35 queries (25 grounded + 10 unsupported)."""
    return BENCHMARK_QUERIES + UNSUPPORTED_QUERIES


# Export aliases for evaluation harness
BENCHMARK_DATASET = BENCHMARK_QUERIES
ADVERSARIAL_UNSUPPORTED_QUERIES = UNSUPPORTED_QUERIES
UnsupportedQuery = EvaluationQuery
BenchmarkQuery = EvaluationQuery

