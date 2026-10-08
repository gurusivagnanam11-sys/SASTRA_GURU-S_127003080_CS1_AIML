"""Lightweight deterministic grounding checker for AUTOSAR HLD RAG outputs.

Compares claims and answer content against retrieved evidence chunks to detect
unsupported statements and flag them for human engineer review.
"""

import logging
import re
from typing import Dict, List, Set, Tuple
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


class GroundingChecker:
    """Deterministic grounding verification comparing claims to retrieved evidence."""

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

        chunk_text_map: Dict[str, str] = {c.chunk_id: c.text for c in retrieved_chunks}
        all_retrieved_text = " ".join(c.text.lower() for c in retrieved_chunks)

        if not claims:
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

            # Gather text of all cited chunks
            cited_texts = []
            invalid_citations = []
            for cid in claim.citation_ids:
                if cid in chunk_text_map:
                    cited_texts.append(chunk_text_map[cid].lower())
                else:
                    invalid_citations.append(cid)

            if invalid_citations:
                claim.grounded = False
                issues.append(f"Claim cites non-retrieved chunk(s) {invalid_citations}.")
                continue

            combined_cited_text = " ".join(cited_texts)
            content_words = self._extract_content_words(claim.text)

            if not content_words:
                claim.grounded = True
                grounded_count += 1
                continue

            # Check what proportion of content words exist in cited chunk text
            missing_words = [w for w in content_words if w not in combined_cited_text]
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

    def _extract_content_words(self, text: str) -> List[str]:
        """Extract meaningful lowercased alphanumeric tokens excluding stopwords."""
        tokens = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
        return [t for t in tokens if t not in COMMON_STOPWORDS]
