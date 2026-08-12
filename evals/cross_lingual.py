"""Pair validation and language-split evaluation helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence

from evals.schema import (
    AnswerPrediction,
    EvalCase,
    LanguageAnswerResult,
    LanguageRetrievalResult,
    RetrievedItem,
)
from evals.scorers.answers import aggregate_answers
from evals.scorers.retrieval import aggregate_retrieval


def validate_paired_cases(
    cases: Sequence[EvalCase], required_languages: frozenset[str] = frozenset({"en", "hi"})
) -> None:
    """Require matched language variants to share all scoring targets."""
    grouped: dict[str, list[EvalCase]] = defaultdict(list)
    for case in cases:
        if not case.pair_id:
            raise ValueError(f"cross-lingual case needs pair_id: {case.question_id}")
        grouped[case.pair_id].append(case)
    if not grouped:
        raise ValueError("cross-lingual dataset has no pairs")
    for pair_id, pair_cases in grouped.items():
        languages = {case.language for case in pair_cases}
        if languages != required_languages or len(pair_cases) != len(required_languages):
            raise ValueError(
                f"pair {pair_id} must contain exactly {sorted(required_languages)}, got "
                f"{sorted(languages)}"
            )
        reference = pair_cases[0]
        for case in pair_cases[1:]:
            if case.relevant_chunk_ids != reference.relevant_chunk_ids:
                raise ValueError(f"pair {pair_id} has mismatched relevant chunks")
            if case.expected_answer != reference.expected_answer:
                raise ValueError(f"pair {pair_id} has mismatched expected answers")
            if case.expected_citations != reference.expected_citations:
                raise ValueError(f"pair {pair_id} has mismatched expected citations")


def aggregate_retrieval_by_language(
    cases: Iterable[EvalCase], predictions: dict[str, Sequence[RetrievedItem]]
) -> tuple[LanguageRetrievalResult, ...]:
    """Calculate retrieval quality independently for each query language."""
    grouped = _group_by_language(cases)
    return tuple(
        LanguageRetrievalResult(
            language=language,
            retrieval=aggregate_retrieval(language_cases, predictions),
        )
        for language, language_cases in sorted(grouped.items())
    )


def aggregate_answers_by_language(
    cases: Iterable[EvalCase], predictions: dict[str, AnswerPrediction]
) -> tuple[LanguageAnswerResult, ...]:
    """Calculate answer and citation quality independently per language."""
    grouped = _group_by_language(cases)
    return tuple(
        LanguageAnswerResult(
            language=language,
            answer=aggregate_answers(language_cases, predictions),
        )
        for language, language_cases in sorted(grouped.items())
    )


def _group_by_language(cases: Iterable[EvalCase]) -> dict[str, list[EvalCase]]:
    grouped: dict[str, list[EvalCase]] = defaultdict(list)
    for case in cases:
        if not case.language.strip():
            raise ValueError(f"case language must not be blank: {case.question_id}")
        grouped[case.language].append(case)
    return grouped
