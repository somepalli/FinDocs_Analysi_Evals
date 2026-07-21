"""Run reproducible retrieval sweeps and write separate score tables.

By default, ``--sweep`` uses the checked-in fixture records so the command is
immediately runnable without downloading model weights. Pass ``--live`` to
run each strategy against local Qdrant and the pinned BGE models.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from pydantic import TypeAdapter

from evals.schema import (
    AnswerPrediction,
    EvalCase,
    RetrievedItem,
    StrategyResult,
    SweepResult,
)
from evals.scorers.answers import aggregate_answers
from evals.scorers.retrieval import aggregate_retrieval
from findociq.retrieve.pipeline import (
    RetrievalPipeline,
    RetrievalRuntimeConfig,
    build_local_pipeline,
)

CASE_ADAPTER = TypeAdapter(EvalCase)
ANSWER_ADAPTER = TypeAdapter(AnswerPrediction)
STRATEGIES = ("naive", "hybrid", "hybrid_rerank")


def load_cases(path: str | Path) -> tuple[EvalCase, ...]:
    source = Path(path)
    cases: list[EvalCase] = []
    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    cases.append(CASE_ADAPTER.validate_json(line))
                except ValueError as error:
                    raise ValueError(f"invalid eval case at {source}:{line_number}") from error
    if not cases:
        raise ValueError(f"evaluation dataset is empty: {source}")
    identifiers = [case.question_id for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("evaluation question_id values must be unique")
    return tuple(cases)


def load_retrieval_records(path: str | Path) -> dict[str, dict[str, tuple[RetrievedItem, ...]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("retrieval records must be an object keyed by strategy")
    output: dict[str, dict[str, tuple[RetrievedItem, ...]]] = {}
    for strategy, questions in payload.items():
        if not isinstance(questions, dict):
            raise ValueError(f"retrieval records for {strategy} must be an object")
        output[strategy] = {
            question_id: tuple(RetrievedItem.model_validate(item) for item in items)
            for question_id, items in questions.items()
        }
    return output


def load_answer_records(path: str | Path) -> dict[str, dict[str, AnswerPrediction]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("answer records must be an object keyed by strategy")
    return {
        strategy: {
            question_id: ANSWER_ADAPTER.validate_python(prediction)
            for question_id, prediction in questions.items()
        }
        for strategy, questions in payload.items()
    }


def run_sweep(
    cases: Sequence[EvalCase],
    *,
    strategy_paths: dict[str, Path],
    dataset_sha256: str,
    retrieval_records: dict[str, dict[str, tuple[RetrievedItem, ...]]] | None = None,
    answer_records: dict[str, dict[str, AnswerPrediction]] | None = None,
    pipeline_factory: Callable[[str, Path], RetrievalPipeline] | None = None,
    index_config_path: Path = Path("configs/index/default.yaml"),
) -> SweepResult:
    results: list[StrategyResult] = []
    for strategy, config_path in strategy_paths.items():
        if retrieval_records is not None:
            predictions = retrieval_records.get(strategy, {})
            backend = "fixture"
        else:
            if pipeline_factory is None:
                pipeline_factory = _default_pipeline_factory(index_config_path)
            pipeline = pipeline_factory(strategy, config_path)
            predictions = _retrieve_live(cases, pipeline)
            backend = "live"
        answer = None
        if answer_records is not None and strategy in answer_records:
            answer = aggregate_answers(cases, answer_records[strategy])
        results.append(
            StrategyResult(
                strategy=strategy,
                config_hash=file_hash(index_config_path, config_path),
                backend=backend,
                retrieval=aggregate_retrieval(cases, predictions),
                answer=answer,
            )
        )
    return SweepResult(dataset_sha256=dataset_sha256, results=tuple(results))


def write_results(result: SweepResult, output_dir: str | Path) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "retrieval_sweep.json"
    markdown_path = destination / "retrieval_sweep.md"
    json_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(result: SweepResult) -> str:
    lines = [
        "# FinDocIQ retrieval sweep",
        "",
        f"Dataset SHA-256: `{result.dataset_sha256}`",
        "",
        "## Retrieval quality",
        "",
        "| Strategy | Backend | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result.results:
        metrics = item.retrieval
        lines.append(
            f"| {item.strategy} | {item.backend} | {metrics.query_count} | "
            f"{metrics.recall_at_1:.3f} | {metrics.recall_at_5:.3f} | "
            f"{metrics.recall_at_8:.3f} | {metrics.mrr:.3f} | {metrics.ndcg_at_8:.3f} |"
        )
    answers = [item for item in result.results if item.answer is not None]
    if answers:
        lines.extend(
            [
                "",
                "## Answer quality",
                "",
                "| Strategy | Answers | Exact | Numeric exact | Text exact | "
                "Citation P | Citation R | Citation F1 |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in answers:
            assert item.answer is not None
            metrics = item.answer
            lines.append(
                f"| {item.strategy} | {metrics.answer_count} | "
                f"{metrics.exact_match_accuracy:.3f} | "
                f"{_optional_metric(metrics.numeric_exact_accuracy)} | "
                f"{_optional_metric(metrics.text_exact_accuracy)} | "
                f"{metrics.citation_precision:.3f} | {metrics.citation_recall:.3f} | "
                f"{metrics.citation_f1:.3f} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    if not args.sweep:
        raise SystemExit("pass --sweep to run the evaluation sweep")
    cases = load_cases(args.dataset)
    records = None if args.live else load_retrieval_records(args.retrieval_records)
    answers = load_answer_records(args.answer_predictions) if args.answer_predictions else None
    strategy_paths = {name: args.config_dir / f"{name}.yaml" for name in STRATEGIES}
    result = run_sweep(
        cases,
        strategy_paths=strategy_paths,
        dataset_sha256=file_hash(args.dataset),
        retrieval_records=records,
        answer_records=answers,
        index_config_path=args.index_config,
    )
    json_path, markdown_path = write_results(result, args.results_dir)
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--live", action="store_true", help="use local Qdrant and BGE models")
    parser.add_argument("--dataset", type=Path, default=Path("evals/datasets/smoke.jsonl"))
    parser.add_argument(
        "--retrieval-records",
        type=Path,
        default=Path("evals/datasets/smoke_retrieval.json"),
    )
    parser.add_argument("--answer-predictions", type=Path)
    parser.add_argument("--results-dir", type=Path, default=Path("evals/results"))
    parser.add_argument("--config-dir", type=Path, default=Path("configs/retrieval"))
    parser.add_argument("--index-config", type=Path, default=Path("configs/index/default.yaml"))
    return parser.parse_args()


def file_hash(*paths: str | Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _retrieve_live(
    cases: Iterable[EvalCase], pipeline: RetrievalPipeline
) -> dict[str, tuple[RetrievedItem, ...]]:
    return {
        case.question_id: tuple(
            RetrievedItem(chunk_id=hit.chunk.chunk_id, rank=hit.rank, score=hit.score)
            for hit in pipeline.retrieve(case.question)
        )
        for case in cases
    }


def _default_pipeline_factory(index_path: Path) -> Callable[[str, Path], RetrievalPipeline]:
    def factory(_: str, strategy_path: Path) -> RetrievalPipeline:
        runtime = RetrievalRuntimeConfig.from_yaml(index_path, strategy_path)
        return build_local_pipeline(runtime)

    return factory


def _optional_metric(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


if __name__ == "__main__":
    main()
