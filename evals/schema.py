"""Pydantic contracts for evaluation datasets, predictions, and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from findociq.ingest.schema import BoundingBox


class CitationTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    page_number: int = Field(ge=1)
    bbox: BoundingBox | None = None


class LabeledNumericValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class AnswerExpectation(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer_type: Literal["numeric", "numeric_multi", "text", "abstain"]
    value: str | None = None
    values: tuple[LabeledNumericValue, ...] = ()
    direction: str | None = None
    tolerance: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_answer_shape(self) -> AnswerExpectation:
        if self.answer_type == "numeric_multi":
            if not self.values:
                raise ValueError("numeric_multi answer requires labeled values")
            if self.direction is None or not self.direction.strip():
                raise ValueError("numeric_multi answer requires direction")
            if self.value is not None:
                raise ValueError("numeric_multi answer must use values, not value")
        elif self.value is None or not self.value.strip():
            raise ValueError(f"{self.answer_type} answer requires value")
        return self


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    pair_id: str | None = Field(default=None, min_length=1)
    question: str
    language: str = Field(default="en", min_length=2)
    category: Literal[
        "single_lookup",
        "multi_year_numeric",
        "derived_metric",
        "qualitative_flag",
        "cross_document",
        "negative",
    ] | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    relevant_chunk_ids: tuple[str, ...]
    expected_answer: AnswerExpectation | None = None
    expected_citations: tuple[CitationTarget, ...] = ()
    notes: str | None = None


class RetrievedItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    rank: int = Field(ge=1)
    score: float


class AnswerPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str
    citations: tuple[CitationTarget, ...] = ()


class ReasoningPrediction(AnswerPrediction):
    error: str | None = None


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


class LanguageRetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    retrieval: RetrievalMetrics


class LanguageAnswerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    language: str
    answer: AnswerMetrics


class StrategyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    config_hash: str
    backend: Literal["live", "fixture"]
    retrieval: RetrievalMetrics
    answer: AnswerMetrics | None = None
    retrieval_by_language: tuple[LanguageRetrievalResult, ...] = ()
    answer_by_language: tuple[LanguageAnswerResult, ...] = ()


class ReasoningResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str
    config_hash: str
    backend: Literal["live", "fixture"]
    model_id: str | None = None
    model_revision: str | None = None
    retrieval_strategy: str | None = None
    answer: AnswerMetrics
    answer_by_language: tuple[LanguageAnswerResult, ...] = ()


class SweepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_sha256: str
    results: tuple[StrategyResult, ...]
    reasoning: tuple[ReasoningResult, ...] = ()
