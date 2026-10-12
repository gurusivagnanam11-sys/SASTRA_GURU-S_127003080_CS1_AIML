"""Regression tests for VehicleSpeed data type across versions 1.0 and 2.0.

Verifies:
1. Version 1.0 query returns float32 with valid v1.0 citations and high confidence.
2. Version 2.0 query returns float64 with valid v2.0 citations and high confidence.
3. Cross-version query ("versions 1.0 and 2.0") accurately reports float32 for v1.0 and float64 for v2.0.
4. Grounding verification rejects answers claiming float32 for both versions (flags contradiction, lowers grounding score, marks review_required).
5. Grounding verification rejects answers attributing float32 to version 2.0.
6. Per-chunk source text verification confirms actual values directly match cited evidence chunks.
"""

import json
import pytest

from rag.grounding_checker import GroundingChecker, check_claim_contradictions
from rag.models import Citation, Claim, ConfidenceLevel, ContextChunk
from rag.pipeline import get_pipeline


class TestVehicleSpeedGroundingVerification:
    """Verify deterministic grounding checks and contradiction detection against source text."""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        self.grounding_checker = GroundingChecker()
        self.chunk_v1 = ContextChunk(
            chunk_id="autosar_hld__v1.0_p07_c27",
            document_id="autosar_hld_v1.0",
            version="1.0",
            page_number=7,
            section="5.",
            section_title="Signals",
            chunk_type="interface",
            entity_hint="VehicleSpeed",
            text=(
                "5. Signals\n"
                "Signal Name\nType\nUnit\nSource\nDestination\nInterface\n"
                "VehicleSpeed\nfloat32\nkm/h\nSensorManager\nVehicleControl\nVehicleDataInterface\n"
                "EngineRPM\nuint16\nrpm\nSensorManager\nVehicleControl\nVehicleDataInterface"
            ),
            score=0.87,
        )
        self.chunk_v2 = ContextChunk(
            chunk_id="autosar_hld__v2.0_p07_c30",
            document_id="autosar_hld_v2.0",
            version="2.0",
            page_number=7,
            section="5.",
            section_title="Signals",
            chunk_type="interface",
            entity_hint="VehicleSpeed",
            text=(
                "5. Signals\n"
                "Signal Name\nType\nUnit\nSource\nDestination\nInterface\n"
                "VehicleSpeed\nfloat64\nkm/h\nSensorManager\nVehicleControl\nVehicleDataInterface\n"
                "EngineRPM\nuint16\nrpm\nSensorManager\nVehicleControl\nVehicleDataInterface\n"
                "EngineTemperature\nfloat32\ndegC\nSensorManager\nVehicleControl\nVehicleDataInterface"
            ),
            score=0.87,
        )

    def test_rejects_answer_claiming_float32_for_both_versions(self):
        """Reject an answer that claims float32 for both versions when v2.0 evidence says float64."""
        # Contradictory claim asserting float32 across both versions
        claim_contradictory = Claim(
            text="The data type assigned to VehicleSpeed in both versions 1.0 and 2.0 is float32.",
            citation_ids=["autosar_hld__v1.0_p07_c27", "autosar_hld__v2.0_p07_c30"],
        )

        checked_claims, score, issues = self.grounding_checker.check_grounding(
            answer="The data type assigned to VehicleSpeed in both versions 1.0 and 2.0 is float32.",
            claims=[claim_contradictory],
            retrieved_chunks=[self.chunk_v1, self.chunk_v2],
        )

        assert checked_claims[0].grounded is False
        assert score == 0.0, "Score must not be 1.0 when a claim contradicts cited evidence"
        assert any("contradicts cited chunk" in iss for iss in issues)
        assert any("autosar_hld__v2.0_p07_c30" in iss for iss in issues)

    def test_rejects_claim_attributing_float32_to_version_2(self):
        """Reject claim specifically stating VehicleSpeed in version 2.0 is float32."""
        claim_v2_invalid = Claim(
            text="In version 2.0, the VehicleSpeed signal has data type float32.",
            citation_ids=["autosar_hld__v2.0_p07_c30"],
        )

        checked, score, issues = self.grounding_checker.check_grounding(
            answer="In version 2.0, VehicleSpeed is float32.",
            claims=[claim_v2_invalid],
            retrieved_chunks=[self.chunk_v2],
        )

        assert checked[0].grounded is False
        assert score == 0.0
        assert any("contradicts cited chunk" in iss for iss in issues)

    def test_accepts_grounded_version_specific_claims(self):
        """Accept separate claims matching source values in v1.0 and v2.0 evidence."""
        claim_v1 = Claim(
            text="The data type assigned to VehicleSpeed in version 1.0 is float32.",
            citation_ids=["autosar_hld__v1.0_p07_c27"],
        )
        claim_v2 = Claim(
            text="The data type assigned to VehicleSpeed in version 2.0 is float64.",
            citation_ids=["autosar_hld__v2.0_p07_c30"],
        )

        checked, score, issues = self.grounding_checker.check_grounding(
            answer="In version 1.0 VehicleSpeed is float32, and in version 2.0 it is float64.",
            claims=[claim_v1, claim_v2],
            retrieved_chunks=[self.chunk_v1, self.chunk_v2],
        )

        assert checked[0].grounded is True
        assert checked[1].grounded is True
        assert score == 1.0
        assert len(issues) == 0

    def test_direct_chunk_contradiction_function(self):
        """Unit test check_claim_contradictions function directly."""
        err1 = check_claim_contradictions(
            "The data type assigned to VehicleSpeed in both versions 1.0 and 2.0 is float32.",
            self.chunk_v2,
        )
        assert err1 is not None
        assert "contradicts cited chunk" in err1

        err2 = check_claim_contradictions(
            "The data type assigned to VehicleSpeed in version 2.0 is float64.",
            self.chunk_v2,
        )
        assert err2 is None


