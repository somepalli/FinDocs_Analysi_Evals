"""Answer and citation metrics, kept separate from retrieval metrics."""

from __future__ import annotations

from collections.abc import Iterable

from evals.schema import AnswerMetrics, AnswerPrediction, EvalCase
from evals.scorers.citation import score_citations
from evals.scorers.numeric_exact import score_answer_value


def aggregate_answers(
    cases: Iterable[EvalCase],
    predictions: dict[str, AnswerPrediction],
) -> AnswerMetrics:
    answer_cases = [case for case in cases if case.expected_answer is not None]
    exact: list[bool] = []
    numeric: list[bool] = []
    text: list[bool] = []
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for case in answer_cases:
        prediction = predictions.get(case.question_id, AnswerPrediction(answer=""))
        assert case.expected_answer is not None
        matched = score_answer_value(prediction.answer, case.expected_answer)
        exact.append(matched)
        if case.expected_answer.answer_type == "numeric":
            numeric.append(matched)
        else:
            text.append(matched)
        precision, recall, f1 = score_citations(prediction.citations, case.expected_citations)
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    def mean(values: list[float] | list[bool]) -> float:
        return sum(values) / len(values) if values else 0.0

    return AnswerMetrics(
        answer_count=len(answer_cases),
        exact_match_accuracy=mean(exact),
        numeric_exact_accuracy=mean(numeric) if numeric else None,
        text_exact_accuracy=mean(text) if text else None,
        citation_precision=mean(precisions),
        citation_recall=mean(recalls),
        citation_f1=mean(f1s),
    )
