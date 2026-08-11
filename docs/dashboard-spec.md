# Dashboard Specification

Runtime source: `GET /metrics`

Dashboard contract source: `config/dashboard.yaml`

Tooling: Langfuse/Grafana-compatible spec. If no external dashboard is available, use this file and `config/dashboard.yaml` as the dashboard contract evidence.

Default time range: 60 minutes

Refresh interval: 30 seconds

## Panels

| # | Panel | Metric fields | Unit | Visualization | Threshold / SLO line |
|---|---|---|---|---|---|
| 1 | Latency percentiles | `latency_p50`, `latency_p95`, `latency_p99` | `ms` | Line chart or single value panel for P50/P95/P99 | P95 `<= 3000 ms` |
| 2 | Request traffic | `traffic` | `requests_per_minute` | Counter or QPS gauge | Rate `>= 1 request/min` during load test |
| 3 | Error rate and breakdown | `error_rate_pct`, `error_breakdown` | `percent` | Percentage stat plus breakdown table | Error rate `<= 2%` |
| 4 | Cost over time | `total_cost_usd`, `avg_cost_usd` | `usd` | Line chart plus total value | Total cost `<= 2.5 USD` |
| 5 | Input and output tokens | `tokens_in_total`, `tokens_out_total` | `tokens` | Stacked bar or two single values | Total token budget `<= 50000` |
| 6 | Quality proxy | `quality_avg` | `score_0_to_1` | Gauge or single value | Average quality `>= 0.75` |

## Runtime Check

Use this command to inspect current metric values:

```bash
curl http://localhost:8000/metrics | python -m json.tool
```

On Windows PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/metrics | Select-Object -ExpandProperty Content
```

## Contract Check

Run the validator before capturing evidence:

```bash
python scripts/validate_dashboard.py
```

Expected output:

```text
HOP LE: 6/6 panel co trong dashboard contract.
```

## Evidence Checklist

- Screenshot or exported view includes all 6 panels.
- Screenshot shows the 60 minute time range.
- Panel titles and units are visible.
- Threshold or SLO line is visible for latency, errors, cost, tokens, and quality.
- Evidence file is saved under `submission/evidence/`.
