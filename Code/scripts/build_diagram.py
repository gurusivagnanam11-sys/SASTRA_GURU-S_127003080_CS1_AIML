# Diagram generator for AUTOSAR HLD Intelligence Assistant
import os
import pymupdf
from pathlib import Path

BASE_DIR = Path('C:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant')
DOC_DIR = BASE_DIR / 'Documentation'
DOC_DIR.mkdir(parents=True, exist_ok=True)
