"""Pass 1: extract figures and citations into typed JSON."""

from __future__ import annotations

import json

from findociq.observability.recorder import TraceObserver
from findociq.observability.schema import TraceContext
from findociq.reason.generation import GenerationClient
from findociq.reason.prompting import load_prompt, render_evidence, substitute
from findociq.reason.schema import (
    Pass1Extraction,
    citation_from_provenance,
    ground_citation,
)
from findociq.retrieve.schema import RetrievalHit


class Pass1Extractor:
    def __init__(self, client: GenerationClient, observer: TraceObserver | None = None) -> None:
        self.client = client
        self.observer = observer or TraceObserver()

    def extract(
        self,
        question: str,
        hits: tuple[RetrievalHit, ...],
        *,
        trace_context: TraceContext | None = None,
    ) -> Pass1Extraction:
        if not question.strip():
            raise ValueError("question must not be blank")
        if not hits:
            raise ValueError("pass 1 requires at least one retrieved evidence chunk")
        prompt = substitute(
            load_prompt("pass1_extract.txt"),
            QUESTION=question,
            EVIDENCE=render_evidence(hits),
        )
        raw = self.client.complete(
            prompt, trace_context=trace_context, stage="generation.pass1"
        )
        extraction = Pass1Extraction.model_validate(_parse_json(raw))
        context = trace_context or TraceContext.for_query(question, operation="reasoning:pass1")
        with self.observer.span(
            context,
            "citation_validation",
            {"mode": "pass1", "citation_count": len(extraction.figures)},
        ):
            return self._ground_citations(extraction, hits)

    @staticmethod
    def _ground_citations(
        extraction: Pass1Extraction, hits: tuple[RetrievalHit, ...]
    ) -> Pass1Extraction:
        allowed = tuple(
            citation_from_provenance(provenance)
            for hit in hits
            for provenance in hit.chunk.provenance
        )
        try:
            figures = tuple(
                figure.model_copy(
                    update={"citation": ground_citation(figure.citation, allowed)}
                )
                for figure in extraction.figures
            )
        except ValueError as error:
            raise ValueError(
                "pass 1 returned a citation not present in retrieved evidence"
            ) from error
        return extraction.model_copy(update={"figures": figures})


def _parse_json(raw: str) -> dict[str, object]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("generation response did not contain a JSON object") from None
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("generation response must be a JSON object")
    return value
