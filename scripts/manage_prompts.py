from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "submission" / "evidence" / "prompt_versions.json"
BASELINE = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
CANDIDATE = (
    "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\n"
    "Answer concisely in no more than three sentences and cite the supplied docs."
)


def client() -> Langfuse:
    load_dotenv(REPO_ROOT / ".env")
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        raise RuntimeError("LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are required")
    return Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        base_url=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )


def get_by_label(langfuse: Langfuse, name: str, label: str):
    try:
        return langfuse.get_prompt(name, label=label, type="text", cache_ttl_seconds=0)
    except Exception:
        return None


def ensure_versions(langfuse: Langfuse, name: str) -> tuple[object, object]:
    baseline = get_by_label(langfuse, name, "baseline")
    if baseline is None:
        baseline = langfuse.create_prompt(
            name=name,
            type="text",
            prompt=BASELINE,
            labels=["baseline", "production"],
            tags=["day13", "baseline"],
            commit_message="Day 13 baseline prompt",
        )
    candidate = get_by_label(langfuse, name, "candidate")
    if candidate is None:
        candidate = langfuse.create_prompt(
            name=name,
            type="text",
            prompt=CANDIDATE,
            labels=["candidate"],
            tags=["day13", "candidate"],
            commit_message="Day 13 concise candidate prompt",
        )
    return baseline, candidate


def write_status(langfuse: Langfuse, name: str) -> dict:
    result: dict[str, object] = {"prompt_name": name, "labels": {}}
    for label in ("baseline", "candidate", "production"):
        prompt = get_by_label(langfuse, name, label)
        result["labels"][label] = (
            {"version": int(prompt.version), "is_fallback": bool(getattr(prompt, "is_fallback", False))}
            if prompt is not None
            else None
        )
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Day 13 Langfuse prompt labels")
    parser.add_argument("action", choices=["setup", "promote", "rollback", "status"])
    parser.add_argument("--name", default=os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat"))
    args = parser.parse_args()
    langfuse = client()
    baseline, candidate = ensure_versions(langfuse, args.name)
    if args.action == "promote":
        langfuse.update_prompt(
            name=args.name,
            version=int(candidate.version),
            new_labels=["candidate", "production"],
        )
    elif args.action == "rollback":
        langfuse.update_prompt(
            name=args.name,
            version=int(baseline.version),
            new_labels=["baseline", "production"],
        )
    write_status(langfuse, args.name)
    langfuse.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
