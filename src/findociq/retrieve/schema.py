"""Typed retrieval results with the original chunk provenance intact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from findociq.ingest.schema import TableChunk, TextChunk


class RetrievalHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: TextChunk | TableChunk = Field(discriminator="kind")
    score: float
    rank: int = Field(ge=1)
    method: str
    retrieval_score: float | None = None
