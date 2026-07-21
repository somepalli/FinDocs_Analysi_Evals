from pathlib import Path

from scripts.fetch_corpus import load_manifest

ROOT = Path(__file__).parents[1]


def test_phase1_manifest_has_eighteen_unique_official_pdfs() -> None:
    name, entries = load_manifest(ROOT / "configs/corpus/phase1.json")
    assert name == "phase1-official-indian-filings"
    assert len(entries) == 18
    assert len({entry.id for entry in entries}) == 18
    assert {entry.kind for entry in entries} == {"annual_report", "rating_rationale"}
    assert all(entry.url.startswith("https://") for entry in entries)
