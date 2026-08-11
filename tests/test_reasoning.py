import json
from pathlib import Path

import pytest

from evals.run import run_live_reasoning
from evals.schema import AnswerExpectation, CitationTarget, EvalCase
from findociq.ingest.schema import BoundingBox, Provenance, TextChunk
from findociq.reason.generation import GenerationConfig
from findociq.reason.pass1_extract import Pass1Extractor
from findociq.reason.pipeline import ReasoningPipeline, ReasoningPipelineConfig
from findociq.reason.schema import SourceCitation
from findociq.retrieve.schema import RetrievalHit

ROOT = Path(__file__).parents[1]


def citation() -> SourceCitation:
    return SourceCitation(
        document_id="doc-1",
        page_number=2,
        bbox=BoundingBox(x0=10, y0=20, x1=100, y1=40),
    )


def retrieval_hit() -> RetrievalHit:
    provenance = Provenance(
        document_id="doc-1",
        source_path="filing.pdf",
        page_number=2,
        bbox=citation().bbox,
        page_width=595,
        page_height=842,
    )
    return RetrievalHit(
        chunk=TextChunk(
            chunk_id="chunk-1",
            text="Revenue was INR 1,240 crore in FY25.",
            provenance=(provenance,),
        ),
        score=0.9,
        rank=1,
        method="fixture",
    )


class FakeClient:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def extraction_json() -> str:
    return json.dumps(
        {
            "question": "What was revenue?",
            "figures": [
                {
                    "label": "Revenue",
                    "value": "1240",
                    "unit": "INR crore",
                    "period": "FY25",
                    "citation": citation().model_dump(mode="json"),
                }
            ],
            "notes": [],
        }
    )


def answer_json() -> str:
    return json.dumps(
        {
            "answer": "Revenue was INR 1,240 crore in FY25.",
            "citations": [citation().model_dump(mode="json")],
        }
    )


def test_generation_config_is_local_deterministic_and_yaml_backed() -> None:
    config = GenerationConfig.from_yaml(ROOT / "configs/reasoning/gemma_local.yaml")
    assert config.temperature == 0.0
    assert config.seed == 17
    with pytest.raises(ValueError, match="local HTTP"):
        GenerationConfig(
            base_url="https://example.invalid/v1",
            model_id="google/gemma-3-12b-it",
            revision="rev",
        )


def test_two_pass_extracts_then_reasons_only_over_structured_json() -> None:
    client = FakeClient(extraction_json(), answer_json())
    pipeline = ReasoningPipeline(
        ReasoningPipelineConfig.from_yaml(ROOT / "configs/pipeline/two_pass.yaml"),
        client,
    )
    result = pipeline.run("What was revenue?", (retrieval_hit(),))
    assert result.mode == "two_pass"
    assert result.extraction is not None
    assert result.extraction.figures[0].value == "1240"
    assert result.answer.citations[0].page_number == 2
    assert "Revenue was INR 1,240" in client.prompts[0]
    assert "Revenue was INR 1,240" not in client.prompts[1]
    assert '"figures"' in client.prompts[1]


def test_single_pass_has_no_intermediate_extraction() -> None:
    client = FakeClient(answer_json())
    pipeline = ReasoningPipeline(
        ReasoningPipelineConfig.from_yaml(ROOT / "configs/pipeline/single_pass.yaml"),
        client,
    )
    result = pipeline.run("What was revenue?", (retrieval_hit(),))
    assert result.mode == "single_pass"
    assert result.extraction is None
    assert result.answer.answer.startswith("Revenue")
    assert "Revenue was INR 1,240" in client.prompts[0]


def test_single_pass_canonicalizes_rounded_bbox_to_exact_provenance() -> None:
    rounded = json.loads(answer_json())
    rounded["citations"][0]["bbox"] = {"x0": 10.01, "y0": 20, "x1": 100, "y1": 40}
    pipeline = ReasoningPipeline(
        ReasoningPipelineConfig.from_yaml(ROOT / "configs/pipeline/single_pass.yaml"),
        FakeClient(json.dumps(rounded)),
    )
    result = pipeline.run("What was revenue?", (retrieval_hit(),))
    assert result.answer.citations[0].bbox == citation().bbox


def test_pass1_accepts_fenced_json_and_rejects_ungrounded_citation() -> None:
    client = FakeClient(f"```json\n{extraction_json()}\n```")
    extraction = Pass1Extractor(client).extract("What was revenue?", (retrieval_hit(),))
    assert extraction.figures[0].citation.document_id == "doc-1"

    bad = json.dumps(
        {
            "question": "q",
            "figures": [
                {
                    "label": "x",
                    "value": "1",
                    "citation": {
                        "document_id": "other",
                        "page_number": 1,
                        "bbox": {"x0": 0, "y0": 0, "x1": 1, "y1": 1},
                    },
                }
            ],
            "notes": [],
        }
    )
    with pytest.raises(ValueError, match="not present"):
        Pass1Extractor(FakeClient(bad)).extract("q", (retrieval_hit(),))


def test_pipeline_rejects_empty_evidence_before_model_call() -> None:
    client = FakeClient(answer_json())
    pipeline = ReasoningPipeline(ReasoningPipelineConfig(name="single_pass", passes=1), client)
    with pytest.raises(ValueError, match="retrieved evidence"):
        pipeline.run("q", ())
    assert client.prompts == []


def test_live_reasoning_scores_both_modes_and_records_model_revision() -> None:
    class FakeRetrievalPipeline:
        def retrieve(self, _: str) -> tuple[RetrievalHit, ...]:
            return (retrieval_hit(),)

    config = GenerationConfig(
        base_url="http://localhost:8000/v1",
        model_id="google/gemma-3-4b-it",
        revision="pinned-revision",
    )
    results, predictions = run_live_reasoning(
        (
            EvalCase(
                question_id="q1",
                question="What was revenue?",
                relevant_chunk_ids=("chunk-1",),
                expected_answer=AnswerExpectation(answer_type="numeric", value="1240"),
                expected_citations=(
                    CitationTarget.model_validate(citation().model_dump(mode="json")),
                ),
            ),
        ),
        retrieval_pipeline=FakeRetrievalPipeline(),  # type: ignore[arg-type]
        retrieval_strategy="hybrid_rerank",
        generation_client=FakeClient(answer_json(), extraction_json(), answer_json()),
        generation_config=config,
        generation_config_path=ROOT / "configs/reasoning/gemma_local.yaml",
        reasoning_config_dir=ROOT / "configs/pipeline",
        retrieval_config_path=ROOT / "configs/retrieval/hybrid_rerank.yaml",
        index_config_path=ROOT / "configs/index/default.yaml",
    )
    assert [result.mode for result in results] == ["single_pass", "two_pass"]
    assert all(result.backend == "live" for result in results)
    assert all(result.model_revision == "pinned-revision" for result in results)
    assert results[1].answer.exact_match_accuracy == 1.0
    assert predictions["two_pass"]["q1"].citations[0].bbox == citation().bbox
