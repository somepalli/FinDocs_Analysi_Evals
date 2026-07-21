"""Retrieval-only metrics."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import log2

from evals.schema import EvalCase, RetrievalMetrics, RetrievedItem


def score_retrieval_case(case: EvalCase, retrieved: Sequence[RetrievedItem]) -> dict[str, float]:
    relevant = set(case.relevant_chunk_ids)
    ranked_ids = [item.chunk_id for item in sorted(retrieved, key=lambda item: item.rank)]
    if not relevant:
        return {
            "recall_at_1": 0.0,
            "recall_at_5": 0.0,
            "recall_at_8": 0.0,
            "mrr": 0.0,
            "ndcg_at_8": 0.0,
        }

    def recall(k: int) -> float:
        return len(relevant.intersection(ranked_ids[:k])) / len(relevant)

    reciprocal_rank = next(
        (1.0 / rank for rank, chunk_id in enumerate(ranked_ids, start=1) if chunk_id in relevant),
        0.0,
    )
    ideal_hits = min(len(relevant), 8)
    dcg = sum(
        1.0 / log2(rank + 1)
        for rank, chunk_id in enumerate(ranked_ids[:8], start=1)
        if chunk_id in relevant
    )
    ideal_dcg = sum(1.0 / log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return {
        "recall_at_1": recall(1),
        "recall_at_5": recall(5),
        "recall_at_8": recall(8),
        "mrr": reciprocal_rank,
        "ndcg_at_8": dcg / ideal_dcg if ideal_dcg else 0.0,
    }


def aggregate_retrieval(
    cases: Iterable[EvalCase],
    predictions: dict[str, Sequence[RetrievedItem]],
) -> RetrievalMetrics:
    values = [score_retrieval_case(case, predictions.get(case.question_id, ())) for case in cases]
    count = len(values)
    if count == 0:
        return RetrievalMetrics(
            query_count=0,
            recall_at_1=0.0,
            recall_at_5=0.0,
            recall_at_8=0.0,
            mrr=0.0,
            ndcg_at_8=0.0,
        )
    return RetrievalMetrics(
        query_count=count,
        **{key: sum(item[key] for item in values) / count for key in values[0]},
    )
