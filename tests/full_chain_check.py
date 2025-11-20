"""Full prediction chain check.

This script simulates the end to end flow starting from a natural
language user input (as Backend API would receive) and goes through:
  1. Lightweight NL parsing (regex heuristics instead of Claude)
  2. MCPContext construction
  3. Route selection (model_version + path)
  4. Predictor selection + run (BaselinePredictor or LSTMPredictor)
  5. Post-processing policy application

Run:
    python tests/full_chain_check.py "피크타임에 120명 CPU 2코어 메모리 4기가" "https://github.com/fastapi/fastapi"

If no args are provided a default sample will be used.
Outputs a concise summary of each stage.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from typing import Any, Dict

import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH when run directly
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.common import MCPContext
from app.core.router import select_route
from app.routes.plans import pick_engine
from app.core.policy import postprocess_predictions


def parse_natural_language(text: str) -> Dict[str, Any]:
    """Heuristic parser that extracts approximate structured fields.

    This replaces the real Claude call for local chain validation.
    """
    lowered = text.lower()

    # time_slot
    if "피크" in lowered or "peak" in lowered:
        time_slot = "peak"
    elif "저" in lowered or "low" in lowered:
        time_slot = "low"
    elif "weekend" in lowered or "주말" in lowered:
        time_slot = "weekend"
    else:
        time_slot = "normal"

    # expected users (first integer like token)
    users_match = re.search(r"(\d+)(?:명|user|명쯤|명정도)?", lowered)
    expected_users = int(users_match.group(1)) if users_match else 150

    # cpu cores
    cpu_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:코어|core|cpu)", lowered)
    curr_cpu = float(cpu_match.group(1)) if cpu_match else 2.0

    # memory (GB -> MB)
    mem_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:gb|기가|g)", lowered)
    if mem_match:
        curr_mem = float(mem_match.group(1)) * 1024.0
    else:
        curr_mem = 4096.0

    return {
        "time_slot": time_slot,
        "expected_users": expected_users,
        "curr_cpu": curr_cpu,
        "curr_mem": curr_mem,
        "service_type": "web",
        "runtime_env": "prod",
    }


def build_context(parsed: Dict[str, Any], github_url: str) -> MCPContext:
    return MCPContext(
        context_id=f"ctx-{int(datetime.utcnow().timestamp())}",
        timestamp=datetime.utcnow(),
        service_type=parsed["service_type"],
        runtime_env=parsed["runtime_env"],
        time_slot=parsed["time_slot"],
        weight=1.0,
        expected_users=parsed["expected_users"],
        curr_cpu=parsed["curr_cpu"],
        curr_mem=parsed["curr_mem"],
    )


def main() -> None:
    user_input = sys.argv[1] if len(sys.argv) > 1 else "피크타임에 120명 CPU 2코어 메모리 4기가"
    github_url = sys.argv[2] if len(sys.argv) > 2 else "https://github.com/fastapi/fastapi"

    print("[1] Raw user input:", user_input)
    parsed = parse_natural_language(user_input)
    print("[2] Parsed fields:", parsed)

    ctx = build_context(parsed, github_url)
    print("[3] MCPContext constructed:")
    print("    context_id=", ctx.context_id)
    print("    time_slot=", ctx.time_slot, "expected_users=", ctx.expected_users)
    print("    cpu=", ctx.curr_cpu, "mem(MB)=", ctx.curr_mem)

    model_version, path = select_route(ctx)
    print("[4] Route selection:")
    print("    model_version=", model_version, "path=", path)

    predictor = pick_engine(model_version)
    print(f"[5] Predictor chosen: {predictor.__class__.__name__}")

    raw_pred = predictor.run(
        github_url=github_url,
        metric_name="total_events",
        ctx=ctx,
        model_version=model_version,
    )
    print("[6] Raw predictions count:", len(raw_pred.predictions))
    print("    First value:", raw_pred.predictions[0].value if raw_pred.predictions else None)

    final_pred = postprocess_predictions(raw_pred, ctx)
    print("[7] Post-processed predictions count:", len(final_pred.predictions))
    print("    First processed value:", final_pred.predictions[0].value if final_pred.predictions else None)

    max_val = max(p.value for p in final_pred.predictions) if final_pred.predictions else 0
    avg_val = (sum(p.value for p in final_pred.predictions) / len(final_pred.predictions)) if final_pred.predictions else 0
    print("[8] Summary stats: max=", round(max_val, 2), "avg=", round(avg_val, 2))

    print("[✓] Chain test complete.")


if __name__ == "__main__":
    main()
