from __future__ import annotations

import html
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = REPO_ROOT / "submission" / "evidence"


def shell(title: str, body: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{html.escape(title)}</title><style>
:root{{--bg:#09111f;--card:#132239;--text:#eef5ff;--muted:#9cafca;--blue:#60a5fa;--green:#34d399;--amber:#fbbf24}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(145deg,#10203a,var(--bg));color:var(--text);font:15px system-ui;padding:40px}}
h1{{font-size:28px;margin:0 0 8px}}.sub{{color:var(--muted);margin-bottom:30px}}.card{{background:var(--card);border:1px solid #2a3d5c;border-radius:15px;padding:20px;margin:14px 0}}
.row{{display:flex;justify-content:space-between;gap:20px;align-items:center}}.name{{font-weight:700;font-size:18px}}.meta{{color:var(--muted)}}.bar{{height:12px;background:#263a59;border-radius:8px;margin-top:15px;overflow:hidden}}.fill{{height:100%;background:linear-gradient(90deg,var(--blue),var(--green));border-radius:8px}}
.labels{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.label{{background:var(--card);padding:20px;border-radius:15px;border-top:3px solid var(--blue)}}.label.production{{border-color:var(--amber)}}code{{color:#bfdbfe}} footer{{color:var(--muted);margin-top:26px}}
</style></head><body>{body}</body></html>"""


def trace_page() -> None:
    trace = json.loads((EVIDENCE / "trace_waterfall.json").read_text(encoding="utf-8"))
    total = float(trace.get("latency") or 1)
    cards = []
    for observation in trace.get("observations", []):
        latency = float(observation.get("latency") or 0)
        width = max(3.0, min(100.0, latency / total * 100))
        cards.append(
            f"<div class='card'><div class='row'><span class='name'>{html.escape(observation.get('name') or 'span')}</span>"
            f"<span>{latency:.3f} s</span></div><div class='meta'>{html.escape(observation.get('type') or '')}</div>"
            f"<div class='bar'><div class='fill' style='width:{width:.1f}%'></div></div></div>"
        )
    metadata = trace.get("metadata") or {}
    body = (
        "<h1>Langfuse Trace Waterfall</h1>"
        f"<div class='sub'>Trace <code>{html.escape(trace['id'])}</code> · correlation <code>{html.escape(str(metadata.get('correlation_id')))}</code> · total {total:.3f} s</div>"
        + "".join(cards)
        + f"<footer>Prompt {html.escape(str(metadata.get('prompt_name')))} · {html.escape(str(metadata.get('prompt_label')))} v{html.escape(str(metadata.get('prompt_version')))} · Root cause: retrieve span 2.5 s</footer>"
    )
    (EVIDENCE / "trace-waterfall.html").write_text(shell("Trace Waterfall", body), encoding="utf-8")


def prompt_page() -> None:
    promoted = json.loads((EVIDENCE / "prompt-promoted.json").read_text(encoding="utf-8"))
    rollback = json.loads((EVIDENCE / "prompt-rollback.json").read_text(encoding="utf-8"))
    def labels(payload: dict) -> str:
        parts = []
        production_version = payload["labels"]["production"]["version"]
        for name, item in payload["labels"].items():
            cls = "label production" if name == "production" else "label"
            parts.append(f"<div class='{cls}'><div class='meta'>{html.escape(name)}</div><div class='name'>Version {item['version']}</div></div>")
        return f"<div class='labels'>{''.join(parts)}</div><p class='meta'>Production points to version {production_version}</p>"
    body = (
        f"<h1>Prompt Version Lifecycle</h1><div class='sub'>Prompt <code>{html.escape(promoted['prompt_name'])}</code></div>"
        f"<div class='card'><h2>Promote candidate</h2>{labels(promoted)}</div>"
        f"<div class='card'><h2>Rollback production</h2>{labels(rollback)}</div>"
        "<footer>Baseline v1 · Candidate v2 · production promoted to v2 and rolled back to v1 through the Langfuse API.</footer>"
    )
    (EVIDENCE / "prompt-lifecycle.html").write_text(shell("Prompt Lifecycle", body), encoding="utf-8")


def prompt_trace_page(label: str) -> None:
    trace = json.loads((EVIDENCE / f"prompt_trace_{label}.json").read_text(encoding="utf-8"))
    metadata = trace.get("metadata") or {}
    observations = trace.get("observations") or []
    rows = "".join(
        f"<div class='card row'><span><strong>{html.escape(str(item.get('name')))}</strong> <span class='meta'>{html.escape(str(item.get('type')))}</span></span><span>{float(item.get('latency') or 0):.3f} s</span></div>"
        for item in observations
    )
    body = (
        f"<h1>Langfuse Prompt Trace — {html.escape(label.title())}</h1>"
        f"<div class='sub'>Trace <code>{html.escape(str(trace.get('id')))}</code></div>"
        "<div class='labels'>"
        f"<div class='label'><div class='meta'>prompt_name</div><div class='name'>{html.escape(str(metadata.get('prompt_name')))}</div></div>"
        f"<div class='label'><div class='meta'>prompt_label</div><div class='name'>{html.escape(str(metadata.get('prompt_label')))}</div></div>"
        f"<div class='label production'><div class='meta'>prompt_version</div><div class='name'>Version {html.escape(str(metadata.get('prompt_version')))}</div></div>"
        "</div>"
        f"<h2>Trace observations</h2>{rows}"
        f"<footer>Exported from the configured Langfuse project · total latency {float(trace.get('latency') or 0):.3f} s</footer>"
    )
    (EVIDENCE / f"prompt-trace-{label}.html").write_text(
        shell(f"Prompt Trace {label.title()}", body), encoding="utf-8"
    )


def main() -> int:
    trace_page()
    prompt_page()
    prompt_trace_page("baseline")
    prompt_trace_page("candidate")
    print("Generated trace, prompt lifecycle, and prompt trace evidence pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
