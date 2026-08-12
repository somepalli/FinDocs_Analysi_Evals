"""Index and query FinDocIQ chunks with one of the retrieval strategies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from findociq.index.embedder import BgeM3Embedder
from findociq.index.store import IndexRecord, QdrantStore
from findociq.ingest.schema import Chunk
from findociq.observability.aggregate import aggregate_traces, write_observability_report
from findociq.observability.recorder import build_observer, load_trace_events
from findociq.observability.schema import ObservabilityConfig
from findociq.retrieve.pipeline import RetrievalRuntimeConfig, build_local_pipeline

CHUNK_ADAPTER = TypeAdapter(Chunk)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    index = subparsers.add_parser("index", help="embed JSONL chunks and upsert them to Qdrant")
    index.add_argument("chunks", type=Path, nargs="+")
    index.add_argument("--index-config", type=Path, default=Path("configs/index/default.yaml"))
    index.add_argument("--batch-size", type=int, default=8)

    query = subparsers.add_parser("query", help="retrieve chunks from Qdrant")
    query.add_argument("query")
    query.add_argument(
        "--strategy", choices=("naive", "hybrid", "hybrid_rerank"), default="hybrid_rerank"
    )
    query.add_argument("--index-config", type=Path, default=Path("configs/index/default.yaml"))
    query.add_argument("--config-dir", type=Path, default=Path("configs/retrieval"))
    query.add_argument("--observability-config", type=Path)
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
    chunks: list[Chunk] = []
    for source in _chunk_files(args.chunks):
        with source.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                chunks.append(CHUNK_ADAPTER.validate_json(line))
    chunks.sort(key=lambda chunk: (len(chunk.text), chunk.chunk_id))
    print(f"indexing {len(chunks)} chunks in deterministic length-bucketed batches")
    total = 0
    for offset in range(0, len(chunks), args.batch_size):
        total += _upsert_batch(chunks[offset : offset + args.batch_size], embedder, store)
    print(f"indexed {total} chunks into {runtime.store.collection}")


def _chunk_files(paths: list[Path]) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.jsonl")))
        elif path.is_file():
            files.append(path)
        else:
            raise ValueError(f"chunk path does not exist: {path}")
    if not files:
        raise ValueError("no JSONL chunk files found")
    return tuple(files)


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
    observability = (
        ObservabilityConfig.from_yaml(args.observability_config)
        if args.observability_config
        else ObservabilityConfig()
    )
    observer = build_observer(observability, reset=True)
    pipeline = build_local_pipeline(runtime, observer)
    payload = [hit.model_dump(mode="json") for hit in pipeline.retrieve(args.query)]
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if observability.enabled:
        write_observability_report(
            aggregate_traces(load_trace_events(observability.trace_path)),
            observability.trace_path.parent,
        )


if __name__ == "__main__":
    main()
