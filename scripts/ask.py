"""CLI tool for testing grounded RAG question answering in AUTOSAR HLD Assistant.

Usage:
    python scripts/ask.py "What interface carries VehicleSpeed?"
    python scripts/ask.py "What components are associated with VehicleControl?" --version 2.0
    python scripts/ask.py "What changed between version 1.0 and version 2.0?" --provider mock
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logging_config import setup_logging
from rag.pipeline import RAGPipeline
from rag.llm_provider import get_llm_provider


def main():
    parser = argparse.ArgumentParser(
        description="Grounded Question Answering over AUTOSAR High-Level Design (HLD) specifications."
    )
    parser.add_argument("question", type=str, help="Architectural question to answer")
    parser.add_argument("--version", type=str, default=None, help="Filter by document version (e.g., '1.0' or '2.0')")
    parser.add_argument("--project", type=str, default=None, help="Filter by project ID")
    parser.add_argument("--chunk-type", type=str, default=None, help="Filter by chunk type ('component', 'interface', 'port', etc.)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of evidence chunks to retrieve (default: 5)")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider: 'mock', 'openai', or 'gemini'")
    parser.add_argument("--json", action="store_true", help="Output full response as structured JSON")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        setup_logging(log_level=logging.INFO)
    else:
        # Suppress noisy logs for clean CLI output
        logging.basicConfig(level=logging.WARNING)

    # Initialize provider and pipeline
    llm = get_llm_provider(args.provider)
    pipeline = RAGPipeline(llm_provider=llm, top_k=args.top_k)

    response = pipeline.ask(
        question=args.question,
        project=args.project,
        document_version=args.version,
        chunk_type=args.chunk_type,
        top_k=args.top_k,
    )

    if args.json:
        print(response.model_dump_json(indent=2))
        return

    # Formatted human-readable output
    print(f"\n{'=' * 65}")
    print("AUTOSAR HLD ASSISTANT - GROUNDED RAG Q&A")
    print(f"{'=' * 65}")
    print(f"\nQUESTION:\n{response.question}\n")
    print(f"ANSWER:\n{response.answer}\n")

    print("SOURCES:")
    if response.citations:
        for i, cit in enumerate(response.citations, 1):
            valid_flag = "[VALID]" if cit.valid else "[INVALID]"
            print(f"{i}. {cit.document}")
            print(f"   Version: {cit.version}")
            print(f"   Page: {cit.page}")
            print(f"   Section: {cit.section}")
            print(f"   Chunk ID: {cit.chunk_id}")
            print(f"   Status: {valid_flag} ({cit.validation_notes or 'OK'})")
    else:
        print("   None (No citations returned)")

    print(f"\nCONFIDENCE:\n{response.confidence.value.capitalize()}")

    print("\nLIMITATIONS:")
    if response.limitations:
        for lim in response.limitations:
            print(f"- {lim}")
    else:
        print("None")

    print(f"\nREVIEW REQUIRED:\n{response.review_required}")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
