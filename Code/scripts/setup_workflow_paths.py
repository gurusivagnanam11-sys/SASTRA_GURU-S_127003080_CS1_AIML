import os
import pymupdf
from pathlib import Path

# Paths
DOC_DIR = Path("C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/Documentation")
DOC_DIR.mkdir(parents=True, exist_ok=True)
SVG_PATH = DOC_DIR / "RAG_Workflow.svg"
PNG_PATH = DOC_DIR / "RAG_Workflow.png"
MMD_PATH = DOC_DIR / "RAG_Workflow.mmd"

print("Documentation directory verified:", DOC_DIR)
