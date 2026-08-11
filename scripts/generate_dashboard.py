from __future__ import annotations

import argparse
import html
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil((p / 100) * len(ordered)) - 1))
    return ordered[index]


def load_records(path: Path, minutes: int) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            record["_dt"] = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
            records.append(record)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    if not records:
        return []
    cutoff = max(record["_dt"] for record in records) - timedelta(minutes=minutes)
    return [record for record in records if record["_dt"] >= cutoff]


def status(value: float, operator: str, threshold: float) -> str:
    passing = value <= threshold if operator == "lte" else value >= threshold
    return "good" if passing else "bad"


def panel(title: str, value: str, detail: str, state: str) -> str:
    return f"""
    <section class="panel {state}">
      <h2>{html.escape(title)}</h2>
      <div class="value">{html.escape(value)}</div>
      <p>{html.escape(detail)}</p>
    </section>"""


def render(records: list[dict], minutes: int) -> str:
    responses = [record for record in records if record.get("event") == "response_sent"]
    requests = [record for record in records if record.get("event") == "request_received"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    latencies = [float(record.get("latency_ms", 0)) for record in responses]
    p50, p95, p99 = (percentile(latencies, p) for p in (50, 95, 99))
    if requests:
        observed_seconds = (
            max(record["_dt"] for record in requests)
            - min(record["_dt"] for record in requests)
        ).total_seconds()
        span_minutes = max(1.0, min(float(minutes), observed_seconds / 60))
    else:
        span_minutes = 1.0
    request_rate = len(requests) / span_minutes
    error_rate = (len(failures) / len(requests) * 100) if requests else 0.0
    errors = Counter(record.get("error_type", "unknown") for record in failures)
    total_cost = sum(float(record.get("cost_usd", 0)) for record in responses)
    tokens_in = sum(int(record.get("tokens_in", 0)) for record in responses)
    tokens_out = sum(int(record.get("tokens_out", 0)) for record in responses)
    quality = mean(float(record.get("quality_score", 0)) for record in responses) if responses else 0.0

    cost_by_minute: dict[str, float] = defaultdict(float)
    for record in responses:
        cost_by_minute[record["_dt"].strftime("%H:%M")] += float(record.get("cost_usd", 0))
    cost_detail = ", ".join(f"{key}: ${value:.4f}" for key, value in sorted(cost_by_minute.items())) or "No response data"
    error_detail = ", ".join(f"{key}: {value}" for key, value in errors.items()) or "No errors"

    panels = "".join(
        [
            panel("Latency percentiles", f"P95 {p95:.0f} ms", f"P50 {p50:.0f} ms · P99 {p99:.0f} ms · SLO ≤ 3000 ms", status(p95, "lte", 3000)),
            panel("Request traffic", f"{len(requests)} requests", f"{request_rate:.2f} requests/min · threshold ≥ 1 during load", status(request_rate, "gte", 1)),
            panel("Error rate and breakdown", f"{error_rate:.2f}%", f"{error_detail} · SLO ≤ 2%", status(error_rate, "lte", 2)),
            panel("Cost over time", f"${total_cost:.4f}", f"{cost_detail} · budget ≤ $2.50", status(total_cost, "lte", 2.5)),
            panel("Input and output tokens", f"{tokens_in:,} in / {tokens_out:,} out", f"Total {tokens_in + tokens_out:,} · budget ≤ 50,000", status(tokens_in + tokens_out, "lte", 50000)),
            panel("Quality proxy", f"{quality:.2f}", "Mean score · SLO ≥ 0.75", status(quality, "gte", 0.75)),
        ]
    )
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="refresh" content="30"><title>Day 13 AI Observability</title>
<style>
:root{{--bg:#09111f;--card:#111d31;--text:#edf4ff;--muted:#9eb0ca;--green:#35d399;--red:#fb7185;--line:#263652}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at top,#152746,var(--bg) 48%);color:var(--text);font:15px system-ui;padding:36px}}
header{{display:flex;justify-content:space-between;align-items:end;margin-bottom:24px}} h1{{margin:0;font-size:28px}} header p{{margin:6px 0 0;color:var(--muted)}}
.badge{{border:1px solid var(--line);border-radius:999px;padding:8px 13px;color:var(--muted)}} main{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.panel{{background:linear-gradient(145deg,#15243b,var(--card));border:1px solid var(--line);border-radius:16px;padding:20px;min-height:170px;box-shadow:0 12px 30px #0004}}
.panel.good{{border-top:3px solid var(--green)}} .panel.bad{{border-top:3px solid var(--red)}} h2{{font-size:15px;color:var(--muted);margin:0 0 20px}}
.value{{font-size:30px;font-weight:750;letter-spacing:-.03em}} .panel p{{color:var(--muted);line-height:1.55;margin-top:18px}}
footer{{margin-top:22px;color:var(--muted);display:flex;justify-content:space-between}} @media(max-width:900px){{main{{grid-template-columns:1fr 1fr}}}} @media(max-width:600px){{main{{grid-template-columns:1fr}}}}
</style></head><body><header><div><h1>Day 13 AI Observability</h1><p>Source: data/logs.jsonl · Generated {generated}</p></div><div class="badge">Last {minutes} minutes · refresh 30s</div></header>
<main>{panels}</main><footer><span>{len(records)} log records in window</span><span>Metrics → Traces → Logs</span></footer></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Day 13 runtime dashboard")
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "submission" / "evidence" / "dashboard.html")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument(
        "--first-records",
        type=int,
        help="Render only the first N valid records (useful for baseline evidence).",
    )
    args = parser.parse_args()
    if not args.logs.exists():
        parser.error(f"log file not found: {args.logs}")
    records = load_records(args.logs, args.minutes)
    if args.first_records is not None:
        records = records[: args.first_records]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(records, args.minutes), encoding="utf-8")
    print(f"Generated {args.output} from {len(records)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
