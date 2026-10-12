"""Export utilities for AUTOSAR HLD Assistant Q&A responses.

Supports exporting grounded RAG responses to formatted JSON and Markdown.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

from rag.models import ConfidenceLevel, RAGResponse


def export_response_to_json(
    response: RAGResponse,
    provider: str = "ollama",
    output_path: Optional[Union[str, Path]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Export RAGResponse to a structured JSON string and optionally save to file.

    Includes full provenance, validation status, timestamps, and provider details.
    """
    export_dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "question": response.question,
        "answer": response.answer,
        "confidence": response.confidence.value if isinstance(response.confidence, ConfidenceLevel) else str(response.confidence),
        "review_required": response.review_required,
        "grounding_score": response.grounding_score,
        "retrieved_chunks_count": response.retrieved_chunks_count,
        "metadata_filter_applied": response.metadata_filter_applied,
        "claims": [claim.model_dump() for claim in response.claims],
        "citations": [cit.model_dump() for cit in response.citations],
        "limitations": response.limitations,
    }

    if extra_metadata:
        export_dict["metadata"] = extra_metadata

    json_str = json.dumps(export_dict, indent=2, ensure_ascii=False)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json_str, encoding="utf-8")

    return json_str


def export_response_to_markdown(
    response: RAGResponse,
    provider: str = "ollama",
    output_path: Optional[Union[str, Path]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Export RAGResponse to an engineering-ready Markdown report and optionally save to file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    confidence_str = (
        response.confidence.value.upper()
        if isinstance(response.confidence, ConfidenceLevel)
        else str(response.confidence).upper()
    )

    review_badge = "**REVIEW REQUIRED**" if response.review_required else "APPROVED / LOW RISK"

    lines = [
        "# AUTOSAR HLD Architecture Q&A Report",
        "",
        f"- **Generated:** {timestamp}",
        f"- **LLM Provider:** `{provider}`",
        f"- **Confidence:** `{confidence_str}`",
        f"- **Review Status:** {review_badge}",
        f"- **Retrieved Chunks:** {response.retrieved_chunks_count}",
    ]

    if response.grounding_score is not None:
        lines.append(f"- **Grounding Score:** `{response.grounding_score:.2f}`")

    if response.metadata_filter_applied:
        filters = ", ".join(f"{k}={v}" for k, v in response.metadata_filter_applied.items())
        lines.append(f"- **Filters Applied:** `{filters}`")

    lines.extend([
        "",
        "## Query",
        "",
        f"> {response.question}",
        "",
        "## Grounded Answer",
        "",
        response.answer,
        "",
        "## Architectural Claims",
        "",
    ])

    if response.claims:
        for idx, claim in enumerate(response.claims, start=1):
            c_ids = ", ".join(f"`{cid}`" for cid in claim.citation_ids) if claim.citation_ids else "None"
            grounded_label = "[Grounded]" if claim.grounded else "[Ungrounded]"
            lines.append(f"{idx}. {claim.text} {grounded_label} (Citations: {c_ids})")
    else:
        lines.append("*No individual claims segmented.*")

    lines.extend([
        "",
        "## Provenance Citations",
        "",
    ])

    if response.citations:
        lines.append("| Chunk ID | Document | Version | Page | Section | Validation Status |")
        lines.append("|---|---|---|---|---|---|")
        for cit in response.citations:
            val_status = "[VALID]" if cit.valid else "[UNVERIFIED]"
            lines.append(
                f"| `{cit.chunk_id}` | `{cit.document}` | {cit.version} | p. {cit.page} | Sec {cit.section} | {val_status} |"
            )
    else:
        lines.append("*No citations provided.*")

    if response.limitations:
        lines.extend([
            "",
            "## Limitations & Warnings",
            "",
        ])
        for lim in response.limitations:
            lines.append(f"- {lim}")

    lines.append("")
    md_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(md_str, encoding="utf-8")

    return md_str
