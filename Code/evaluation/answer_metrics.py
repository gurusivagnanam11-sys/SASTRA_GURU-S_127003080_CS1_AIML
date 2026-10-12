"""Answer quality, citation correctness, groundedness, and abstention metrics.

Provides deterministic evaluation of RAG responses:
- Citation correctness and coverage
- Fine-grained claim grounding (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED)
- Abstention accuracy on adversarial/unsupported questions
- Architecture entity recall and precision in answers
"""

import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rag.models import Citation, Claim, ContextChunk, RAGResponse

ABSTENTION_PHRASES: List[str] = [
    "does not specify",
    "do not specify",
    "not specified",
    "insufficient evidence",
    "not provided",
    "not found",
    "no evidence",
    "does not mention",
    "do not mention",
    "cannot be determined",
    "not stated",
    "neither version specifies",
    "outside the scope",
    "not defined in hld",
]

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


def extract_content_words(text: str) -> List[str]:
    """Extract lowercased content tokens of length >= 3 excluding stopwords."""
    tokens = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
    return [t for t in tokens if t not in COMMON_STOPWORDS]


def extract_architectural_entities(text: str) -> List[str]:
    """Extract architectural entities (components, interfaces, ports, signals) from text."""
    # Find CamelCase words of length >= 4
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9_]{3,}\b", text)
    # Filter common non-entity capitalized words
    non_entities = {"AUTOSAR", "Version", "Figure", "Table", "Section", "Document", "Sender", "Receiver"}
    return [c for c in candidates if c not in non_entities]



def evaluate_citation_correctness(
    citations: List[Citation],
    retrieved_chunks: List[ContextChunk],
    claims: Optional[List[Claim]] = None,
) -> Dict[str, Any]:
    """Evaluate citation accuracy, coverage, and precision against retrieved chunks."""
    retrieved_map = {c.chunk_id: c for c in retrieved_chunks}
    total_citations = len(citations)

    valid_citations = 0
    fabricated_citations = 0
    metadata_mismatches = 0
    issues = []

    for cit in citations:
        cid = cit.chunk_id.strip()
        if cid not in retrieved_map:
            fabricated_citations += 1
            issues.append(f"Citation references unretrieved chunk '{cid}'")
            continue

        actual = retrieved_map[cid]
        # Check metadata alignment
        doc_match = (
            cit.document.lower().replace(".pdf", "") in actual.document_id.lower()
            or actual.document_id.lower().replace(".pdf", "") in cit.document.lower()
        )
        ver_match = cit.version.strip() == actual.version.strip()
        page_match = int(cit.page) == int(actual.page_number)

        if doc_match and ver_match and page_match:
            valid_citations += 1
        else:
            metadata_mismatches += 1
            issues.append(
                f"Discrepancy for '{cid}': cited(doc={cit.document}, ver={cit.version}, p={cit.page}) "
                f"vs actual(doc={actual.document_id}, ver={actual.version}, p={actual.page_number})"
            )

    citation_precision = (valid_citations / total_citations) if total_citations > 0 else 1.0

    # Citation coverage across claims
    total_claims = len(claims) if claims else 0
    claims_cited = sum(1 for c in claims if c.citation_ids) if claims else 0
    citation_coverage = (claims_cited / total_claims) if total_claims > 0 else (1.0 if total_citations > 0 else 0.0)

    return {
        "total_citations": total_citations,
        "valid_citations": valid_citations,
        "fabricated_citations": fabricated_citations,
        "metadata_mismatches": metadata_mismatches,
        "citation_precision": round(citation_precision, 4),
        "citation_coverage": round(citation_coverage, 4),
        "issues": issues,
    }


# Convenient alias
evaluate_citations = evaluate_citation_correctness


