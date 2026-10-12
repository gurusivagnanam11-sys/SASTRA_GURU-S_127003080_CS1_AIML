"""Tests for Docker deployment configuration and OCR subsystem.

Validates:
1. Dockerfile contains required CPU-only settings, Tesseract packages, and no GPU/Ollama dependencies.
2. docker-compose.yml defines required services, ports, volumes, networks, and environment variables.
3. OCR imports (pytesseract, PIL) work and Tesseract initialization/fallback behaves safely.
4. Gemini configuration behaves as expected without logging secrets.
"""

import os
from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_contents():
    """Verify Dockerfile adheres to all CPU-only, Gemini, and OCR constraints."""
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile must exist at project root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Base image
    assert "python:3.12-slim" in content, "Must use python:3.12-slim base image"

    # CPU-only constraints
    assert "CUDA" not in content or 'CUDA_VISIBLE_DEVICES=""' in content
    assert "nvidia" not in content.lower(), "Must NOT install NVIDIA packages"
    assert "ollama" not in content.lower() or "langchain-ollama" in content.lower(), "Must NOT install Ollama daemon in Docker"

    # OCR packages
    assert "tesseract-ocr" in content, "Must install tesseract-ocr system package"
    assert "tesseract-ocr-eng" in content, "Must install tesseract-ocr-eng system package"

    # Pre-caching BGE model
    assert "BAAI/bge-small-en-v1.5" in content, "Must pre-cache BGE model in Docker layer"

    # Non-root user
    assert "appuser" in content, "Must configure non-root appuser"


def test_docker_compose_configuration():
    """Verify docker-compose.yml defines services, ports, environment, and persistent volumes."""
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at project root"

    content = compose_path.read_text(encoding="utf-8")

    # Services
    assert "hld-api:" in content, "Must define hld-api service"
    assert "hld-ui:" in content, "Must define hld-ui service"

    # Ports
    assert '"8000:8000"' in content or "'8000:8000'" in content, "Must expose port 8000 for FastAPI"
    assert '"8501:8501"' in content or "'8501:8501'" in content, "Must expose port 8501 for Streamlit"

    # Environment
    assert "LLM_PROVIDER" in content
    assert "GEMINI_API_KEY" in content
    assert "GEMINI_MODEL" in content
    assert "OLLAMA_BASE_URL" in content
    assert "OLLAMA_MODEL" in content
    assert "host.docker.internal" in content

    # Volumes
    assert "./data:/app/data" in content, "Must mount ./data:/app/data for persistence"

    # Healthchecks
    assert "health" in content, "Must define healthchecks"

    # No GPU/CUDA/Ollama service in compose
    assert "ollama:" not in content, "Ollama must not be a service in docker-compose.yml"
    assert "gpu" not in content.lower(), "Must not configure GPU in docker-compose.yml"


def test_ocr_packages_importable():
    """Verify pytesseract and PIL (Pillow) are importable and functional."""
    import pytesseract
    from PIL import Image

    assert pytesseract is not None
    assert Image is not None

    # Verify dummy image creation for OCR
    img = Image.new("RGB", (100, 30), color=(255, 255, 255))
    assert img.size == (100, 30)


def test_ocr_fallback_behavior():
    """Verify pdf_parser OCR fallback function executes safely."""
    from ingestion.pdf_parser import _ocr_page
    from unittest.mock import MagicMock

    mock_page = MagicMock()
    mock_pix = MagicMock()
    mock_pix.n = 3
    mock_pix.alpha = 0
    mock_pix.width = 10
    mock_pix.height = 10
    mock_pix.samples = b"\x00" * 300
    mock_page.get_pixmap.return_value = mock_pix

    # Should execute without throwing unhandled exceptions
    result = _ocr_page(mock_page)
    assert isinstance(result, str)


def test_env_example_contains_no_secrets():
    """Verify .env.example contains only placeholders and no plaintext secrets."""
    env_example = PROJECT_ROOT / ".env.example"
    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")

    assert "GEMINI_API_KEY=\n" in content or "GEMINI_API_KEY=" in content
    for line in content.splitlines():
        if line.startswith("GEMINI_API_KEY="):
            value = line.split("=", 1)[1].strip()
            assert value == "", "GEMINI_API_KEY in .env.example must be empty"
