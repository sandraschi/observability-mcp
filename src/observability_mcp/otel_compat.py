"""OpenTelemetry tracer compatibility across SDK versions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


@contextmanager
def use_span(tracer: Any, name: str) -> Iterator[Any]:
    if hasattr(tracer, "start_as_current_span"):
        with tracer.start_as_current_span(name) as span:
            yield span
        return
    if hasattr(tracer, "start_as_span"):
        with tracer.start_as_span(name) as span:
            yield span
        return
    yield None
