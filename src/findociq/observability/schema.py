"""Typed configuration and event contracts for operational observability."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

AttributeValue = str | int | float | bool | None


class ObservabilityConfig(BaseModel):
    """Config-driven local trace behavior."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    trace_path: Path = Path("evals/results/phase5_observability/traces.jsonl")
    capture_content: Literal[False] = False

    @classmethod
    def from_yaml(cls, path: str | Path) -> ObservabilityConfig:
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"observability config must be a mapping: {source}")
        expected = {"enabled", "trace_path", "capture_content"}
        if set(payload) != expected:
            raise ValueError(
                f"invalid observability config keys; missing={sorted(expected - set(payload))}, "
                f"extra={sorted(set(payload) - expected)}"
            )
        return cls(**payload)


class TraceContext(BaseModel):
    """Stable identifiers attached to every span for one pipeline operation."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    operation: str
    query_sha256: str = Field(min_length=64, max_length=64)
    question_id: str | None = None
    config_hash: str | None = None
    dataset_sha256: str | None = None

    @classmethod
    def for_query(
        cls,
        query: str,
        *,
        operation: str,
        question_id: str | None = None,
        config_hash: str | None = None,
        dataset_sha256: str | None = None,
    ) -> TraceContext:
        if not query.strip():
            raise ValueError("trace query must not be blank")
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        identity = "|".join(
            (operation, question_id or "", config_hash or "", dataset_sha256 or "", query_hash)
        )
        return cls(
            run_id=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
            operation=operation,
            query_sha256=query_hash,
            question_id=question_id,
            config_hash=config_hash,
            dataset_sha256=dataset_sha256,
        )


class SpanEvent(BaseModel):
    """One timed pipeline stage without raw prompt or document content."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    operation: str
    query_sha256: str
    question_id: str | None = None
    config_hash: str | None = None
    dataset_sha256: str | None = None
    stage: str
    status: Literal["success", "error"]
    duration_ms: float = Field(ge=0)
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)
    error_type: str | None = None


class StageSummary(BaseModel):
    """Latency and failure aggregation for one named stage."""

    model_config = ConfigDict(frozen=True)

    stage: str
    span_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    p50_ms: float = Field(ge=0)
    p95_ms: float = Field(ge=0)


class ObservabilitySummary(BaseModel):
    """Operational metrics kept separate from retrieval and answer quality."""

    model_config = ConfigDict(frozen=True)

    run_count: int = Field(ge=0)
    span_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    span_error_count: int = Field(ge=0)
    cache_hit_rate: float | None = Field(default=None, ge=0, le=1)
    non_empty_retrieval_rate: float | None = Field(default=None, ge=0, le=1)
    stages: tuple[StageSummary, ...]
