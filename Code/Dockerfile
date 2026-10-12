# ==============================================================================
# AUTOSAR HLD Intelligence & Traceability Assistant - Production Dockerfile
# CPU-only container image using Gemini Cloud for LLM inference.
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive \
    LLM_PROVIDER=gemini \
    USE_TF=0 \
    USE_TORCH=1 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    CUDA_VISIBLE_DEVICES="" \
    HF_HOME=/app/cache/huggingface

WORKDIR /app

# Install OS dependencies:
# - tesseract-ocr & tesseract-ocr-eng: System OCR engine and English training data
# - curl: Used for container healthchecks
# - libgomp1: OpenMP runtime required by faiss-cpu on Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Verify Tesseract binary is discoverable in PATH
RUN which tesseract && tesseract --version

# Create non-root application user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/cache/huggingface /app/data && \
    chown -R appuser:appuser /app

# Copy dependency specifications first to maximize Docker layer caching
COPY requirements.txt .

# Install CPU-only PyTorch first to avoid heavy CUDA packages
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application Python dependencies (including pytesseract, Pillow, python-dotenv)
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download BAAI/bge-small-en-v1.5 embedding model into image layer
# This avoids downloading model weights repeatedly on every container start
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')" && \
    chown -R appuser:appuser /app/cache

# Copy application source code
COPY . .

# Ensure data subdirectories exist and permissions are set
RUN mkdir -p /app/data/raw /app/data/processed /app/data/indexes && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Default command runs FastAPI backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
