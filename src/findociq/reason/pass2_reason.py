"""Pass 2: reason only over pass-1 structured extraction."""

from __future__ import annotations

from findociq.observability.recorder import TraceObserver
from findociq.observability.schema import TraceContext
from findociq.reason.generation import GenerationClient
from findociq.reason.pass1_extract import _parse_json
from findociq.reason.prompting import load_prompt, render_extraction, substitute
from findociq.reason.schema import Pass1Extraction, ReasonedAnswer, ground_citation


class Pass2Reasoner:
    def __init__(self, client: GenerationClient, observer: TraceObserver | None = None) -> None:
        self.client = client
        self.observer = observer or TraceObserver()

    def reason(
        self,
        question: str,
        extraction: Pass1Extraction,
        *,
        trace_context: TraceContext | None = None,
    ) -> ReasonedAnswer:
        if not question.strip():
            raise ValueError("question must not be blank")
        prompt = substitute(
            load_prompt("pass2_reason.txt"),
            QUESTION=question,
            EXTRACTION=render_extraction(extraction),
        )
        answer = ReasonedAnswer.model_validate(
            _parse_json(
                self.client.complete(
                    prompt, trace_context=trace_context, stage="generation.pass2"
                )
            )
        )
        allowed = tuple(figure.citation for figure in extraction.figures)
        if not allowed:
            raise ValueError("pass 2 cannot produce a cited answer without extracted figures")
        context = trace_context or TraceContext.for_query(question, operation="reasoning:pass2")
        with self.observer.span(
            context,
            "citation_validation",
            {"mode": "pass2", "citation_count": len(answer.citations)},
        ):
            try:
                citations = tuple(
                    ground_citation(citation, allowed) for citation in answer.citations
                )
            except ValueError as error:
                raise ValueError(
                    "pass 2 returned a citation not present in pass-1 extraction"
                ) from error
        return answer.model_copy(update={"citations": citations})
