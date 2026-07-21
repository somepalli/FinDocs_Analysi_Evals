"""Render a chunk's provenance boxes over its source PDF page(s)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("chunks", type=Path, help="JSONL emitted by findociq-ingest")
    parser.add_argument("--chunk-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=144)
    return parser.parse_args()


def load_chunk(path: Path, chunk_id: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            chunk = json.loads(line)
            if chunk["chunk_id"] == chunk_id:
                return chunk
    raise KeyError(f"chunk not found: {chunk_id}")


def main() -> None:
    args = parse_args()
    chunk = load_chunk(args.chunks, args.chunk_id)
    by_page: dict[int, list[dict[str, Any]]] = {}
    for evidence in chunk["provenance"]:
        by_page.setdefault(int(evidence["page_number"]), []).append(evidence["bbox"])

    multiple = len(by_page) > 1
    with fitz.open(args.pdf) as document:
        for page_number, boxes in sorted(by_page.items()):
            page = document[page_number - 1]
            for box in boxes:
                rectangle = fitz.Rect(box["x0"], box["y0"], box["x1"], box["y1"])
                page.draw_rect(rectangle, color=(1, 0, 0), width=2, overlay=True)
            pixmap = page.get_pixmap(dpi=args.dpi, alpha=False)
            output = args.output
            if multiple:
                output = output.with_name(f"{output.stem}-p{page_number}{output.suffix}")
            output.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(output)
            print(output)


if __name__ == "__main__":
    main()
