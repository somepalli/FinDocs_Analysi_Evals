"""Typed public HTTP contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from findociq.reason.schema import SourceCitation
from findociq.service import ReasoningMode


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=4000)
    mode: ReasoningMode | None = None
    question_id: str | None = Field(default=None, min_length=1, max_length=200)


class QueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: ReasoningMode
    answer: str
    citations: tuple[SourceCitation, ...] = Field(min_length=1)


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str = "ok"
    service: str = "findociq"
