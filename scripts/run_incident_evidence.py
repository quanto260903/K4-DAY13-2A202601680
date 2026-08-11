from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.challenge import load_challenge, ordered_queries

SAMPLE_QUERIES = REPO_ROOT / "data" / "sample_queries.jsonl"


def send(client: httpx.Client, payload: dict) -> dict:
    response = client.post("/chat", json=payload)
    body = response.json()
    return {
        "status_code": response.status_code,
        "correlation_id": body.get("correlation_id"),
        "latency_ms": body.get("latency_ms"),
        "feature": payload["feature"],
        "session_id": payload["session_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an incident and save reproducible evidence")
    parser.add_argument("--mode", choices=["practice", "challenge"], required=True)
    parser.add_argument("--scenario", default="rag_slow")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()

    if args.mode == "challenge":
        challenge = load_challenge(REPO_ROOT / "config" / "challenge.json")
        scenario = challenge.incident
        payloads = ordered_queries(challenge)
        challenge_id = challenge.challenge_id
        threshold_ms = challenge.latency_threshold_ms
    else:
        scenario = args.scenario
        payloads = [json.loads(line) for line in SAMPLE_QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]
        challenge_id = "practice"
        threshold_ms = 2000

    with httpx.Client(base_url=args.base_url, timeout=45.0) as client:
        before = client.get("/metrics").json()
        client.post(f"/incidents/{scenario}/enable").raise_for_status()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                results = list(pool.map(lambda payload: send(client, payload), payloads))
            after = client.get("/metrics").json()
        finally:
            client.post(f"/incidents/{scenario}/disable").raise_for_status()

    slow = [result for result in results if (result.get("latency_ms") or 0) > threshold_ms]
    evidence = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "challenge_id": challenge_id,
        "scenario": scenario,
        "threshold_ms": threshold_ms,
        "metrics_before": before,
        "metrics_after": after,
        "requests": results,
        "slow_request_count": len(slow),
        "root_cause": "The rag_slow incident adds 2.5 seconds inside the retrieve span.",
        "fix_action": "Disable rag_slow and restore the normal retrieval path.",
        "preventive_measure": "Alert on tail latency and retrieval-span duration, with timeout and fallback controls.",
    }
    output = REPO_ROOT / "submission" / "evidence" / f"{args.mode}-incident.json"
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Saved {output}; slow requests: {len(slow)}/{len(results)}; P95={after['latency_p95']}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