class TestVehicleSpeedPipelineDeterministic:
    """Verify deterministic pipeline question answering using Mock provider."""

    @pytest.fixture(autouse=True)
    def setup_pipeline(self):
        self.pipeline = get_pipeline(provider_name="mock")

    def test_pipeline_v1_isolation_returns_float32(self):
        """Querying version 1.0 specifically returns float32."""
        q = "What data type is assigned to VehicleSpeed in version 1.0?"
        resp = self.pipeline.ask(q, document_version="1.0")

        assert "float32" in resp.answer.lower()
        assert resp.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert any("1.0" in c.version for c in resp.citations)
        assert resp.grounding_score >= 0.85

    def test_pipeline_v2_isolation_returns_float64(self):
        """Querying version 2.0 specifically returns float64."""
        q = "What data type is assigned to VehicleSpeed in version 2.0?"
        resp = self.pipeline.ask(q, document_version="2.0")

        assert "float64" in resp.answer.lower()
        assert resp.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        assert any("2.0" in c.version for c in resp.citations)
        assert resp.grounding_score >= 0.85

    def test_pipeline_cross_version_query_returns_both_accurately(self):
        """Querying both versions reports float32 for v1.0 and float64 for v2.0."""
        q = "What data type is assigned to VehicleSpeed in versions 1.0 and 2.0?"
        resp = self.pipeline.ask(q)

        ans_lower = resp.answer.lower()
        assert "float32" in ans_lower
        assert "float64" in ans_lower
        assert resp.confidence == ConfidenceLevel.HIGH
        assert resp.review_required is False
        assert resp.grounding_score == 1.0

        # Verify distinct claims
        claim_texts = [c.text.lower() for c in resp.claims]
        assert any("1.0" in ct and "float32" in ct for ct in claim_texts)
        assert any("2.0" in ct and "float64" in ct for ct in claim_texts)

        # Verify citations cover both versions
        c_versions = {c.version for c in resp.citations}
        assert "1.0" in c_versions
        assert "2.0" in c_versions

    def test_pipeline_contradictory_response_triggers_low_confidence_and_review(self):
        """If an LLM produces a contradictory response claiming float32 for v2.0, pipeline must flag it."""
        mock_provider = self.pipeline.llm_provider
        # Inject contradictory LLM payload
        contradictory_payload = {
            "answer": "The data type assigned to VehicleSpeed in both versions 1.0 and 2.0 is float32.",
            "claims": [
                {
                    "text": "The data type assigned to VehicleSpeed in both versions 1.0 and 2.0 is float32.",
                    "citation_ids": ["autosar_hld__v1.0_p07_c27", "autosar_hld__v2.0_p07_c30"],
                }
            ],
            "citations": [
                {
                    "document": "autosar_hld_v1.0",
                    "version": "1.0",
                    "page": 7,
                    "section": "5.",
                    "chunk_id": "autosar_hld__v1.0_p07_c27",
                },
                {
                    "document": "autosar_hld_v2.0",
                    "version": "2.0",
                    "page": 7,
                    "section": "5.",
                    "chunk_id": "autosar_hld__v2.0_p07_c30",
                },
            ],
            "confidence": "high",
            "limitations": [],
            "review_required": False,
        }
        mock_provider.set_custom_response(contradictory_payload)

        try:
            q = "What data type is assigned to VehicleSpeed in versions 1.0 and 2.0?"
            resp = self.pipeline.ask(q)

            # Grounding check must have caught the contradiction
            assert resp.grounding_score == 0.0
            assert resp.confidence == ConfidenceLevel.LOW
            assert resp.review_required is True
            assert any("contradicts" in lim.lower() for lim in resp.limitations)
        finally:
            mock_provider.clear_custom_response()
