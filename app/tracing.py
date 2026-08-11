from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import get_client, observe

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def get_client():
        return _DummyClient()


class _DummyClient:
    def update_current_trace(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None


class LangfuseClientAdapter:
    def __init__(self, client: Any) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def update_current_trace(self, **kwargs: Any) -> Any:
        update_trace = getattr(self._client, "update_current_trace", None)
        if callable(update_trace):
            return update_trace(**kwargs)

        update_span = getattr(self._client, "update_current_span", None)
        if callable(update_span):
            metadata = dict(kwargs.get("metadata") or {})
            for field in ("user_id", "session_id", "tags"):
                if field in kwargs:
                    metadata[field] = kwargs[field]
            return update_span(metadata=metadata)

        return None

    def update_current_generation(self, **kwargs: Any) -> Any:
        update_generation = getattr(self._client, "update_current_generation", None)
        if callable(update_generation):
            return update_generation(**kwargs)
        return None

    def flush(self) -> Any:
        flush = getattr(self._client, "flush", None)
        if callable(flush):
            return flush()
        return None


def get_langfuse_client():
    if not tracing_enabled():
        return _DummyClient()
    return LangfuseClientAdapter(get_client())


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
