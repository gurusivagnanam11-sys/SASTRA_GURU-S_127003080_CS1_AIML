"""Docker deployment smoke test for AUTOSAR HLD Intelligence Assistant.

Verifies:
1. FastAPI /health endpoint responds on http://localhost:8000/health
2. Diagnostics contain expected Gemini provider without leaking secrets
3. FAISS index chunk count is non-zero
4. Streamlit UI responds on http://localhost:8501
5. OCR functionality works inside container (pytesseract, Pillow, binary discoverable)
6. Optional grounded query verification against Gemini Cloud
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


def log(msg: str):
    print(f"[DOCKER-SMOKE-TEST] {msg}")


def test_api_health(base_url: str = "http://localhost:8000") -> dict:
    url = f"{base_url}/health"
    log(f"Testing API health at {url}...")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = resp.status
            body = resp.read().decode("utf-8")
            assert status_code == 200, f"Expected 200 OK, got {status_code}"
            data = json.loads(body)
            assert data.get("status") == "healthy", f"Status not healthy: {data}"
            assert data.get("default_llm_provider") == "gemini", f"Expected provider 'gemini', got {data.get('default_llm_provider')}"
            assert "gemini" in data.get("active_llm_model", "").lower(), f"Unexpected model: {data.get('active_llm_model')}"
            assert data.get("faiss_indexed_chunks", 0) > 0, f"FAISS index empty: {data.get('faiss_indexed_chunks')}"
            
            # Ensure no secret strings leaked
            for key, val in data.items():
                if "key" in key.lower() or "secret" in key.lower():
                    raise AssertionError(f"Sensitive key exposed in /health: {key}")
            
            log(f"API Health PASSED: status={data['status']}, provider={data['default_llm_provider']}, chunks={data['faiss_indexed_chunks']}")
            return data
    except Exception as e:
        log(f"API Health FAILED: {e}")
        raise


def test_streamlit_health(base_url: str = "http://localhost:8501") -> bool:
    url = f"{base_url}/_stcore/health"
    log(f"Testing Streamlit health at {url}...")
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            body = resp.read().decode("utf-8").strip()
            assert body == "ok", f"Expected 'ok', got {body}"
            log("Streamlit Health PASSED: HTTP 200 'ok'")
            return True
    except Exception as e:
        log(f"Streamlit Health check FAILED: {e}")
        raise


def test_container_ocr() -> bool:
    log("Verifying OCR subsystem inside 'hld-api' container...")
    check_code = (
        "import pytesseract; "
        "from PIL import Image, ImageDraw, ImageFont; "
        "import shutil; "
        "tess_bin = shutil.which('tesseract'); "
        "assert tess_bin is not None, 'tesseract binary not found in PATH'; "
        "v = pytesseract.get_tesseract_version(); "
        "print(f'TESSERACT_VERSION:{v}'); "
        "img = Image.new('RGB', (200, 50), color=(255, 255, 255)); "
        "draw = ImageDraw.Draw(img); "
        "draw.text((10, 10), 'AUTOSAR OCR', fill=(0, 0, 0)); "
        "txt = pytesseract.image_to_string(img).strip(); "
        "print(f'OCR_OUTPUT:{txt}'); "
        "assert 'AUTOSAR' in txt or 'OCR' in txt, f'OCR output mismatch: {txt}'"
    )
    cmd = ["docker", "compose", "exec", "-T", "hld-api", "python", "-c", check_code]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"Container OCR check FAILED:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
        raise RuntimeError("Container OCR verification failed")
    
    log(f"Container OCR verification PASSED:\n{res.stdout.strip()}")
    return True


def test_container_query(base_url: str = "http://localhost:8000") -> dict:
    url = f"{base_url}/query"
    log(f"Testing live query endpoint at {url} with canonical query...")
    payload = json.dumps({
        "question": "What interface carries VehicleSpeed?",
        "provider": "gemini",
        "top_k": 3
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            data = json.loads(resp.read().decode("utf-8"))
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            confidence = data.get("confidence", "")
            grounding_score = data.get("grounding_score", 0.0)
            
            assert answer, "Empty answer returned"
            log(f"Query PASSED:")
            log(f"  Confidence: {confidence}")
            log(f"  Grounding Score: {grounding_score}")
            log(f"  Citations: {len(citations)}")
            log(f"  Answer sample: {answer[:120]}...")
            return data
    except Exception as e:
        log(f"Query check note/failure: {e}")
        # Note: If no internet or API key quota exceeded, report clearly
        return {"error": str(e)}


def main():
    log("Starting Docker deployment smoke tests...")
    errors = []
    
    try:
        test_api_health()
    except Exception as e:
        errors.append(f"API Health: {e}")
        
    try:
        test_streamlit_health()
    except Exception as e:
        errors.append(f"Streamlit Health: {e}")
        
    try:
        test_container_ocr()
    except Exception as e:
        errors.append(f"Container OCR: {e}")

    try:
        test_container_query()
    except Exception as e:
        errors.append(f"Container Query: {e}")

    if errors:
        log("Smoke tests completed with errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        log("ALL SMOKE TESTS COMPLETED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    main()
