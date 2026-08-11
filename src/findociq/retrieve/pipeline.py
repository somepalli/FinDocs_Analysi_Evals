"""Config-driven retrieval strategy assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from findociq.index.embedder import BgeM3Embedder, Embedder, EmbeddingConfig
from findociq.index.store import QdrantStore, QdrantStoreConfig, RetrievalStore
from findociq.retrieve.rerank import BgeReranker, Reranker, RerankerConfig
from findociq.retrieve.schema import RetrievalHit

RetrievalMode = Literal["dense", "hybrid_rrf"]


@dataclass(frozen=True, slots=True)
class RetrievalStrategyConfig:
    name: str
    mode: RetrievalMode
    retrieve_top_k: int
    rerank_top_k: int | None
    prefetch_top_k: int
    rrf_k: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("retrieval strategy name is required")
        if self.mode not in {"dense", "hybrid_rrf"}:
            raise ValueError(f"unsupported retrieval mode: {self.mode}")
        if self.retrieve_top_k <= 0 or self.prefetch_top_k <= 0 or self.rrf_k <= 0:
            raise ValueError("retrieval limits and rrf_k must be positive")
        if self.rerank_top_k is not None and not 0 < self.rerank_top_k <= self.retrieve_top_k:
            raise ValueError("rerank_top_k must be between 1 and retrieve_top_k")

    @classmethod
    def from_yaml(cls, path: str | Path) -> RetrievalStrategyConfig:
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"retrieval config must be a mapping: {source}")
        expected = {"name", "mode", "retrieve_top_k", "rerank_top_k", "prefetch_top_k", "rrf_k"}
        if set(payload) != expected:
            raise ValueError(
                f"invalid retrieval config keys; missing={sorted(expected - set(payload))}, "
                f"extra={sorted(set(payload) - expected)}"
            )
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class RetrievalRuntimeConfig:
    embedding: EmbeddingConfig
    reranker: RerankerConfig
    store: QdrantStoreConfig
    strategy: RetrievalStrategyConfig

    @classmethod
    def from_yaml(
        cls,
        index_config_path: str | Path,
        strategy_config_path: str | Path,
    ) -> RetrievalRuntimeConfig:
        source = Path(index_config_path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"embedding", "reranker", "store"}:
            raise ValueError(f"index config must contain embedding, reranker, and store: {source}")
        return cls(
            embedding=EmbeddingConfig(**_mapping(payload["embedding"], "embedding")),
            reranker=RerankerConfig(**_mapping(payload["reranker"], "reranker")),
            store=QdrantStoreConfig(**_mapping(payload["store"], "store")),
            strategy=RetrievalStrategyConfig.from_yaml(strategy_config_path),
        )


class RetrievalPipeline:
    def __init__(
        self,
        config: RetrievalStrategyConfig,
        embedder: Embedder,
        store: RetrievalStore,
        reranker: Reranker | None = None,
    ) -> None:
        if config.rerank_top_k is not None and reranker is None:
            raise ValueError("a reranker is required by this strategy")
        self.config = config
        self.embedder = embedder
        self.store = store
        self.reranker = reranker
        self._cache: dict[str, tuple[RetrievalHit, ...]] = {}

    def retrieve(self, query: str) -> tuple[RetrievalHit, ...]:
        if not query.strip():
            raise ValueError("query must not be blank")
        if query in self._cache:
            return self._cache[query]
        embedding = self.embedder.encode_query(query)
        if self.config.mode == "dense":
            hits = self.store.dense_search(embedding, self.config.retrieve_top_k)
        else:
            hits = self.store.hybrid_search(
                embedding,
                limit=self.config.retrieve_top_k,
                prefetch_limit=self.config.prefetch_top_k,
                rrf_k=self.config.rrf_k,
            )
        if self.reranker is None or self.config.rerank_top_k is None:
            results = self._normalize_ranks(hits)
        else:
            results = self._rerank(query, hits)
        self._cache[query] = results
        return results

    def _rerank(self, query: str, hits: tuple[RetrievalHit, ...]) -> tuple[RetrievalHit, ...]:
        scores = self.reranker.score(query, [hit.chunk.text for hit in hits])
        ranked = sorted(
            zip(scores, hits, strict=True),
            key=lambda item: (-item[0], item[1].rank),
        )[: self.config.rerank_top_k]
        model_name = getattr(self.reranker, "model_name", "reranker")
        return tuple(
            RetrievalHit(
                chunk=hit.chunk,
                score=float(score),
                rank=rank,
                method=model_name,
                retrieval_score=hit.score,
            )
            for rank, (score, hit) in enumerate(ranked, start=1)
        )

    @staticmethod
    def _normalize_ranks(hits: tuple[RetrievalHit, ...]) -> tuple[RetrievalHit, ...]:
        return tuple(hit.model_copy(update={"rank": rank}) for rank, hit in enumerate(hits, 1))


def build_local_pipeline(runtime: RetrievalRuntimeConfig) -> RetrievalPipeline:
    embedder = BgeM3Embedder(runtime.embedding)
    store = QdrantStore(runtime.store)
    reranker = BgeReranker(runtime.reranker) if runtime.strategy.rerank_top_k else None
    return RetrievalPipeline(runtime.strategy, embedder, store, reranker)


def _mapping(value: Any, section: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"index config section '{section}' must be a mapping")
    return value
