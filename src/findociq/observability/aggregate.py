"""Aggregate local span events into operational latency and health metrics."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from findociq.observability.schema import ObservabilitySummary, SpanEvent, StageSummary


def aggregate_traces(events: Sequence[SpanEvent]) -> ObservabilitySummary:
    """Aggregate traces without mixing them with retrieval or answer quality."""
    grouped: dict[str, list[SpanEvent]] = defaultdict(list)
    for event in events:
        grouped[event.stage].append(event)
    stages = tuple(
        StageSummary(
            stage=stage,
            span_count=len(items),
            error_count=sum(item.status == "error" for item in items),
            p50_ms=_percentile([item.duration_ms for item in items], 0.50),
            p95_ms=_percentile([item.duration_ms for item in items], 0.95),
        )
        for stage, items in sorted(grouped.items())
    )
    failed_runs = {event.run_id for event in events if event.status == "error"}
    retrievals = [event for event in events if event.stage == "retrieval.total"]
    cache_hits = [event for event in retrievals if event.attributes.get("cache_hit") is True]
    non_empty = [
        event
        for event in retrievals
        if isinstance(event.attributes.get("hit_count"), int)
        and int(event.attributes["hit_count"]) > 0
    ]
    return ObservabilitySummary(
        run_count=len({event.run_id for event in events}),
        span_count=len(events),
        failed_run_count=len(failed_runs),
        span_error_count=sum(event.status == "error" for event in events),
        cache_hit_rate=len(cache_hits) / len(retrievals) if retrievals else None,
        non_empty_retrieval_rate=len(non_empty) / len(retrievals) if retrievals else None,
        stages=stages,
    )


def write_observability_report(
    summary: ObservabilitySummary, output_dir: str | Path
) -> tuple[Path, Path]:
    """Write machine-readable and reviewable operational summaries."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "observability_summary.json"
    markdown_path = destination / "observability_summary.md"
    json_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(summary), encoding="utf-8")
    return json_path, markdown_path


def _render_markdown(summary: ObservabilitySummary) -> str:
    cache = "-" if summary.cache_hit_rate is None else f"{summary.cache_hit_rate:.3f}"
    non_empty = (
        "-"
        if summary.non_empty_retrieval_rate is None
        else f"{summary.non_empty_retrieval_rate:.3f}"
    )
    lines = [
        "# FinDocIQ operational observability",
        "",
        "Operational metrics are reported separately from retrieval and answer quality.",
        "",
        f"- Runs: {summary.run_count}",
        f"- Spans: {summary.span_count}",
        f"- Failed runs: {summary.failed_run_count}",
        f"- Span errors: {summary.span_error_count}",
        f"- Query-cache hit rate: {cache}",
        f"- Non-empty retrieval rate: {non_empty}",
        "",
        "| Stage | Spans | Errors | p50 ms | p95 ms |",
        "|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {stage.stage} | {stage.span_count} | {stage.error_count} | "
        f"{stage.p50_ms:.3f} | {stage.p95_ms:.3f} |"
        for stage in summary.stages
    )
    return "\n".join(lines) + "\n"


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]
