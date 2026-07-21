"""Index and query FinDocIQ chunks with one of the retrieval strategies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from findociq.index.embedder import BgeM3Embedder
from findociq.index.store import IndexRecord, QdrantStore
from findociq.ingest.schema import Chunk
from findociq.retrieve.pipeline import RetrievalRuntimeConfig, build_local_pipeline

CHUNK_ADAPTER = TypeAdapter(Chunk)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="embed JSONL chunks and upsert them to Qdrant")
    index.add_argument("chunks", type=Path)
    index.add_argument("--index-config", type=Path, default=Path("configs/index/default.yaml"))
    index.add_argument("--batch-size", type=int, default=8)

    query = subparsers.add_parser("query", help="retrieve chunks from Qdrant")
    query.add_argument("query")
    query.add_argument(
        "--strategy", choices=("naive", "hybrid", "hybrid_rerank"), default="hybrid_rerank"
    )
    query.add_argument("--index-config", type=Path, default=Path("configs/index/default.yaml"))
    query.add_argument("--config-dir", type=Path, default=Path("configs/retrieval"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "index":
        index_chunks(args)
    else:
        query_chunks(args)


def index_chunks(args: argparse.Namespace) -> None:
    runtime = RetrievalRuntimeConfig.from_yaml(
        args.index_config,
        Path("configs/retrieval/naive.yaml"),
    )
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive")
    embedder = BgeM3Embedder(runtime.embedding)
    store = QdrantStore(runtime.store)
    store.ensure_collection(embedder.dimension)
    batch: list[Chunk] = []
    total = 0
    with args.chunks.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            batch.append(CHUNK_ADAPTER.validate_json(line))
            if len(batch) >= args.batch_size:
                total += _upsert_batch(batch, embedder, store)
                batch = []
    if batch:
        total += _upsert_batch(batch, embedder, store)
    print(f"indexed {total} chunks into {runtime.store.collection}")


def _upsert_batch(chunks: list[Chunk], embedder: BgeM3Embedder, store: QdrantStore) -> int:
    embeddings = embedder.encode([chunk.text for chunk in chunks])
    records = [
        IndexRecord(chunk=chunk, embedding=embedding)
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    store.upsert(records)
    return len(chunks)


def query_chunks(args: argparse.Namespace) -> None:
    runtime = RetrievalRuntimeConfig.from_yaml(
        args.index_config,
        args.config_dir / f"{args.strategy}.yaml",
    )
    pipeline = build_local_pipeline(runtime)
    payload = [hit.model_dump(mode="json") for hit in pipeline.retrieve(args.query)]
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
