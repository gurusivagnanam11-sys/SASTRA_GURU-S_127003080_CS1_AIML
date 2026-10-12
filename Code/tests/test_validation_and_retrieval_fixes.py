"""Regression tests for architecture validation diagnostics and retrieval quality fixes.

Verifies:
1. Deterministic architecture validation findings for v1.0 and v2.0.
2. Provenance accuracy for extracted interfaces (Section 4 on Page 6).
3. Retrieval quality for VehicleSpeed (eval_01) with All Versions and specific version isolation.
4. Governance filtering preventing unapproved/draft document contamination.
5. Benchmark dataset ground-truth integrity and source chunk validity.
"""

import pytest

from analysis.architecture_validator import (
    Severity,
    ValidationCategory,
    validate_architecture,
)
from evaluation.dataset import get_benchmark_dataset
from extraction.basic_extractor import get_architecture_extractor
from rag.citation_validator import CitationValidator
from rag.grounding_checker import GroundingChecker
from rag.hybrid_retriever import get_hybrid_retriever
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk
from rag.pipeline import get_pipeline
from rag.query_router import QueryType, get_query_router
from reports.generator import get_governance
from reports.models import DocumentStatus


class TestArchitectureValidationDiagnostics:
    """Verify deterministic validation findings and provenance for v1.0 and v2.0."""

    def setup_method(self):
        self.extractor = get_architecture_extractor()

    def test_v1_architecture_validation_findings(self):
        """v1.0 model should produce exactly 1 ERROR and 1 WARNING due to genuine HLD omissions."""
        model_v1 = self.extractor.get_complete_model("1.0")
        result = validate_architecture(model_v1)

        assert result.summary.errors == 1
        assert result.summary.warnings == 1
        assert result.status == "ERROR"

        # Error: Undefined signal CommStatus referenced by CommunicationInterface
        err = result.errors[0]
        assert err.category == ValidationCategory.UNDEFINED_REFERENCE
        assert err.entity_name == "CommunicationInterface"
        assert err.related_entity == "CommStatus"

        # Warning: Orphan interface CommunicationInterface with no port mapping
        warn = result.warnings[0]
        assert warn.category == ValidationCategory.ORPHAN_ENTITY
        assert warn.entity_name == "CommunicationInterface"

    def test_v2_architecture_validation_findings(self):
        """v2.0 model should produce exactly 5 ERRORS and 1 WARNING due to genuine HLD omissions."""
        model_v2 = self.extractor.get_complete_model("2.0")
        result = validate_architecture(model_v2)

        assert result.summary.errors == 5
        assert result.summary.warnings == 1
        assert result.status == "ERROR"

        err_entities = [(e.entity_type, e.entity_name, e.related_entity) for e in result.errors]

        # 1 & 2: Ports SafetyStatusOut and SafetyStatusIn reference undefined signal SafetyStatus
        assert ("Port", "SafetyStatusOut", "SafetyStatus") in err_entities
        assert ("Port", "SafetyStatusIn", "SafetyStatus") in err_entities

        # 3 & 4: SafetyMonitorInterface references undefined signals SafetyStatus and SystemHealth
        assert ("Interface", "SafetyMonitorInterface", "SafetyStatus") in err_entities
        assert ("Interface", "SafetyMonitorInterface", "SystemHealth") in err_entities

        # 5: V2XCommunicationInterface references undefined signal CommStatus
        assert ("Interface", "V2XCommunicationInterface", "CommStatus") in err_entities

        # 6: Warning: V2XCommunicationInterface is orphan (no port mapping)
        warn = result.warnings[0]
        assert warn.category == ValidationCategory.ORPHAN_ENTITY
        assert warn.entity_name == "V2XCommunicationInterface"

    def test_interface_extraction_provenance_accuracy(self):
        """Interfaces must point to Section 4 (Page 6), not Section 3 component chunks."""
        ifaces_v2 = self.extractor.extract_interfaces(version="2.0")
        smi = next(i for i in ifaces_v2 if i.name == "SafetyMonitorInterface")
        v2x = next(i for i in ifaces_v2 if i.name == "V2XCommunicationInterface")

        assert smi.page == 6
        assert smi.section.startswith("4")
        assert smi.chunk_id == "autosar_hld__v2.0_p06_c28"

        assert v2x.page == 6
        assert v2x.section.startswith("4")
        assert v2x.chunk_id == "autosar_hld__v2.0_p06_c27"


