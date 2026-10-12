"""Query Router and Intent Classifier for AUTOSAR HLD queries.

Classifies incoming queries into architectural intent categories:
1. ARCHITECTURE_QUERY (ports, signals, datatypes, interfaces, SWCs)
2. REVISION_QUERY (version differences, modifications, additions, renames)
3. IMPACT_QUERY (downstream/upstream propagation, affected components)
4. UNSUPPORTED_QUERY (adversarial / unindexed automotive topics)
5. DOCUMENT_QA / GENERAL_HLD_QUERY (conceptual architecture, standards)

Detects version intent ('1.0', '2.0') and extracts targeted architecture entities.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from extraction.models import (
    ExtractedComponent,
    ExtractedInterface,
    ExtractedPort,
    ExtractedSignal,
)


class QueryType(str, Enum):
    ARCHITECTURE_QUERY = "ARCHITECTURE_QUERY"
    REVISION_QUERY = "REVISION_QUERY"
    IMPACT_QUERY = "IMPACT_QUERY"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
    DOCUMENT_QA = "DOCUMENT_QA"


# Known architecture entities from the specification AST
KNOWN_COMPONENTS: Set[str] = {
    "VehicleControl", "SensorManager", "DiagnosticManager", "CommunicationManager", "SafetyManager"
}

KNOWN_INTERFACES: Set[str] = {
    "VehicleDataInterface", "DiagnosticInterface", "CommunicationInterface",
    "V2XCommunicationInterface", "SafetyMonitorInterface"
}

KNOWN_SIGNALS: Set[str] = {
    "VehicleSpeed", "EngineRPM", "EngineTemperature", "VehicleState",
    "DiagnosticStatus", "ControlCommand", "SafetyStatus", "SystemHealth"
}

# Known unsupported adversarial topics not present in the HLD
UNSUPPORTED_TOPIC_KEYWORDS: List[str] = [
    "baud rate", "bitrate", "processor", "microcontroller", "aurix", "arm cortex",
    "autosar os release", "os version", "flash memory", "eeprom", "rom size",
    "encryption algorithm", "aes", "rsa", "mac address", "ethernet phy",
    "misra c", "misra checker", "stack depth", "heap allocation", "stack size",
    "power management", "pmic", "supply voltage", "12v", "transceiver part",
    "pinout", "connector pin", "physical pinout", "transceiver pinout", "can transceiver",
    "communicationmanager asil", "sensormanager asil", "vehiclecontrol asil",
    "diagnosticmanager asil", "safety rating assigned to communicationmanager",
    "asil safety rating assigned to communicationmanager",
]


class RoutingDecision(BaseModel):
    """Detailed routing and classification decision for a user query."""
    query: str
    query_type: QueryType
    detected_version: Optional[str] = None
    target_entities: List[str] = Field(default_factory=list)
    target_section_hint: Optional[str] = None
    target_chunk_type_hint: Optional[str] = None
    confidence: float = 1.0
    rationale: str = ""
    suggested_engine: str = "rag_pipeline"  # 'rag_pipeline', 'revision_diff_engine', 'impact_analyzer'

    @property
    def intent(self) -> QueryType:
        return self.query_type

    @property
    def is_supported(self) -> bool:
        return self.query_type != QueryType.UNSUPPORTED_QUERY

    @property
    def entity_hints(self) -> List[str]:
        return self.target_entities



class QueryRouter:
    """Deterministic, lightweight query classifier for AUTOSAR HLD queries."""

    def route(self, question: str) -> RoutingDecision:
        """Classify a question and determine optimal routing parameters."""
        q_lower = question.lower()

        # 1. Version Detection
        detected_version = self._detect_version(q_lower)

        # 2. Extract Entities
        matched_entities = self._extract_entities(question)

        # 3. Check for Unsupported / Adversarial Questions
        for topic in UNSUPPORTED_TOPIC_KEYWORDS:
            if topic in q_lower:
                return RoutingDecision(
                    query=question,
                    query_type=QueryType.UNSUPPORTED_QUERY,
                    detected_version=detected_version,
                    target_entities=matched_entities,
                    confidence=0.95,
                    rationale=f"Query requests unsupported technical parameter '{topic}' not defined in HLD.",
                    suggested_engine="abstention_guard",
                )

        # Check for ASIL rating requested for components other than SafetyManager
        if ("asil" in q_lower or "safety rating" in q_lower) and any(
            comp.lower() in q_lower
            for comp in ["communicationmanager", "sensormanager", "vehiclecontrol", "diagnosticmanager"]
        ) and "safetymanager" not in q_lower:
            return RoutingDecision(
                query=question,
                query_type=QueryType.UNSUPPORTED_QUERY,
                detected_version=detected_version,
                target_entities=matched_entities,
                confidence=0.95,
                rationale="Query asks for ASIL rating of a component not assigned a safety level in HLD (only SafetyManager has ASIL-D).",
                suggested_engine="abstention_guard",
            )


        # 4. Check for Impact Queries
        impact_keywords = ["affected by", "impact of", "impact on", "consequences", "downstream", "what components may be affected"]
        if any(ik in q_lower for ik in impact_keywords):
            return RoutingDecision(
                query=question,
                query_type=QueryType.IMPACT_QUERY,
                detected_version=detected_version or "2.0",
                target_entities=matched_entities,
                target_section_hint="5.",
                confidence=0.95,
                rationale="Query asks for architectural impact analysis across dependencies.",
                suggested_engine="impact_analyzer",
            )

        # 5. Check for Revision / Diff / Comparative Queries
        revision_keywords = [
            "what changed", "difference between", "v1.0 vs v2.0", "v1 vs v2",
            "modified in", "added in v2", "added in version", "renamed",
            "version delta", "new in version 2", "new in v2",
            "identical", "same in both", "between versions", "across versions",
            "in both versions", "compare version", "version comparison",
        ]
        has_revision_intent = (
            any(rk in q_lower for rk in revision_keywords)
            or ("changed" in q_lower and "version" in q_lower)
            or bool(re.search(r"\b(?:add|added|adds|introduce|introduced|introduces)\b", q_lower) and re.search(r"\bv(?:ersion)?\s*(?:1|2)(?:\.0)?\b", q_lower))
            or bool(re.search(r"\b(?:identical|same)\b", q_lower) and ("port" in q_lower or "count" in q_lower or "signal" in q_lower or "datatype" in q_lower) and ("v1" in q_lower or "v2" in q_lower or "version" in q_lower))
        )

        if has_revision_intent:
            sec_hint = "2.2"
            type_hint = None
            if "port" in q_lower:
                sec_hint = "6."
                type_hint = "port"
            elif any(k in q_lower for k in ["depend", "coupling", "associat"]):
                sec_hint = "7."
                type_hint = "dependency"
            elif any(k in q_lower for k in ["signal", "datatype", "data type"]):
                sec_hint = "5."
                type_hint = "signal"
            elif "interface" in q_lower:
                sec_hint = "4."
                type_hint = "interface"
            elif any(k in q_lower for k in ["component", "swc"]):
                sec_hint = "3."
                type_hint = "component"

            return RoutingDecision(
                query=question,
                query_type=QueryType.REVISION_QUERY,
                detected_version=None,  # Cross-version comparison requires evidence from both releases
                target_entities=matched_entities,
                target_section_hint=sec_hint,
                target_chunk_type_hint=type_hint,
                confidence=0.95,
                rationale="Query requests comparison, modification, or addition verification across specification releases.",
                suggested_engine="revision_diff_engine",
            )

        # 6. Check for Architecture Queries (Ports, Signals, Interfaces, Dependencies, Flows, Components)
        arch_keywords = [
            "port", "ports", "signal", "signals", "datatype", "data type",
            "unit", "interface", "interfaces", "dependency", "dependencies",
            "depends on", "flow", "flows", "step", "steps", "carries",
            "provide", "provides", "require", "requires", "consumes", "produces",
            "component", "components", "swc", "swcs", "associated", "associate",
            "association", "associations", "connect", "connected", "connection",
            "connections", "relationship", "relationships", "coupling", "interact",
            "interaction", "interactions", "relates to", "related to"
        ]
        has_arch_keyword = any(ak in q_lower for ak in arch_keywords)

        if has_arch_keyword or matched_entities:
            sec_hint = None
            type_hint = None
            if "port" in q_lower:
                sec_hint = "6."
                type_hint = "port"
            elif any(k in q_lower for k in ["signal", "datatype", "data type", "unit"]):
                sec_hint = "5."
                type_hint = "signal"
            elif "flow" in q_lower:
                sec_hint = "8."
                type_hint = "flow"
            elif any(k in q_lower for k in [
                "depend", "coupling", "associat", "relationship", "relat",
                "connect", "interact", "dependencies"
            ]):
                sec_hint = "7."
                type_hint = "dependency"
            elif "interface" in q_lower:
                sec_hint = "4."
                type_hint = "interface"
            elif any(k in q_lower for k in ["component", "swc"]):
                sec_hint = "3."
                type_hint = "component"

            return RoutingDecision(
                query=question,
                query_type=QueryType.ARCHITECTURE_QUERY,
                detected_version=detected_version,
                target_entities=matched_entities,
                target_section_hint=sec_hint,
                target_chunk_type_hint=type_hint,
                confidence=0.90,
                rationale="Query targets specific architectural entities, ports, signals, or interfaces.",
                suggested_engine="rag_pipeline",
            )

        # 7. Fallback: General Document QA
        return RoutingDecision(
            query=question,
            query_type=QueryType.DOCUMENT_QA,
            detected_version=detected_version,
            target_entities=matched_entities,
            confidence=0.80,
            rationale="General conceptual inquiry or layer overview question.",
            suggested_engine="rag_pipeline",
        )

    def _detect_version(self, text_lower: str) -> Optional[str]:
        """Detect explicit version reference from query text."""
        # If query asks about additions/comparisons between releases, treat as cross-version
        is_comparative = (
            any(rk in text_lower for rk in [
                "what changed", "difference", "differ", "identical", "same in both",
                "compared", "comparison", "versus", "vs", "version delta", "new in",
                "between versions", "across versions", "in both versions"
            ])
            or bool(re.search(r"\b(?:add|added|adds|introduce|introduced|introduces)\b", text_lower))
        )
        if is_comparative:
            return None

        # Check v1.0 / version 1.0 / v1
        has_v1 = bool(re.search(r"\b(?:v(?:ersion)?\s*1(?:\.0)?|baseline)\b", text_lower))
        has_v2 = bool(re.search(r"\b(?:v(?:ersion)?\s*2(?:\.0)?|revision)\b", text_lower))

        if has_v1 and has_v2:
            return None  # Both versions mentioned (comparative)
        if has_v1:
            return "1.0"
        if has_v2:
            return "2.0"
        return None

    def _extract_entities(self, text: str) -> List[str]:
        """Extract known architectural entities mentioned in the query."""
        found: List[str] = []
        text_lower = text.lower()
        text_normalized = re.sub(r"[\s_\-]+", "", text_lower)

        def matches_entity(entity: str) -> bool:
            ent_lower = entity.lower()
            if ent_lower in text_lower:
                return True
            ent_normalized = re.sub(r"[\s_\-]+", "", ent_lower)
            if ent_normalized in text_normalized:
                return True
            return False

        # Check components
        for c in KNOWN_COMPONENTS:
            if matches_entity(c):
                found.append(c)

        # Check interfaces
        for i in KNOWN_INTERFACES:
            if matches_entity(i) and i not in found:
                found.append(i)

        # Check signals
        for s in KNOWN_SIGNALS:
            if matches_entity(s) and s not in found:
                found.append(s)

        return sorted(found)


# Global singleton instance
_query_router_instance: Optional[QueryRouter] = None


def get_query_router() -> QueryRouter:
    """Get or create singleton QueryRouter."""
    global _query_router_instance
    if _query_router_instance is None:
        _query_router_instance = QueryRouter()
    return _query_router_instance
