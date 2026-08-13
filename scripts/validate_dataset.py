"""Fail closed when an evaluation dataset is not ready for scoring."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from evals.schema import EvalCase


def _jsonl_files(paths: Iterable[Path]) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.jsonl")))
        elif path.is_file():
            files.append(path)
        else:
            raise ValueError(f"path does not exist: {path}")
    if not files:
        raise ValueError("no JSONL files found")
    return tuple(files)


def _objects(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            yield line_number, value


def load_corpus_ids(paths: Iterable[Path]) -> frozenset[str]:
    """Read chunk IDs from one or more ingested-corpus JSONL paths."""
    chunk_ids: set[str] = set()
    for path in _jsonl_files(paths):
        for line_number, payload in _objects(path):
            chunk_id = payload.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(f"{path}:{line_number}: missing non-empty chunk_id")
            chunk_ids.add(chunk_id)
    return frozenset(chunk_ids)


def load_corpus_manifest(path: Path) -> frozenset[str]:
    """Read the reviewed benchmark subset of an ingested-corpus manifest."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid manifest JSON: {error.msg}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("chunk_ids"), list):
        raise ValueError(f"{path}: manifest must contain a chunk_ids list")
    chunk_ids = payload["chunk_ids"]
    if not chunk_ids or any(not isinstance(item, str) or not item.strip() for item in chunk_ids):
        raise ValueError(f"{path}: chunk_ids must contain non-empty strings")
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(f"{path}: chunk_ids contains duplicates")
    return frozenset(chunk_ids)


def _verify_paths(value: object, path: str = "$") -> Iterator[str]:
    if isinstance(value, str) and value.strip().casefold() == "verify":
        yield path
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _verify_paths(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _verify_paths(item, f"{path}[{index}]")


def validate_datasets(dataset_paths: Iterable[Path], corpus_ids: frozenset[str]) -> int:
    """Validate readiness and return the number of checked questions."""
    if not corpus_ids:
        raise ValueError("corpus contains no chunk IDs")
    errors: list[str] = []
    seen_questions: dict[str, str] = {}
    question_count = 0
    for dataset in _jsonl_files(dataset_paths):
        for line_number, payload in _objects(dataset):
            question_count += 1
            location = f"{dataset}:{line_number}"
            question_id = payload.get("question_id")
            if not isinstance(question_id, str) or not question_id.strip():
                errors.append(f"{location}: missing non-empty question_id")
                question_label = "<unknown>"
            else:
                question_label = question_id
                if question_id in seen_questions:
                    errors.append(
                        f"{location} [{question_id}]: duplicate question_id; "
                        f"first seen at {seen_questions[question_id]}"
                    )
                else:
                    seen_questions[question_id] = location
            prefix = f"{location} [{question_label}]"

            try:
                EvalCase.model_validate(payload)
            except ValidationError as error:
                errors.append(f"{prefix}: schema validation failed: {error}")

            for verify_path in _verify_paths(payload):
                errors.append(f"{prefix}: unresolved VERIFY at {verify_path}")

            expected = payload.get("expected_answer")
            if isinstance(expected, dict) and expected.get("answer_type") == "numeric_multi":
                direction = expected.get("direction")
                if not isinstance(direction, str) or not direction.strip():
                    errors.append(
                        f"{prefix}: numeric_multi expected_answer requires direction"
                    )

            relevant = payload.get("relevant_chunk_ids")
            if not isinstance(relevant, list) or not relevant:
                errors.append(f"{prefix}: relevant_chunk_ids must be a non-empty list")
                continue
            for index, chunk_id in enumerate(relevant):
                if not isinstance(chunk_id, str) or not chunk_id.strip():
                    errors.append(
                        f"{prefix}: relevant_chunk_ids[{index}] must be a non-empty string"
                    )
                elif chunk_id not in corpus_ids:
                    errors.append(
                        f"{prefix}: relevant_chunk_ids[{index}] does not resolve: {chunk_id}"
                    )

    if errors:
        rendered = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"dataset validation failed with {len(errors)} error(s):\n{rendered}")
    return question_count


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line contract used locally and in CI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        type=Path,
        help="JSONL dataset file or directory; repeat for multiple inputs",
    )
    corpus = parser.add_mutually_exclusive_group(required=True)
    corpus.add_argument(
        "--corpus",
        action="append",
        type=Path,
        help="ingested chunk JSONL file or directory; repeat for multiple inputs",
    )
    corpus.add_argument(
        "--corpus-manifest",
        type=Path,
        help="reviewed CI manifest produced from the ingested corpus",
    )
    return parser


def main() -> int:
    """Validate configured datasets and return a process exit status."""
    args = build_parser().parse_args()
    try:
        corpus_ids = (
            load_corpus_ids(args.corpus)
            if args.corpus is not None
            else load_corpus_manifest(args.corpus_manifest)
        )
        count = validate_datasets(args.dataset, corpus_ids)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"validated {count} questions against {len(corpus_ids)} corpus chunk IDs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