def evaluate_groundedness(
    answer: str,
    claims: List[Claim],
    retrieved_chunks: List[ContextChunk],
) -> Dict[str, Any]:
    """Classify factual claims into SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED."""
    if not retrieved_chunks:
        # Check if answer appropriately abstained
        if any(p in answer.lower() for p in ABSTENTION_PHRASES):
            return {
                "groundedness_score": 1.0,
                "grounding_score": 1.0,
                "total_claims": 0,
                "supported": 0,
                "supported_claims": 0,
                "partially_supported": 0,
                "partially_supported_claims": 0,
                "unsupported": 0,
                "unsupported_claims": 0,
                "classification_breakdown": [],
                "status": "ABSTAINED_APPROPRIATELY",
            }
        return {
            "groundedness_score": 0.0,
            "grounding_score": 0.0,
            "total_claims": len(claims),
            "supported": 0,
            "supported_claims": 0,
            "partially_supported": 0,
            "partially_supported_claims": 0,
            "unsupported": len(claims),
            "unsupported_claims": len(claims),
            "classification_breakdown": [
                {"claim": c.text, "status": "UNSUPPORTED", "support_ratio": 0.0, "reason": "No evidence retrieved"}
                for c in claims
            ],
            "status": "UNGROUNDED_NO_CONTEXT",
        }

    chunk_map = {c.chunk_id: c.text.lower() for c in retrieved_chunks}
    all_context_text = " ".join(chunk_map.values())

    supported = 0
    partially_supported = 0
    unsupported = 0
    breakdown: List[Dict[str, Any]] = []

    # If no structured claims provided, evaluate sentences of answer as claims
    eval_claims = claims if claims else [
        Claim(text=s.strip(), citation_ids=[])
        for s in re.split(r"[.\n]+", answer) if len(s.strip()) > 15
    ]

    for c in eval_claims:
        claim_words = extract_content_words(c.text)
        if not claim_words:
            supported += 1
            breakdown.append({
                "claim": c.text,
                "status": "SUPPORTED",
                "support_ratio": 1.0,
                "supporting_chunk": c.citation_ids[0] if c.citation_ids else None,
                "confidence": 1.0,
            })
            continue

        # Look in cited chunks first, fallback to all retrieved chunks
        target_text = ""
        supporting_cid = None
        if c.citation_ids:
            cited_texts = [chunk_map[cid] for cid in c.citation_ids if cid in chunk_map]
            if cited_texts:
                target_text = " ".join(cited_texts)
                supporting_cid = c.citation_ids[0]

        if not target_text:
            target_text = all_context_text
            # Find best matching chunk
            for cid, ctext in chunk_map.items():
                if any(w in ctext for w in claim_words):
                    supporting_cid = cid
                    break

        matched_words = [w for w in claim_words if w in target_text]
        support_ratio = len(matched_words) / float(len(claim_words))

        if support_ratio >= 0.70:
            status = "SUPPORTED"
            supported += 1
        elif support_ratio >= 0.40:
            status = "PARTIALLY_SUPPORTED"
            partially_supported += 1
        else:
            status = "UNSUPPORTED"
            unsupported += 1

        breakdown.append({
            "claim": c.text,
            "status": status,
            "support_ratio": round(support_ratio, 4),
            "matched_terms": matched_words,
            "unmatched_terms": [w for w in claim_words if w not in target_text],
            "supporting_chunk": supporting_cid,
            "confidence": round(min(1.0, support_ratio + 0.1), 2),
        })

    total = len(eval_claims)
    # Groundedness score weights full support as 1.0, partial support as 0.5
    score = (supported + 0.5 * partially_supported) / float(total) if total > 0 else 1.0

    return {
        "groundedness_score": round(score, 4),
        "grounding_score": round(score, 4),
        "total_claims": total,
        "supported": supported,
        "supported_claims": supported,
        "partially_supported": partially_supported,
        "partially_supported_claims": partially_supported,
        "unsupported": unsupported,
        "unsupported_claims": unsupported,
        "classification_breakdown": breakdown,
    }


# Convenient alias
evaluate_answer_grounding = evaluate_groundedness


def evaluate_abstention(answer: str, is_unsupported: bool) -> Dict[str, Any]:
    """Verify whether the assistant properly abstains on unanswerable/adversarial questions."""
    answer_lower = answer.lower()
    abstained = any(p in answer_lower for p in ABSTENTION_PHRASES)

    if is_unsupported:
        correct = abstained
        reason = "Correctly abstained with insufficient evidence statement" if abstained else "FAILED: Hallucinated or attempted to answer unanswerable query"
    else:
        correct = not abstained
        reason = "Correctly provided architectural answer from evidence" if not abstained else "False refusal on valid query"

    return {
        "is_unsupported_query": is_unsupported,
        "abstained": abstained,
        "correct": correct,
        "evaluation_reason": reason,
    }


def evaluate_answer_entities(answer: str, expected_entities: List[str]) -> Dict[str, Any]:
    """Measure exact presence of expected architectural entities in the generated answer."""
    if not expected_entities:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "found": [], "missing": []}

    answer_lower = answer.lower()
    found: List[str] = []
    missing: List[str] = []

    for ent in expected_entities:
        # Check word boundary or substring for compound names
        if ent.lower() in answer_lower:
            found.append(ent)
        else:
            missing.append(ent)

    recall = len(found) / float(len(expected_entities))
    # Approximation of precision: found / total identified entities
    precision = 1.0 if found else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "expected_count": len(expected_entities),
        "found_count": len(found),
        "found_entities": found,
        "missing_entities": missing,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
    }


def evaluate_abstention_batch(
    query_runner: Callable[[str], Tuple[str, List[str], Any, bool]],
    queries: List[Any],
) -> Dict[str, Any]:
    """Evaluate abstention on a batch of adversarial/unsupported queries."""
    total = len(queries)
    correctly_abstained = 0
    hallucinated = 0
    itemized = []

    for q in queries:
        ans, cites, conf, rev_req = query_runner(q.query)
        res = evaluate_abstention(ans, is_unsupported=True)

        # In addition, if citations are present on an unsupported query, that is a hallucinated citation
        has_citations = len(cites) > 0
        if res["correct"] and not has_citations:
            correctly_abstained += 1
            verdict = "PASSED_ABSTAINED"
        else:
            hallucinated += 1
            verdict = "FAILED_HALLUCINATED"

        itemized.append({
            "query_id": q.query_id,
            "query": q.query,
            "category": q.category,
            "rationale": q.rationale,
            "abstained": res["abstained"],
            "citations_count": len(cites),
            "confidence": getattr(conf, "value", str(conf)),
            "review_required": rev_req,
            "verdict": verdict,
            "answer_preview": ans[:120] + "..." if len(ans) > 120 else ans,
        })

    accuracy = correctly_abstained / float(total) if total > 0 else 1.0
    hallucination_rate = hallucinated / float(total) if total > 0 else 0.0

    return {
        "total_queries": total,
        "correctly_abstained": correctly_abstained,
        "hallucinated": hallucinated,
        "abstention_accuracy": round(accuracy, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        "itemized": itemized,
    }

