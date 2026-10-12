"""Regression tests for architectural relationship queries, entity normalization,
retrieval governance, and robust LLM JSON parsing.

Verifies:
1. Intent classification and entity normalization for:
   - "What components are associated with VehicleControl?"
   - "What are all the components associated with VehicleControl?"
   - "What dependencies does VehicleControl have?"
   - "Which components does VehicleControl depend on?"
   - Spaced/lowercase variations ("vehicle control")
2. Retrieval of relevant dependency architectural evidence under Hybrid retrieval.
3. Governance awareness prioritizing approved HLD specifications over unreviewed draft uploads.
4. Robust JSON parsing and graceful fallback for LLM output.
"""

import json
import pytest

from rag.query_router import QueryRouter, QueryType
from rag.pipeline import get_pipeline, RAGPipeline
from rag.hybrid_retriever import get_hybrid_retriever
from rag.models import ConfidenceLevel


REGRESSION_QUERIES = [
    "What components are associated with VehicleControl?",
    "What are all the components associated with VehicleControl?",
    "What dependencies does VehicleControl have?",
    "Which components does VehicleControl depend on?",
]


class TestArchitectureQueryRouting:
    """Validate intent classification and entity normalization in QueryRouter."""

    def setup_method(self):
        self.router = QueryRouter()

    @pytest.mark.parametrize("query", REGRESSION_QUERIES)
    def test_canonical_architecture_queries_routed_to_dependencies(self, query):
        decision = self.router.route(query)
        assert decision.query_type == QueryType.ARCHITECTURE_QUERY
        assert "VehicleControl" in decision.target_entities
        assert decision.target_section_hint == "7."
        assert decision.target_chunk_type_hint == "dependency"

    def test_spaced_and_lowercase_entity_normalization(self):
        query = "What are all the components associated with vehicle control?"
        decision = self.router.route(query)
        assert decision.query_type == QueryType.ARCHITECTURE_QUERY
        assert "VehicleControl" in decision.target_entities
        assert decision.target_section_hint == "7."
        assert decision.target_chunk_type_hint == "dependency"

    def test_hyphenated_and_title_case_entity(self):
        query = "Which components does Vehicle-Control depend on?"
        decision = self.router.route(query)
        assert decision.query_type == QueryType.ARCHITECTURE_QUERY
        assert "VehicleControl" in decision.target_entities
        assert decision.target_section_hint == "7."


class TestHybridRetrievalRegression:
    """Validate that architecture queries retrieve dependency evidence."""

    @pytest.fixture(autouse=True)
    def setup_retriever(self):
        self.retriever = get_hybrid_retriever()

    @pytest.mark.parametrize("query", REGRESSION_QUERIES)
    def test_dependency_evidence_retrieved_in_top_chunks(self, query):
        """Regression test: verify dependency evidence is retrieved in top chunks."""
        results = self.retriever.retrieve(query, top_k=5, version=None)
        assert len(results) > 0

        # Check top evidence contains section 7 dependency information
        top_chunk = results[0][1]
        top_text = top_chunk.get("text", "")
        top_sec = str(top_chunk.get("section", ""))

        # Top chunk must be section 7 dependency evidence
        assert top_sec.startswith("7.") or "7." in top_sec or "depend" in top_text.lower()
        assert "VehicleControl" in top_text or top_chunk.get("entity_hint") == "VehicleControl"
        assert "SensorManager" in top_text or "DiagnosticManager" in top_text

    def test_governance_prioritizes_approved_hld_specifications(self):
        """Verify approved HLD specifications rank higher than draft test uploads."""
        query = "What are all the components associated with VehicleControl?"
        results = self.retriever.retrieve(query, top_k=5, version=None)

        # The rank 1 chunk must be from an approved official specification
        rank_1_doc = results[0][1].get("document_id", "")
        assert rank_1_doc.startswith("autosar_hld")
        # Ensure scores reflect governance
        scores = results[0][1].get("_scores", {})
        assert scores.get("governance_multiplier", 1.0) == 1.0


class TestLLMJSONParserResilience:
    """Validate robustness of _parse_llm_json against malformed and truncated responses."""

    def setup_method(self):
        self.pipeline = get_pipeline()

    def test_parses_clean_json(self):
        payload = {
            "answer": "VehicleControl depends on SensorManager, DiagnosticManager, and SafetyManager.",
            "claims": [{"claim_id": "c1", "statement": "VC depends on SM", "chunk_id": "chunk_1"}],
            "citations": [{"chunk_id": "chunk_1", "document_id": "autosar_hld_v2.0", "version": "2.0"}],
            "confidence": "high",
            "limitations": [],
            "review_required": False,
        }
        raw = json.dumps(payload)
        parsed = self.pipeline._parse_llm_json(raw)
        assert parsed["answer"] == payload["answer"]
        assert len(parsed["claims"]) == 1
        assert parsed["confidence"] == "high"

    def test_repairs_truncated_json(self):
        # Incomplete JSON (cut off inside claims array without closing brackets)
        truncated = '{"answer": "VehicleControl depends on SensorManager.", "claims": [{"claim_id": "c1", "statement": "VC depends on SM", "chunk_id": "chunk_1"}'
        parsed = self.pipeline._parse_llm_json(truncated)
        assert parsed["answer"] == "VehicleControl depends on SensorManager."
        assert len(parsed["claims"]) == 1

    def test_regex_recovery_from_unclosed_quotes(self):
        # Truncated midway through statement string
        cut_off = '{"answer": "VehicleControl is associated with SensorManager.", "claims": [{"claim_id": "c1", "statement": "VC depends'
        parsed = self.pipeline._parse_llm_json(cut_off)
        assert "VehicleControl is associated with SensorManager." in parsed["answer"]
        assert parsed["review_required"] is True

    def test_graceful_fallback_for_completely_invalid_output(self):
        invalid = "This is some unstructured explanatory text without JSON syntax."
        parsed = self.pipeline._parse_llm_json(invalid)
        assert parsed["review_required"] is True
        assert parsed["confidence"] == "low"
        assert "claims" in parsed and parsed["claims"] == []
        assert "citations" in parsed and parsed["citations"] == []
