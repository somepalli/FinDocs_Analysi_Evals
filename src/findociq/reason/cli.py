"""Run one reasoning pass over JSONL retrieval hits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from findociq.reason.generation import GenerationConfig, LocalGemmaClient
from findociq.reason.pipeline import ReasoningPipeline, ReasoningPipelineConfig
from findociq.retrieve.schema import RetrievalHit


def main() -> None:
    args = parse_args()
    raw = args.retrieval_hits.read_text(encoding="utf-8")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = [json.loads(line) for line in raw.splitlines() if line.strip()]
    payload = decoded if isinstance(decoded, list) else [decoded]
    hits = tuple(RetrievalHit.model_validate(item) for item in payload)
    generation = GenerationConfig.from_yaml(args.generation_config)
    pipeline = ReasoningPipeline(
        ReasoningPipelineConfig.from_yaml(args.pipeline_config),
        LocalGemmaClient(generation),
    )
    print(pipeline.run(args.question, hits).model_dump_json(indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--retrieval-hits", type=Path, required=True)
    parser.add_argument(
        "--pipeline-config", type=Path, default=Path("configs/pipeline/two_pass.yaml")
    )
    parser.add_argument(
        "--generation-config", type=Path, default=Path("configs/reasoning/gemma_local.yaml")
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
