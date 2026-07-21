"""Phase 1 ingestion CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from findociq.ingest.chunker import LayoutAwareChunker
from findociq.ingest.config import IngestionConfig
from findociq.ingest.docling_parser import DocumentParser, ParserConfig
from findociq.ingest.router import PageRouter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and chunk a financial PDF")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/ingestion/default.yaml"),
        help="typed ingestion YAML configuration",
    )
    parser.add_argument(
        "--pymupdf-only",
        action="store_true",
        help="disable optional Docling parsing for deterministic fast-path checks",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = IngestionConfig.from_yaml(args.config)
    parser_config = config.parser
    if args.pymupdf_only:
        parser_config = ParserConfig(
            prefer_docling=False,
            fail_on_vision_required=parser_config.fail_on_vision_required,
        )
    parsed = DocumentParser(
        config=parser_config,
        router=PageRouter(config.router),
    ).parse(args.pdf)
    chunks = LayoutAwareChunker(config.chunker).chunk(parsed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            enriched = chunk.model_copy(
                update={"metadata": {**chunk.metadata, "config_hash": config.config_hash}}
            )
            handle.write(enriched.model_dump_json() + "\n")
    print(f"wrote {len(chunks)} chunks to {args.output}")


if __name__ == "__main__":
    main()
