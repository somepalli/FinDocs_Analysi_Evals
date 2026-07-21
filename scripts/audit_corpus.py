"""Route and ingest a checksum-locked corpus, recording the Phase 1 gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from findociq.ingest.chunker import LayoutAwareChunker
from findociq.ingest.config import IngestionConfig
from findociq.ingest.docling_parser import DocumentParser, ParserConfig
from findociq.ingest.router import PageRouter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path("configs/corpus/phase1.lock.json"),
    )
    parser.add_argument("--corpus-dir", type=Path, default=Path("corpus/phase1"))
    parser.add_argument("--chunks-dir", type=Path, default=Path("corpus/phase1_chunks"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/ingestion/default.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("configs/corpus/phase1.audit.json"),
    )
    parser.add_argument("--min-ingested", type=int, default=15)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_pdf(item: dict[str, Any], corpus_dir: Path) -> Path:
    path = corpus_dir / str(item["filename"])
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = file_sha256(path)
    expected = str(item["sha256"])
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path}: {actual} != {expected}")
    return path


def write_chunks(path: Path, chunks: tuple[Any, ...], config_hash: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            enriched = chunk.model_copy(
                update={"metadata": {**chunk.metadata, "config_hash": config_hash}}
            )
            handle.write(enriched.model_dump_json() + "\n")


def audit_document(
    item: dict[str, Any],
    path: Path,
    config: IngestionConfig,
    chunks_dir: Path,
) -> dict[str, Any]:
    router = PageRouter(config.router)
    decisions = router.route(path)
    routes = Counter(decision.route.value for decision in decisions)
    result: dict[str, Any] = {
        "id": item["id"],
        "kind": item["kind"],
        "filename": item["filename"],
        "sha256": item["sha256"],
        "pages": len(decisions),
        "routes": {name: routes.get(name, 0) for name in ("digital", "hybrid", "scanned")},
    }
    if routes.get("hybrid", 0) or routes.get("scanned", 0):
        result.update(
            {
                "status": "vision_required",
                "blocks": None,
                "chunks": None,
                "table_chunks": None,
            }
        )
        return result

    parser_config = ParserConfig(
        prefer_docling=False,
        fail_on_vision_required=True,
    )
    document = DocumentParser(config=parser_config, router=router).parse(path)
    chunks = LayoutAwareChunker(config.chunker).chunk(document)
    output = chunks_dir / f"{item['id']}.jsonl"
    write_chunks(output, chunks, config.config_hash)
    result.update(
        {
            "status": "ingested",
            "parser": document.parser_name,
            "blocks": len(document.blocks),
            "chunks": len(chunks),
            "table_chunks": sum(chunk.kind == "table" for chunk in chunks),
            "chunks_file": output.as_posix(),
        }
    )
    return result


def main() -> None:
    args = parse_args()
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    config = IngestionConfig.from_yaml(args.config)
    results: list[dict[str, Any]] = []
    documents = lock["documents"]
    for index, item in enumerate(documents, start=1):
        path = verify_pdf(item, args.corpus_dir)
        print(f"[{index}/{len(documents)}] {item['id']}", flush=True)
        results.append(audit_document(item, path, config, args.chunks_dir))

    statuses = Counter(result["status"] for result in results)
    payload = {
        "corpus_name": lock["name"],
        "corpus_lock_sha256": file_sha256(args.lock),
        "ingestion_config_hash": config.config_hash,
        "summary": {
            "documents": len(results),
            "ingested": statuses.get("ingested", 0),
            "vision_required": statuses.get("vision_required", 0),
            "pages": sum(result["pages"] for result in results),
            "chunks": sum(result["chunks"] or 0 for result in results),
            "table_chunks": sum(result["table_chunks"] or 0 for result in results),
        },
        "documents": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], sort_keys=True))
    if statuses.get("ingested", 0) < args.min_ingested:
        raise SystemExit(
            f"Phase 1 corpus gate failed: ingested {statuses.get('ingested', 0)} "
            f"documents, required {args.min_ingested}"
        )


if __name__ == "__main__":
    main()
