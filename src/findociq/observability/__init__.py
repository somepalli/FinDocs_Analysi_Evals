"""Local, content-safe operational tracing for FinDocIQ pipelines."""

from findociq.observability.aggregate import aggregate_traces, write_observability_report
from findociq.observability.recorder import (
    CompositeRecorder,
    InMemoryRecorder,
    JsonlRecorder,
    NoOpRecorder,
    TraceObserver,
    build_observer,
    load_trace_events,
)
from findociq.observability.schema import (
    LangfuseOtlpConfig,
    ObservabilityConfig,
    ObservabilitySummary,
    SpanEvent,
    StageSummary,
    TraceContext,
)

__all__ = [
    "InMemoryRecorder",
    "CompositeRecorder",
    "JsonlRecorder",
    "NoOpRecorder",
    "LangfuseOtlpConfig",
    "ObservabilityConfig",
    "ObservabilitySummary",
    "SpanEvent",
    "StageSummary",
    "TraceContext",
    "TraceObserver",
    "aggregate_traces",
    "build_observer",
    "load_trace_events",
    "write_observability_report",
]
