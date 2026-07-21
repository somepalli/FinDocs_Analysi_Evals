"""Page-level citation precision, recall, and F1."""

from __future__ import annotations

from collections.abc import Sequence

from evals.schema import CitationTarget


def citation_matches(predicted: CitationTarget, expected: CitationTarget) -> bool:
    if (
        predicted.document_id != expected.document_id
        or predicted.page_number != expected.page_number
    ):
        return False
    if expected.bbox is None or predicted.bbox is None:
        return True
    return _iou(predicted.bbox, expected.bbox) >= 0.5


def score_citations(
    predicted: Sequence[CitationTarget], expected: Sequence[CitationTarget]
) -> tuple[float, float, float]:
    if not predicted and not expected:
        return 1.0, 1.0, 1.0
    matched_expected: set[int] = set()
    matched_predicted = 0
    for citation in predicted:
        for index, target in enumerate(expected):
            if index not in matched_expected and citation_matches(citation, target):
                matched_expected.add(index)
                matched_predicted += 1
                break
    precision = matched_predicted / len(predicted) if predicted else 0.0
    recall = matched_predicted / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _iou(first: object, second: object) -> float:
    x0 = max(first.x0, second.x0)  # type: ignore[attr-defined]
    y0 = max(first.y0, second.y0)  # type: ignore[attr-defined]
    x1 = min(first.x1, second.x1)  # type: ignore[attr-defined]
    y1 = min(first.y1, second.y1)  # type: ignore[attr-defined]
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    first_area = (first.x1 - first.x0) * (first.y1 - first.y0)  # type: ignore[attr-defined]
    second_area = (second.x1 - second.x0) * (second.y1 - second.y0)  # type: ignore[attr-defined]
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0
