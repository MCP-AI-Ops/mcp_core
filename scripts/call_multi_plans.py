import os
import json
import requests

API = os.getenv("MCP_CORE_URL", "http://127.0.0.1:8000")

from datetime import datetime, timezone

payload = {
    "github_url": os.getenv("TEST_GITHUB_URL", "https://github.com/MCP-AI-Ops/mcp_core"),
    "metric_names": ["total_events", "avg_cpu", "avg_memory"],
    "context": {
        "context_id": "demo-local",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_type": "web",
        "runtime_env": "prod",
        "time_slot": "normal",
        "weight": 1.0,
        "expected_users": 1200
    }
}

resp = requests.post(f"{API}/plans/multi", json=payload, timeout=60)
print("status:", resp.status_code)
data = resp.json()
print("metrics:", list(data.get("results", {}).keys()))
for k, v in data.get("results", {}).items():
    preds = v.get("prediction", {}).get("predictions", [])
    print(k, "points:", len(preds))
    if preds:
        first = preds[0]
        last = preds[-1]
        print("  first:", first)
        print("  last:", last)