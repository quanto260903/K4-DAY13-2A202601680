# Alert Runbook

Alerts must be symptom-based. Start from what users experience, then use metrics, traces, and logs to find the implementation cause.

## Alert 1

- Name: high_latency_p95
- Severity: warning
- Related SLI/SLO: `latency_p95_ms <= 3000` for 99.5% of requests
- Trigger condition: `latency_p95 > 3000ms for 5 minutes`
- User impact: users wait too long for chat answers; demos and support workflows feel stalled even if requests eventually succeed.
- First checks:
  1. Open the latency panel and confirm whether P95/P99 increased while traffic stayed normal.
  2. Open recent Langfuse traces and compare span timings for `run`, `retrieve`, and `generate`.
  3. Search logs by `correlation_id` from a slow trace and check request feature, model, token counts, and incident status.
- Temporary mitigation: reduce concurrency, roll back the latest prompt or retrieval change, and disable any active slow-path incident after recording evidence.
- Owner: on-call-engineer

## Alert 2

- Name: elevated_error_rate
- Severity: critical
- Related SLI/SLO: `error_rate_pct <= 2`
- Trigger condition: `error_rate_pct > 5 for 3 minutes`
- User impact: users receive failed chat responses or retries instead of answers; confidence in the assistant drops quickly.
- First checks:
  1. Open the error panel and identify the dominant `error_breakdown` type.
  2. Pick a failed request, copy its `correlation_id`, and inspect matching log lines for sanitized error details.
  3. Open adjacent traces to see whether failures happen before retrieval, during generation, or while updating observability metadata.
- Temporary mitigation: disable the failing feature path, revert the latest risky config/code change, or switch to local prompt fallback while preserving evidence.
- Owner: on-call-engineer

## Alert 3

- Name: cost_budget_exceeded
- Severity: warning
- Related SLI/SLO: `daily_cost_usd <= 2.5`
- Trigger condition: `daily_cost_usd > 2.5`
- User impact: the service may need throttling or reduced usage, which can slow response times or limit availability for users.
- First checks:
  1. Open the cost and token panels and confirm whether the increase is from traffic, input tokens, or output tokens.
  2. Review Langfuse generations for unusually long prompts, large completions, or repeated retries.
  3. Check logs for feature/session concentration and compare `tokens_in`, `tokens_out`, and `cost_usd` by correlation ID.
- Temporary mitigation: cap max output length, throttle non-critical traffic, roll back expensive prompt versions, and notify the team lead before resuming full load.
- Owner: team-lead