class TestRetrievalQualityAndGovernance:
    """Verify retrieval precision, version filtering, and governance protection."""

    @pytest.fixture(autouse=True)
    def setup_retriever(self):
        self.retriever = get_hybrid_retriever()

    def test_vehiclespeed_eval01_retrieval_all_versions(self):
        """eval_01 ('What interface carries VehicleSpeed?') retrieves approved HLD chunks without contamination."""
        query = "What interface carries VehicleSpeed?"
        results = self.retriever.retrieve(query, top_k=5, version=None)
        assert len(results) >= 4

        retrieved_ids = [c["chunk_id"] for _, c in results]
        retrieved_docs = [c["document_id"] for _, c in results]

        # Top 4 chunks must include ground-truth signals and interface specifications
        expected_matches = {
            "autosar_hld__v1.0_p07_c27",
            "autosar_hld__v2.0_p07_c30",
            "autosar_hld__v1.0_p06_c23",
            "autosar_hld__v2.0_p06_c25",
        }
        found_in_top4 = set(retrieved_ids[:4]).intersection(expected_matches)
        assert len(found_in_top4) == 4, f"Top 4 must contain all expected chunks, got: {retrieved_ids[:4]}"

        # Must not retrieve unrelated documents in top results
        assert all(doc.startswith("autosar_hld") for doc in retrieved_docs[:4])
        assert "harrier-ev-onwers-manual" not in retrieved_docs[:4]

    def test_vehiclespeed_specific_version_isolation(self):
        """Querying with version='1.0' or '2.0' must return strictly chunks from that version."""
        query = "What interface carries VehicleSpeed?"

        # Test v1.0 isolation
        results_v1 = self.retriever.retrieve(query, top_k=5, version="1.0")
        assert len(results_v1) > 0
        for _, c in results_v1:
            assert str(c.get("version")).strip() == "1.0"
            assert "autosar_hld_v1.0" in c.get("document_id", "")

        # Test v2.0 isolation
        results_v2 = self.retriever.retrieve(query, top_k=5, version="2.0")
        assert len(results_v2) > 0
        for _, c in results_v2:
            assert str(c.get("version")).strip() == "2.0"
            assert "autosar_hld_v2.0" in c.get("document_id", "")

    def test_governance_penalizes_draft_and_unapproved_documents(self):
        """Approved specifications must receive 1.0 multiplier while drafts/unapproved receive penalties."""
        gov_v1 = get_governance("autosar_hld_v1.0")
        gov_v2 = get_governance("autosar_hld_v2.0")

        assert gov_v1 is not None and gov_v1.status == DocumentStatus.APPROVED
        assert gov_v2 is not None and gov_v2.status == DocumentStatus.APPROVED


class TestBenchmarkGroundTruthIntegrity:
    """Verify that all expected ground-truth chunks in the dataset exist and are valid."""

    def test_ground_truth_chunks_reflect_real_content(self):
        """All expected chunks in the dataset must point to verified chunks in the metadata store."""
        retriever = get_hybrid_retriever()
        store = retriever.metadata_store
        metadata_map = {e.get("chunk_id"): e for e in store.entries}

        dataset = get_benchmark_dataset()
        for q in dataset:
            for expected_id in q.expected_chunks:
                assert expected_id in metadata_map, f"Query {q.query_id} expects {expected_id} which does not exist in metadata store!"
                chunk_data = metadata_map[expected_id]
                # Ensure it's not an empty warning banner or lone header
                text = chunk_data.get("text", "")
                assert len(text.strip()) > 10, f"Expected chunk {expected_id} has insufficient text: '{text}'"

        # Verify eval_01 specifically points to c25 for v2.0 VehicleDataInterface
        eval_01 = next(q for q in dataset if q.query_id == "eval_01")
        assert "autosar_hld__v2.0_p06_c25" in eval_01.expected_chunks
        assert "autosar_hld__v2.0_p06_c24" not in eval_01.expected_chunks


