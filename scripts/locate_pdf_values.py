"""Locate candidate PDF pages containing one or more literal value strings."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("values", nargs="+")
    parser.add_argument("--context", type=int, default=180)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    needles = tuple(value.casefold().replace(",", "") for value in args.values)
    with fitz.open(args.pdf) as document:
        for page in document:
            text = page.get_text("text", sort=True)
            normalized = text.casefold().replace(",", "")
            matches = [needle for needle in needles if needle in normalized]
            if not matches:
                continue
            first = min(normalized.index(match) for match in matches)
            start = max(0, first - args.context)
            end = min(len(text), first + max(map(len, matches)) + args.context)
            snippet = " ".join(text[start:end].split())
            print(f"page={page.number + 1} matches={matches!r} text={snippet}")


if __name__ == "__main__":
    main()
