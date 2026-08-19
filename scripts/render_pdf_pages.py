"""Render selected one-based PDF pages to PNG files for visual review."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("pages", nargs="+", type=int)
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/pdfs"))
    parser.add_argument("--dpi", type=int, default=180)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.pdf.stem
    with fitz.open(args.pdf) as document:
        for page_number in args.pages:
            if not 1 <= page_number <= len(document):
                raise ValueError(f"page {page_number} outside 1..{len(document)}")
            output = args.output_dir / f"{stem}-p{page_number}.png"
            document[page_number - 1].get_pixmap(dpi=args.dpi, alpha=False).save(output)
            print(output)


if __name__ == "__main__":
    main()
