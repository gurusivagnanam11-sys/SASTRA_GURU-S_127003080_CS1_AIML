import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, path, expected_status=200, json=None, params=None):
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            res = requests.get(url, params=params)
        elif method == "POST":
            res = requests.post(url, json=json)
        print(f"{method} {path} -> {res.status_code}")
        if res.status_code != expected_status:
            print(f"FAILED: Expected {expected_status}, got {res.status_code}. Response: {res.text}")
            return False
        return True
    except Exception as e:
        print(f"FAILED: {method} {path} -> Error: {e}")
        return False

def main():
    success = True
    print("Testing endpoints...")
    success &= test_endpoint("GET", "/health")
    
    # RAG Query
    q_data = {"question": "What components depend on VehicleControl?", "version": "1.0"}
    success &= test_endpoint("POST", "/query", json=q_data)
    
    # Reports
    success &= test_endpoint("GET", "/reports/component", params={"component_name": "VehicleControl", "version": "1.0"})
    success &= test_endpoint("GET", "/reports/validation", params={"version": "1.0"})
    success &= test_endpoint("GET", "/reports/revision", params={"version_from": "1.0", "version_to": "2.0"})
    success &= test_endpoint("GET", "/reports/impact", params={"component_name": "VehicleControl", "version": "2.0"})
    
    # Entities / Architecture
    success &= test_endpoint("GET", "/entities/components", params={"version": "1.0"})
    success &= test_endpoint("GET", "/entities/interfaces", params={"version": "1.0"})
    success &= test_endpoint("GET", "/entities/signals", params={"version": "1.0"})
    
    success &= test_endpoint("GET", "/architecture/flows", params={"version": "1.0"})
    success &= test_endpoint("GET", "/architecture/graph", params={"version": "1.0"})
    success &= test_endpoint("GET", "/architecture/validate", params={"version": "1.0"})
    
    # Diff
    success &= test_endpoint("GET", "/architecture/diff", params={"version_from": "1.0", "version_to": "2.0"})
    
    # Impact
    success &= test_endpoint("GET", "/architecture/impact", params={"component_name": "VehicleControl", "version": "2.0"})
    
    # Governance
    gov_data = {"document_id": "test_doc", "version": "1.0", "user": "test_user", "action": "APPROVE"}
    success &= test_endpoint("POST", "/governance/transition", json=gov_data)
    success &= test_endpoint("GET", "/governance/audit", params={"document_id": "test_doc"})
    
    # Review
    rev_data = {"report_id": "rep_123", "document_id": "test_doc", "version": "1.0", "reviewer": "test_user", "decision": "ENGINEER_APPROVED"}
    success &= test_endpoint("POST", "/review", json=rev_data)
    success &= test_endpoint("GET", "/reviews")

    if not success:
        sys.exit(1)
    print("All endpoints tested successfully.")

if __name__ == "__main__":
    main()
