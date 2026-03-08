import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("N8N_WEBHOOK_URL")


payload = {
    "case_id": "TEST-001",
    "new_status": "IN_PROGRESS",
    "note": "test from python"
}

try:
    res = requests.post(url, json=payload, timeout=10)
    print("status_code =", res.status_code)
    print("response =", res.text)
except Exception as e:
    print("error =", e)