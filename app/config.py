"""Centralized configuration for the AUTOSAR HLD Assistant.

All paths are relative to PROJECT_ROOT. No hard-coded absolute paths.
No API keys or credentials.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root is parent of app/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Centralized environment variable loading from PROJECT_ROOT / .env
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger(__name__)
logger.info(
    "Configuration initialized. GEMINI_API_KEY available: %s",
    bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
)

# Ensure PyTorch is used for transformers and sentence-transformers
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
if not os.environ.get("HF_HUB_ONLINE"):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "indexes"
FIXTURES_DIR = PROJECT_ROOT / "fixtures"

# Database
DB_PATH = DATA_DIR / "autosar_hld.db"

# Embedding configuration
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Retrieval configuration
TOP_K = int(os.environ.get("TOP_K", "5"))

# Chunking configuration
CHUNK_MAX_CHARS = int(os.environ.get("CHUNK_MAX_CHARS", "1500"))

# Default project ID
PROJECT_ID = os.environ.get("PROJECT_ID", "demo_project")

# LLM configuration (free-tier only policy: Ollama, Gemini, Mock)
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")

# Gemini Free Tier
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")

# Local Ollama
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")

# LLM generation parameters
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.1"))
LLM_MAX_OUTPUT_TOKENS = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "2000"))
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "180"))


def ensure_directories():
    """Create required data directories if they don't exist."""
    for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, INDEX_DIR]:
        d.mkdir(parents=True, exist_ok=True)
