"""Pydantic contracts for evaluation datasets, predictions, and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from findociq.ingest.schema import BoundingBox


class CitationTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    page_number: int = Field(ge=1)
    bbox: BoundingBox | None = None


class AnswerExpectation(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer_type: Literal["numeric", "text"]
    value: str
    tolerance: float = Field(default=0.0, ge=0.0)


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    question: str
    language: str = "en"
    relevant_chunk_ids: tuple[str, ...]
    expected_answer: AnswerExpectation | None = None
    expected_citations: tuple[CitationTarget, ...] = ()


class RetrievedItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    rank: int = Field(ge=1)
    score: float


class AnswerPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: tuple[CitationTarget, ...] = ()


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_count: int = Field(ge=0)
    recall_at_1: float = Field(ge=0, le=1)
    recall_at_5: float = Field(ge=0, le=1)
    recall_at_8: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
    ndcg_at_8: float = Field(ge=0, le=1)


class AnswerMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer_count: int = Field(ge=0)
    exact_match_accuracy: float = Field(ge=0, le=1)
    numeric_exact_accuracy: float | None = Field(default=None, ge=0, le=1)
    text_exact_accuracy: float | None = Field(default=None, ge=0, le=1)
    citation_precision: float = Field(ge=0, le=1)
    citation_recall: float = Field(ge=0, le=1)
    citation_f1: float = Field(ge=0, le=1)


class StrategyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    config_hash: str
    backend: Literal["live", "fixture"]
    retrieval: RetrievalMetrics
    answer: AnswerMetrics | None = None


class SweepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_sha256: str
    results: tuple[StrategyResult, ...]
