import json
from pathlib import Path

import pytest

from scripts.validate_dataset import (
    load_corpus_ids,
    load_corpus_manifest,
    validate_datasets,
)


def _write_jsonl(path: Path, *rows: dict[str, object]) -> Path:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _case(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "question_id": "q-1",
        "question": "What changed?",
        "relevant_chunk_ids": ["chunk-1"],
        "expected_answer": {"answer_type": "numeric", "value": "10"},
    }
    payload.update(updates)
    return payload


def test_valid_dataset_resolves_against_ingested_corpus(tmp_path: Path) -> None:
    corpus = _write_jsonl(tmp_path / "chunks.jsonl", {"chunk_id": "chunk-1"})
    dataset = _write_jsonl(tmp_path / "dataset.jsonl", _case())
    corpus_ids = load_corpus_ids((corpus,))
    assert validate_datasets((dataset,), corpus_ids) == 1


def test_validator_reports_verify_direction_and_missing_chunk(tmp_path: Path) -> None:
    dataset = _write_jsonl(
        tmp_path / "dataset.jsonl",
        _case(
            relevant_chunk_ids=["missing"],
            expected_answer={
                "answer_type": "numeric_multi",
                "values": [{"label": "FY2025", "value": "VERIFY"}],
            },
        ),
    )
    with pytest.raises(ValueError) as captured:
        validate_datasets((dataset,), frozenset({"chunk-1"}))
    message = str(captured.value)
    assert "unresolved VERIFY at $.expected_answer.values[0].value" in message
    assert "numeric_multi expected_answer requires direction" in message
    assert "relevant_chunk_ids[0] does not resolve: missing" in message


def test_manifest_rejects_duplicate_chunk_ids(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"chunk_ids": ["a", "a"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicates"):
        load_corpus_manifest(manifest)


def test_validator_applies_typed_answer_contract(tmp_path: Path) -> None:
    dataset = _write_jsonl(
        tmp_path / "dataset.jsonl",
        _case(expected_answer={"answer_type": "numeric", "value": "10", "tolerance": None}),
    )
    with pytest.raises(ValueError, match="numeric answer requires tolerance"):
        validate_datasets((dataset,), frozenset({"chunk-1"}))
