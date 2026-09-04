import requests
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.security import create_access_token

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("=== 1. Check Health ===")
    res = requests.get(f"{BASE_URL}/health")
    print(f"Health Status: {res.status_code}, Body: {res.json()}")

    print("\n=== 2. Create Auth Token for Doctor (ID: 17 - Dr. Saurav Madake) ===")
    token = create_access_token(subject="17", role="doctor")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("Doctor token successfully generated.")

    print("\n=== 3. Requirement 11: Real Gemini Connectivity Test ===")
    prompt_11 = "Explain in two sentences what a hospital care plan is."
    req_11 = {
        "agent_type": "clinical_coordinator",
        "prompt": prompt_11
    }
    print(f"Sending prompt: {prompt_11}")
    q11_res = requests.post(f"{BASE_URL}/api/v1/agents/query", json=req_11, headers=headers, timeout=60)
    print(f"Req 11 Status: {q11_res.status_code}")
    if q11_res.status_code == 200:
        d = q11_res.json()
        print(f"Model Used: {d.get('model_used') or d.get('model_name')}")
        print(f"Latency: {d.get('execution_time_ms')}ms")
        print(f"Query ID: {d.get('query_id')}")
        ans = d.get('answer') or ''
        print(f"Real Gemini Response:\n{ans}")
    else:
        print(f"Req 11 Error: {q11_res.text}")

    print("\n=== 4. Requirement 12: Real Autonomous AI Agent Care Coordination Test ===")
    prompt_12 = "Summarize the general purpose of a hospital care plan and list three common sections it may contain."
    req_12 = {
        "agent_type": "clinical_coordinator",
        "prompt": prompt_12
    }
    print(f"Sending prompt: {prompt_12}")
    q12_res = requests.post(f"{BASE_URL}/api/v1/agents/query", json=req_12, headers=headers, timeout=60)
    print(f"Req 12 Status: {q12_res.status_code}")
    if q12_res.status_code == 200:
        d = q12_res.json()
        print(f"Model Used: {d.get('model_used') or d.get('model_name')}")
        print(f"Latency: {d.get('execution_time_ms')}ms")
        print(f"Query ID: {d.get('query_id')}")
        ans = d.get('answer') or ''
        print(f"\nReal Autonomous Agent Response:\n{ans}")
    else:
        print(f"Req 12 Error: {q12_res.text}")

if __name__ == "__main__":
    run_test()