class TestRegressionTrueFalseRetrievalAndGrounding:
    """Regression suite covering True/False evaluation, citation grounding, and cross-version retrieval."""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        self.grounding_checker = GroundingChecker()
        self.citation_validator = CitationValidator()
        self.retriever = get_hybrid_retriever()
        self.router = get_query_router()
        self.pipeline = get_pipeline(provider_name="mock")

    def test_missing_and_non_retrieved_citations(self):
        """Claims with missing or non-retrieved citations must be flagged as ungrounded."""
        chunk = ContextChunk(
            chunk_id="autosar_hld__v2.0_p08_c34",
            document_id="autosar_hld_v2.0",
            version="2.0",
            page_number=8,
            section="7.1",
            section_title="Dependencies",
            chunk_type="dependency",
            text="7.1 Component Dependencies\nVehicleControl depends on SafetyManager for safety override commands.",
            score=0.85,
        )

        # 1. Claim lacking any citations
        claim_no_cite = Claim(text="VehicleControl depends on SafetyManager.", citation_ids=[])
        checked, score, issues = self.grounding_checker.check_grounding(
            answer="VehicleControl depends on SafetyManager.",
            claims=[claim_no_cite],
            retrieved_chunks=[chunk],
        )
        assert checked[0].grounded is False
        assert score == 0.0
        assert any("Claim lacks citations" in iss for iss in issues)

        # 2. Claim citing non-retrieved fabricated chunk ID
        claim_bad_cite = Claim(
            text="VehicleControl depends on SafetyManager.",
            citation_ids=["fabricated_chunk_id_99"],
        )
        checked, score, issues = self.grounding_checker.check_grounding(
            answer="VehicleControl depends on SafetyManager.",
            claims=[claim_bad_cite],
            retrieved_chunks=[chunk],
        )
        assert checked[0].grounded is False
        assert score == 0.0
        assert any("cites non-retrieved chunk" in iss for iss in issues)

        # 3. Truncated prefix citation resolves unambiguously
        claim_truncated = Claim(
            text="VehicleControl depends on SafetyManager for safety override commands.",
            citation_ids=["autosar_hld__v2.0_p08"],  # Missing _c34 suffix
        )
        checked, score, issues = self.grounding_checker.check_grounding(
            answer="VehicleControl depends on SafetyManager.",
            claims=[claim_truncated],
            retrieved_chunks=[chunk],
        )
        assert checked[0].grounded is True
        assert checked[0].citation_ids == ["autosar_hld__v2.0_p08_c34"]
        assert score == 1.0

    def test_valid_citation_does_not_mean_grounded_claim(self):
        """A valid citation ID does not ground a claim containing unsupported facts (Issue 4)."""
        chunk = ContextChunk(
            chunk_id="autosar_hld__v2.0_p07_c31",
            document_id="autosar_hld_v2.0",
            version="2.0",
            page_number=7,
            section="5.",
            section_title="Signals",
            chunk_type="general",
            text="6. Port Definitions\nVehicleSpeedIn VehicleControl Input VehicleDataInterface VehicleSpeed",
            score=0.80,
        )

        # Citation metadata is valid
        cit = Citation(
            document="autosar_hld_v2.0",
            version="2.0",
            page=7,
            section="5.",
            chunk_id="autosar_hld__v2.0_p07_c31",
        )
        validated_cits, all_valid, _ = self.citation_validator.validate_citations(
            citations=[cit], retrieved_chunks=[chunk]
        )
        assert all_valid is True
        assert validated_cits[0].valid is True

        # Claim contains fabricated hardware details not in the chunk
        unsupported_claim = Claim(
            text="VehicleControl executes on an ARM Cortex-M4 microcontroller running at 100MHz with flash storage.",
            citation_ids=["autosar_hld__v2.0_p07_c31"],
        )
        checked, score, issues = self.grounding_checker.check_grounding(
            answer="VehicleControl executes on an ARM Cortex-M4 microcontroller.",
            claims=[unsupported_claim],
            retrieved_chunks=[chunk],
        )
        assert checked[0].grounded is False
        assert score == 0.0
        assert any("low textual support" in iss for iss in issues)

    def test_vehiclecontrol_heading_and_metadata_grounding(self):
        """VehicleControl definition claims are supported by section heading and metadata (Issue 2)."""
        chunk = ContextChunk(
            chunk_id="autosar_hld__v2.0_p04_c17",
            document_id="autosar_hld_v2.0",
            version="2.0",
            page_number=4,
            section="3.",
            section_title="Software Components",
            chunk_type="component",
            entity_hint="VehicleControl",
            text="3.1 VehicleControl",
            score=0.88,
        )

        claim = Claim(
            text="VehicleControl is defined as a software component under Section 3.1.",
            citation_ids=["autosar_hld__v2.0_p04_c17"],
        )
        checked, score, issues = self.grounding_checker.check_grounding(
            answer="VehicleControl is defined under Section 3.1.",
            claims=[claim],
            retrieved_chunks=[chunk],
        )
        assert checked[0].grounded is True
        assert score == 1.0
        assert len(issues) == 0

    def test_cross_version_balanced_retrieval(self):
        """Cross-version queries retrieve evidence from both releases without starving either (Issue 3)."""
        # 1. Dependency addition query
        q_dep = "Does v2.0 add a dependency from VehicleControl to SafetyManager?"
        results_dep = self.retriever.retrieve(q_dep, top_k=5)
        versions_dep = {c["version"] for _, c in results_dep}
        assert "1.0" in versions_dep, "v1.0 baseline must be retrieved for dependency comparison"
        assert "2.0" in versions_dep, "v2.0 revision must be retrieved for dependency comparison"

        # 2. Port count identity query
        q_ports = "Are v1.0 and v2.0 identical in their port counts?"
        results_ports = self.retriever.retrieve(q_ports, top_k=5)
        versions_ports = {c["version"] for _, c in results_ports}
        assert "1.0" in versions_ports, "v1.0 baseline must be retrieved for port comparison"
        assert "2.0" in versions_ports, "v2.0 revision must be retrieved for port comparison"

        # Top results must contain the port definition tables
        top_ids = [c["chunk_id"] for _, c in results_ports[:2]]
        assert "autosar_hld__v2.0_p07_c31" in top_ids
        assert "autosar_hld__v1.0_p07_c28" in top_ids

    def test_cross_version_comparison_abstains_when_version_missing(self):
        """Cross-version comparisons must abstain rather than guessing if a version is missing."""
        q = "Are v1.0 and v2.0 identical in their port counts?"
        # Force single-version constraint so v1.0 is completely missing
        res = self.pipeline.ask(q, document_version="2.0")
        assert res.confidence == ConfidenceLevel.LOW
        assert res.review_required is True
        assert "Insufficient evidence" in res.answer
        assert "1.0" in res.answer or any("1.0" in lim for lim in res.limitations)

    def test_true_false_evaluation_distinction(self):
        """End-to-end pipeline properly distinguishes supported True, supported False, and abstention."""
        # A. Supported True statement
        res_true = self.pipeline.ask("Does v2.0 add a dependency from VehicleControl to SafetyManager?")
        assert res_true.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert res_true.review_required is False
        assert "Yes" in res_true.answer
        assert res_true.grounding_score == 1.0

        # B. Supported False statement
        res_false = self.pipeline.ask("Are v1.0 and v2.0 identical in their port counts?")
        assert res_false.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert res_false.review_required is False
        assert "No" in res_false.answer
        assert res_false.grounding_score == 1.0

        # C. Not specified / Unsupported statement
        res_unsupported = self.pipeline.ask("What is the CAN bus transceiver physical pinout and baud rate?")
        assert res_unsupported.confidence == ConfidenceLevel.LOW
        assert res_unsupported.review_required is True
        assert "do not specify" in res_unsupported.answer.lower()
