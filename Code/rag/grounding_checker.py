"""Lightweight deterministic grounding checker for AUTOSAR HLD RAG outputs.

Compares claims and answer content against retrieved evidence chunks to detect
unsupported statements and flag them for human engineer review.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from rag.models import Claim, ContextChunk

logger = logging.getLogger(__name__)

# Basic English stopwords to filter out when checking content term overlap
COMMON_STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its",
    "itself", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself",
}

# Meta-discourse and reporting vocabulary commonly used in engineering summaries
# Filtered so faithful synthesis statements are not falsely penalized as ungrounded
REPORTING_STOPWORDS: Set[str] = {
    "defined", "defines", "definition", "definitions",
    "specified", "specifies", "specification", "specifications",
    "described", "describes", "description", "descriptions",
    "stated", "states", "statement", "statements",
    "provided", "provides", "providing", "provision",
    "listed", "lists", "listing", "listings",
    "included", "includes", "including",
    "contains", "contained", "containing",
    "table", "tables", "section", "sections", "heading", "headings",
    "document", "documents", "documentation",
    "hld", "autosar", "version", "versions",
    "page", "pages", "chapter", "chapters",
    "evidence", "chunk", "chunks", "excerpt", "excerpts",
    "per", "according", "refer", "refers", "referenced", "references",
    "shows", "shown", "indicates", "indicated", "mentions", "mentioned",
    "presents", "presented", "details", "detailed",
    "specific", "mappings", "mapping", "mapped",
    "state", "states", "whether", "true", "false", "yes", "no",
    "complete", "set", "system", "connected", "connection", "connections",
    "connect", "connects", "least", "list", "lists",
}

ALL_EVAL_STOPWORDS = COMMON_STOPWORDS | REPORTING_STOPWORDS

KNOWN_DATA_TYPES: Set[str] = {
    "float32", "float64", "uint8", "uint16", "uint32", "int8", "int16", "int32",
    "boolean", "bool", "enum", "struct"
}


def extract_signal_type_bindings(text: str) -> Dict[str, str]:
    """Extract (signal_name, data_type) bindings from text or tabular rows."""
    bindings = {}
    types_pattern = r"(float32|float64|uint8|uint16|uint32|int8|int16|int32|boolean|bool|enum|struct)"
    # Matches: SignalName [newline/spaces] DataType
    for m in re.finditer(rf"\b([A-Za-z0-9_]+)\s*(?:[\n\r]+|\s+){types_pattern}\b", text, re.IGNORECASE):
        entity = m.group(1).lower()
        dtype = m.group(2).lower()
        if entity not in ("signal", "name", "type", "unit", "source", "destination", "interface"):
            bindings[entity] = dtype
    return bindings


def check_claim_contradictions(claim_text: str, chunk: ContextChunk) -> Optional[str]:
    """Check if claim directly contradicts entity-attribute bindings in cited chunk."""
    chunk_text = f"{chunk.text} {chunk.section} {chunk.section_title}".lower()
    claim_lower = claim_text.lower()
    chunk_ver = chunk.version.strip() if chunk.version else ""

    # 1. Check Signal Data Types
    chunk_signal_types = extract_signal_type_bindings(chunk.text)
    for signal, actual_type in chunk_signal_types.items():
        if signal in claim_lower:
            # Check what data types appear in the claim
            claim_types_present = [dt for dt in KNOWN_DATA_TYPES if re.search(rf"\b{dt}\b", claim_lower)]
            if not claim_types_present:
                continue

            # Determine whether this claim asserts properties of this chunk's version
            mentions_chunk_version = (
                (chunk_ver and (chunk_ver in claim_lower or f"v{chunk_ver}" in claim_lower))
                or "both versions" in claim_lower
                or "each version" in claim_lower
                or "all versions" in claim_lower
                or "two versions" in claim_lower
            )
            other_ver = "1.0" if chunk_ver == "2.0" else "2.0"
            strictly_other_version = (
                (other_ver in claim_lower or f"v{other_ver}" in claim_lower)
                and not mentions_chunk_version
            )

            if strictly_other_version:
                continue

            # Check if claim asserts a type that contradicts actual_type in this chunk
            for ct in claim_types_present:
                if ct != actual_type:
                    # Invariance assumption e.g., "in both versions ... is float32"
                    if any(term in claim_lower for term in ("both versions", "all versions", "each version", "two versions")):
                        return (
                            f"Claim asserts {signal} is {ct} across versions, which contradicts cited chunk "
                            f"{chunk.chunk_id} (version {chunk_ver}) where {signal} is defined as {actual_type}."
                        )
                    # Version-specific claim e.g., "version 2.0 is float32" while chunk defines float64
                    if chunk_ver and (chunk_ver in claim_lower or f"v{chunk_ver}" in claim_lower):
                        pattern = rf"(?:version\s*{chunk_ver}|v{chunk_ver})[^\.\,\;]*?\b{ct}\b"
                        if re.search(pattern, claim_lower) or not re.search(rf"(?:version\s*{chunk_ver}|v{chunk_ver})[^\.\,\;]*?\b{actual_type}\b", claim_lower):
                            return (
                                f"Claim asserts {signal} in version {chunk_ver} is {ct}, which contradicts cited chunk "
                                f"{chunk.chunk_id} where {signal} is defined as {actual_type}."
                            )

    # 2. Check Port Counts
    if "port" in claim_lower and ("count" in claim_lower or "port definitions" in chunk_text):
        count_m = re.search(r"\b(\d+)\s+(?:component\s+)?ports\b", chunk_text)
        if count_m:
            actual_count = count_m.group(1)
            if chunk_ver and (chunk_ver in claim_lower or f"v{chunk_ver}" in claim_lower):
                claim_counts = re.findall(r"\b(\d+)\s+(?:component\s+)?ports\b", claim_lower)
                for cc in claim_counts:
                    if cc != actual_count and re.search(rf"(?:version\s*{chunk_ver}|v{chunk_ver})[^\.\,\;]*?\b{cc}\b", claim_lower):
                        return (
                            f"Claim asserts {cc} ports in version {chunk_ver}, which contradicts cited chunk "
                            f"{chunk.chunk_id} where port count is {actual_count}."
                        )

    return None


class GroundingChecker:
    """Deterministic grounding verification comparing claims to retrieved evidence."""

    @staticmethod
    def resolve_chunk_id(cid: str, retrieved_chunks: List[ContextChunk]) -> Optional[str]:
        """Resolve a citation ID against retrieved chunks, handling unambiguous prefix truncation."""
        cid_clean = cid.strip()
        # 1. Exact match
        for c in retrieved_chunks:
            if c.chunk_id == cid_clean:
                return c.chunk_id
        # 2. Prefix match (e.g. LLM produced 'autosar_hld__v2.0_p08' for 'autosar_hld__v2.0_p08_c34')
        matches = [
            c.chunk_id for c in retrieved_chunks
            if c.chunk_id.startswith(cid_clean + "_") or c.chunk_id == cid_clean
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def check_grounding(
        self,
        answer: str,
        claims: List[Claim],
        retrieved_chunks: List[ContextChunk],
    ) -> Tuple[List[Claim], float, List[str]]:
        """Verify that claims are grounded in the retrieved chunk text.

        Args:
            answer: Complete answer text.
            claims: List of Claim objects extracted from the answer.
            retrieved_chunks: Evidence chunks available during synthesis.

        Returns:
            Tuple of:
            - checked_claims: Updated Claim objects with `grounded` boolean
            - grounding_score: Float between 0.0 and 1.0
            - issues: List of human-readable grounding issue strings
        """
        issues: List[str] = []

        if not retrieved_chunks:
            # If answer correctly declares insufficient evidence, that is grounded behavior
            if "insufficient evidence" in answer.lower():
                return claims, 1.0, []
            issues.append("Answer generated with zero retrieved evidence chunks.")
            for c in claims:
                c.grounded = False
            return claims, 0.0, issues

        # Map chunk objects and evidence texts
        chunk_obj_map: Dict[str, ContextChunk] = {
            c.chunk_id: c for c in retrieved_chunks
        }
        chunk_evidence_map: Dict[str, str] = {
            c.chunk_id: f"{c.text} {c.section} {c.section_title} {c.chunk_type} {c.entity_hint}".lower()
            for c in retrieved_chunks
        }
        all_retrieved_text = " ".join(chunk_evidence_map.values())

        if not claims:
            # If answer declares insufficient evidence, that is grounded abstention behavior
            if "insufficient evidence" in answer.lower():
                return [], 1.0, []
            # Check answer directly if no fine-grained claims provided
            answer_words = self._extract_content_words(answer)
            if not answer_words:
                return [], 1.0, []
            missing = [w for w in answer_words if w not in all_retrieved_text]
            ratio = 1.0 - (len(missing) / len(answer_words)) if answer_words else 1.0
            if ratio < 0.6:
                issues.append(f"Answer contains significant ungrounded vocabulary not in context (support: {ratio:.1%}).")
            return [], max(0.0, min(1.0, ratio)), issues

        grounded_count = 0

        for claim in claims:
            if not claim.citation_ids:
                claim.grounded = False
                issues.append(f"Claim lacks citations: '{claim.text[:60]}...'")
                continue

            # Resolve citation IDs against retrieved chunks
            resolved_cids = []
            invalid_citations = []
            for cid in claim.citation_ids:
                matched_id = self.resolve_chunk_id(cid, retrieved_chunks)
                if matched_id:
                    resolved_cids.append(matched_id)
                else:
                    invalid_citations.append(cid)

            claim.citation_ids = resolved_cids

            if invalid_citations:
                claim.grounded = False
                issues.append(f"Claim cites non-retrieved chunk(s) {invalid_citations}.")
                continue

            # 1. Per-chunk Factual Contradiction Check
            has_contradiction = False
            for cid in resolved_cids:
                chunk_obj = chunk_obj_map.get(cid)
                if chunk_obj:
                    contra_err = check_claim_contradictions(claim.text, chunk_obj)
                    if contra_err:
                        claim.grounded = False
                        has_contradiction = True
                        issues.append(f"Factual Contradiction: {contra_err}")
                        break

            if has_contradiction:
                continue

            # 2. Version Alignment Check for cited chunks
            version_mismatch = False
            claim_lower = claim.text.lower()
            for cid in resolved_cids:
                chunk_obj = chunk_obj_map.get(cid)
                if not chunk_obj or not chunk_obj.version:
                    continue
                c_ver = chunk_obj.version.strip()
                if c_ver == "1.0":
                    if ("version 2.0" in claim_lower or "v2.0" in claim_lower) and not (
                        "version 1.0" in claim_lower or "v1.0" in claim_lower or "both versions" in claim_lower
                    ):
                        claim.grounded = False
                        version_mismatch = True
                        issues.append(
                            f"Version mismatch: Claim references version 2.0 but cites version 1.0 chunk '{cid}'."
                        )
                        break
                elif c_ver == "2.0":
                    if ("version 1.0" in claim_lower or "v1.0" in claim_lower) and not (
                        "version 2.0" in claim_lower or "v2.0" in claim_lower or "both versions" in claim_lower
                    ):
                        claim.grounded = False
                        version_mismatch = True
                        issues.append(
                            f"Version mismatch: Claim references version 1.0 but cites version 2.0 chunk '{cid}'."
                        )
                        break

            if version_mismatch:
                continue

            # 3. Gather evidence text from cited chunks and check token support
            cited_texts = [chunk_evidence_map[cid] for cid in resolved_cids if cid in chunk_evidence_map]
            combined_cited_text = " ".join(cited_texts)
            content_words = self._extract_content_words(claim.text)

            if not content_words:
                claim.grounded = True
                grounded_count += 1
                continue

            # Check what proportion of content words exist in cited chunk text/metadata
            missing_words = [
                w for w in content_words
                if not self._token_matches_text(w, combined_cited_text)
            ]
            support_ratio = 1.0 - (len(missing_words) / len(content_words))

            # Allow moderate variation (synonyms/rephrasing), but require >= 60% support
            if support_ratio >= 0.60:
                claim.grounded = True
                grounded_count += 1
            else:
                claim.grounded = False
                issues.append(
                    f"Claim has low textual support ({support_ratio:.0%}) in cited chunks: "
                    f"unmatched terms: {missing_words[:5]}"
                )

        score = grounded_count / len(claims) if claims else 1.0
        return claims, score, issues


    def _token_matches_text(self, token: str, text: str) -> bool:
        """Check if token or its simple inflections/stems appear in the text."""
        if token in text:
            return True
        # Handle plurals (ports -> port, components -> component, mappings -> mapping)
        if token.endswith("ies") and (token[:-3] + "y") in text:
            return True
        if token.endswith("es") and token[:-2] in text:
            return True
        if token.endswith("s") and len(token) > 3 and token[:-1] in text:
            return True
        # Handle reverse plural (text has ports, claim has port)
        if (token + "s") in text or (token + "es") in text:
            return True
        return False

    def _extract_content_words(self, text: str) -> List[str]:
        """Extract meaningful lowercased alphanumeric tokens excluding stopwords and reporting terms."""
        tokens = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
        return [t for t in tokens if t not in ALL_EVAL_STOPWORDS]
