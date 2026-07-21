"""Hybrid retrieval helpers, including deterministic reciprocal-rank fusion."""

from __future__ import annotations

from collections.abc import Sequence

from findociq.retrieve.schema import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RetrievalHit]],
    *,
    k: int = 60,
    limit: int | None = None,
) -> tuple[RetrievalHit, ...]:
    """Fuse ranked result lists using standard RRF and chunk identity."""

    if k <= 0:
        raise ValueError("RRF k must be positive")
    if limit is not None and limit <= 0:
        raise ValueError("RRF limit must be positive when provided")

    fused: dict[str, tuple[RetrievalHit, float, int]] = {}
    first_seen = 0
    for ranked in ranked_lists:
        for rank, hit in enumerate(ranked, start=1):
            chunk_id = hit.chunk.chunk_id
            contribution = 1.0 / (k + rank)
            if chunk_id not in fused:
                fused[chunk_id] = (hit, contribution, first_seen)
                first_seen += 1
            else:
                previous, score, original_order = fused[chunk_id]
                fused[chunk_id] = (previous, score + contribution, original_order)

    ordered = sorted(fused.values(), key=lambda value: (-value[1], value[2]))
    if limit is not None:
        ordered = ordered[:limit]
    return tuple(
        RetrievalHit(
            chunk=hit.chunk,
            score=score,
            rank=rank,
            method="hybrid_rrf",
            retrieval_score=hit.retrieval_score if hit.retrieval_score is not None else hit.score,
        )
        for rank, (hit, score, _) in enumerate(ordered, start=1)
    )
