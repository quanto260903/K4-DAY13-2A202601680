from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.pii import scrub_text


def sanitize(value):
    if isinstance(value, dict):
        return {
            key: sanitize(item)
            for key, item in value.items()
            if key.lower() not in {"public_key", "secret_key", "authorization"}
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Export recent Langfuse trace evidence")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--hours", type=int, default=4)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "submission" / "evidence" / "langfuse_traces.json",
    )
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        base_url=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        timeout=60,
    )
    traces = client.api.trace.list(
        limit=args.limit,
        name="run",
        from_timestamp=datetime.now(timezone.utc) - timedelta(hours=args.hours),
        order_by="timestamp.desc",
    )
    items = []
    for trace in traces.data:
        payload = sanitize(trace.model_dump(mode="json"))
        items.append(
            {
                "id": payload.get("id"),
                "timestamp": payload.get("timestamp"),
                "name": payload.get("name"),
                "session_id": payload.get("session_id"),
                "tags": payload.get("tags"),
                "metadata": payload.get("metadata"),
                "latency": payload.get("latency"),
            }
        )
    output = {"exported_at": datetime.now(timezone.utc).isoformat(), "count": len(items), "traces": items}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    correlated = [item for item in items if (item.get("metadata") or {}).get("correlation_id")]
    if correlated:
        selected = max(correlated, key=lambda item: float(item.get("latency") or 0))
        waterfall = sanitize(
            client.api.trace.get(str(selected["id"])).model_dump(mode="json")
        )
        waterfall_path = args.output.with_name("trace_waterfall.json")
        waterfall_path.write_text(
            json.dumps(waterfall, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Exported waterfall trace {selected['id']} to {waterfall_path}")
    for label in ("baseline", "candidate"):
        matching = [
            item
            for item in items
            if (item.get("metadata") or {}).get("prompt_label") == label
        ]
        if matching:
            prompt_trace = sanitize(
                client.api.trace.get(str(matching[0]["id"])).model_dump(mode="json")
            )
            prompt_trace_path = args.output.with_name(f"prompt_trace_{label}.json")
            prompt_trace_path.write_text(
                json.dumps(prompt_trace, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Exported {label} prompt trace to {prompt_trace_path}")
    print(f"Exported {len(items)} traces to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
