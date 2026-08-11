# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: K4-G27
- Repository URL: https://github.com/quanto260903/Day13-K4-G27
- Commit SHA nền đã kiểm chứng: `3fff4750b2b47b8c606ccef4686f420551d0bfea`
- Thành viên và vai trò:
  - `HungBil`: khởi tạo hệ thống, challenge config, dashboard/prompt workflow nền.
  - `quanto260903`: Checkpoint 1 — correlation ID, log enrichment và PII redaction.
  - `saihonganh-prog`: Checkpoint 2/3 — tracing, dashboard/SLO/alert, load test, incident và tổng hợp báo cáo.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: **100/100** trên 84 log records; 0 thiếu required fields, 0 thiếu enrichment, 41 correlation IDs duy nhất.
- Tổng số traces export gần nhất: **50 trace `run`**, gồm traces baseline, candidate, production, practice và challenge.
- Số PII leak còn lại: **0**.
- Dashboard runtime: [`evidence/dashboard.html`](evidence/dashboard.html).
- Dashboard baseline: [`evidence/dashboard-baseline.png`](evidence/dashboard-baseline.png).
- Dashboard sau challenge: [`evidence/dashboard-challenge.png`](evidence/dashboard-challenge.png).

## 3. Logging và tracing

- Evidence correlation ID và log đã redact: [`evidence/logs.jsonl`](evidence/logs.jsonl).
- Kết quả validator: [`evidence/validate_logs.txt`](evidence/validate_logs.txt).
- Evidence trace waterfall: [`evidence/trace-waterfall.png`](evidence/trace-waterfall.png) và [`evidence/trace_waterfall.json`](evidence/trace_waterfall.json).
- Danh sách 50 traces và metadata: [`evidence/langfuse_traces.json`](evidence/langfuse_traces.json).
- Trace đáng chú ý: `2f40640fad01bc562424bd46bb8ff860`, correlation ID `req-900764f6`.
- Tổng trace latency: `4.848 s`; span `retrieve`: `2.501 s`; span `generate`: `0.150 s`. Retrieval chiếm phần lớn thời gian xử lý và là bằng chứng trực tiếp cho root cause.

## 4. Prompt versioning

- Prompt name: `day13-chat`.
- Baseline: version `1`, labels `baseline` và `production` ban đầu.
- Candidate: version `2`, label `candidate`.
- Baseline trace ID: `5bdde65f1526cc8cde701ace7d187dbf`.
- Candidate trace ID: `9b8313de7f07b9092f651f293b663c8b`.
- Ảnh trace baseline: [`evidence/prompt-trace-baseline.png`](evidence/prompt-trace-baseline.png).
- Ảnh trace candidate: [`evidence/prompt-trace-candidate.png`](evidence/prompt-trace-candidate.png).
- Production-v2 demo correlation ID: `req-b06b84b5`.
- Rollback-to-v1 demo correlation ID: `req-2f918936`.
- Evidence promote: [`evidence/prompt-promoted.json`](evidence/prompt-promoted.json).
- Evidence rollback: [`evidence/prompt-rollback.json`](evidence/prompt-rollback.json).
- Ảnh vòng đời label: [`evidence/prompt-lifecycle.png`](evidence/prompt-lifecycle.png).
- Trạng thái cuối: `production → version 1`.

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: **HỢP LỆ: 6/6 panel**; xem [`evidence/validate_dashboard.txt`](evidence/validate_dashboard.txt).
- Dashboard dùng nguồn chuẩn `data/logs.jsonl`, time range 60 phút, refresh 30 giây.
- Sáu panel: latency P50/P95/P99, traffic, error rate/breakdown, cost, input/output tokens và quality proxy.
- SLO:
  - latency P95 ≤ 3000 ms;
  - error rate ≤ 2%;
  - daily cost ≤ 2.5 USD;
  - quality average ≥ 0.75.
- Sau challenge, dashboard ghi nhận P95 `3601 ms`, vượt SLO `3000 ms`; P99 `3632 ms`.
- Alert rules nằm trong `config/alert_rules.yaml`; runbook chi tiết nằm trong `docs/alerts.md`.
- Alert được thiết kế symptom-based vì người dùng quan sát thấy chậm, lỗi hoặc giới hạn dịch vụ; implementation có thể thay đổi mà không làm mất ý nghĩa cảnh báo.

## 6. Điều tra challenge

- Challenge ID: `day13-k4-observability-v1`.
- Scenario: `rag_slow`.
- Ngưỡng challenge: `2000 ms`.
- Triệu chứng từ metrics: P95 `3632 ms`; **5/5 request** vượt ngưỡng.
- Trace ID: `2f40640fad01bc562424bd46bb8ff860`.
- Correlation ID: `req-900764f6`.
- Log liên quan: `response_sent.latency_ms=3632`, feature `monitoring`, session `k4-challenge-s02` trong [`evidence/logs.jsonl`](evidence/logs.jsonl).
- Root cause: incident `rag_slow` thêm khoảng 2.5 giây trong span `retrieve`; trace ghi chính xác `retrieve=2.501 s`, lớn hơn nhiều so với `generate=0.150 s`.
- Fix action: tắt `rag_slow` và khôi phục retrieval path bình thường.
- Preventive measure: alert theo tail latency và retrieval-span duration; bổ sung retrieval timeout, fallback/circuit breaker và kiểm thử latency trước release.
- Evidence challenge: [`evidence/challenge-incident.json`](evidence/challenge-incident.json).
- Evidence practice: [`evidence/practice-incident.json`](evidence/practice-incident.json).

## 7. Đóng góp cá nhân

| Thành viên | Phần việc | Commit/đầu ra | Điều đã học |
|---|---|---|---|
| `HungBil` | Khung lab, challenge, dashboard/prompt workflow nền | `b95464c`, `4013676`, `aff4f19`, `5ba6472` | Thiết kế observability contract và challenge có thể tái lập |
| `quanto260903` | Correlation ID, metadata và PII | `21249bb` | Context propagation và scrub dữ liệu trước khi ghi log |
| `saihonganh-prog` | Tracing, dashboard/SLO/alerts, load test, incident và report | `3fff475` và các file evidence hiện tại | Điều tra theo chuỗi Metrics → Traces → Logs và quản lý prompt rollback |

## 8. Kịch bản demo ngắn

1. Mở dashboard baseline và chỉ P95 `1062 ms`.
2. Mở dashboard challenge và chỉ P95 tăng lên `3601 ms`.
3. Mở trace `2f40640fad01bc562424bd46bb8ff860`; so sánh `retrieve=2.501 s` với `generate=0.150 s`.
4. Tìm correlation ID `req-900764f6` trong log và xác nhận request `monitoring` có latency `3632 ms`.
5. Kết luận `rag_slow` là root cause, trình bày fix và preventive measure.
6. Mở prompt lifecycle để chứng minh promote v2 và rollback production về v1.
