from pathlib import Path

import pytest

from evals.run import (
    load_answer_records,
    load_cases,
    load_retrieval_records,
    render_markdown,
    run_sweep,
    write_results,
)
from evals.schema import (
    AnswerExpectation,
    AnswerPrediction,
    BoundingBox,
    CitationTarget,
    EvalCase,
    RetrievedItem,
)
from evals.scorers.answers import aggregate_answers
from evals.scorers.citation import score_citations
from evals.scorers.numeric_exact import parse_number, score_answer_value
from evals.scorers.retrieval import aggregate_retrieval

ROOT = Path(__file__).parents[1]


def test_eval_schema_and_fixture_records_load() -> None:
    cases = load_cases(ROOT / "evals/datasets/smoke.jsonl")
    records = load_retrieval_records(ROOT / "evals/datasets/smoke_retrieval.json")
    answers = load_answer_records(ROOT / "evals/datasets/smoke_answers.json")
    assert len(cases) == 2
    assert records["hybrid"]["q-ebitda"][0].chunk_id == "chunk-ebitda"
    assert answers["hybrid_rerank"]["q-revenue"].answer == "1240"


def test_phase4_dataset_is_corpus_backed_with_bbox_targets() -> None:
    cases = load_cases(ROOT / "evals/datasets/phase4_corpus.jsonl")
    assert len(cases) == 5
    assert all(case.expected_answer is not None for case in cases)
    assert all(case.expected_citations[0].bbox is not None for case in cases)


def test_numeric_matching_handles_currency_grouping_and_tolerance() -> None:
    assert parse_number("INR (1,240.5) crore") == -1240.5
    expected = AnswerExpectation(answer_type="numeric", value="1240", tolerance=0.5)
    assert score_answer_value("₹1,240.4 crore", expected)
    assert not score_answer_value("1,241", expected)
    assert score_answer_value("In FY2025, revenue was INR 1,240 crore.", expected)


def test_text_matching_normalizes_case_punctuation_and_space() -> None:
    expected = AnswerExpectation(answer_type="text", value="Strong growth", tolerance=0)
    assert score_answer_value(" strong   GROWTH! ", expected)


def test_retrieval_metrics_are_separate_and_rank_sensitive() -> None:
    cases = (
        EvalCase(question_id="q1", question="q", relevant_chunk_ids=("a",)),
        EvalCase(question_id="q2", question="q", relevant_chunk_ids=("b",)),
    )
    metrics = aggregate_retrieval(
        cases,
        {
            "q1": (RetrievedItem(chunk_id="a", rank=1, score=1),),
            "q2": (
                RetrievedItem(chunk_id="x", rank=1, score=1),
                RetrievedItem(chunk_id="b", rank=2, score=0.9),
            ),
        },
    )
    assert metrics.recall_at_1 == pytest.approx(0.5)
    assert metrics.recall_at_5 == pytest.approx(1.0)
    assert metrics.mrr == pytest.approx(0.75)


def test_citation_score_requires_document_and_page_and_supports_bbox() -> None:
    expected = CitationTarget(
        document_id="doc",
        page_number=2,
        bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
    )
    predicted = CitationTarget(
        document_id="doc",
        page_number=2,
        bbox=BoundingBox(x0=1, y0=1, x1=9, y1=9),
    )
    assert score_citations((predicted,), (expected,)) == (1.0, 1.0, 1.0)
    wrong_page = predicted.model_copy(update={"page_number": 3})
    assert score_citations((wrong_page,), (expected,))[2] == 0.0


def test_answer_metrics_keep_citation_quality_separate() -> None:
    case = EvalCase(
        question_id="q1",
        question="q",
        relevant_chunk_ids=("a",),
        expected_answer=AnswerExpectation(answer_type="numeric", value="10"),
        expected_citations=(CitationTarget(document_id="doc", page_number=1),),
    )
    metrics = aggregate_answers(
        (case,),
        {"q1": AnswerPrediction(answer="10", citations=())},
    )
    assert metrics.exact_match_accuracy == 1.0
    assert metrics.numeric_exact_accuracy == 1.0
    assert metrics.citation_recall == 0.0


def test_fixture_sweep_writes_separate_markdown_tables(tmp_path: Path) -> None:
    cases = load_cases(ROOT / "evals/datasets/smoke.jsonl")
    records = load_retrieval_records(ROOT / "evals/datasets/smoke_retrieval.json")
    answers = load_answer_records(ROOT / "evals/datasets/smoke_answers.json")
    reasoning = load_answer_records(ROOT / "evals/datasets/smoke_reasoning_answers.json")
    result = run_sweep(
        cases,
        strategy_paths={
            name: ROOT / "configs/retrieval" / f"{name}.yaml"
            for name in ("naive", "hybrid", "hybrid_rerank")
        },
        dataset_sha256="dataset-hash",
        retrieval_records=records,
        answer_records=answers,
        reasoning_records=reasoning,
        index_config_path=ROOT / "configs/index/default.yaml",
    )
    json_path, markdown_path = write_results(result, tmp_path)
    assert json_path.is_file()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Retrieval quality" in markdown
    assert "## Answer quality" in markdown
    assert "## Reasoning comparison" in markdown
    assert "hybrid_rerank" in markdown
    assert render_markdown(result) == markdown
