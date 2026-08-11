"""Pass 2: reason only over pass-1 structured extraction."""

from __future__ import annotations

from findociq.reason.generation import GenerationClient
from findociq.reason.pass1_extract import _parse_json
from findociq.reason.prompting import load_prompt, render_extraction, substitute
from findociq.reason.schema import Pass1Extraction, ReasonedAnswer, ground_citation


class Pass2Reasoner:
    def __init__(self, client: GenerationClient) -> None:
        self.client = client

    def reason(self, question: str, extraction: Pass1Extraction) -> ReasonedAnswer:
        if not question.strip():
            raise ValueError("question must not be blank")
        prompt = substitute(
            load_prompt("pass2_reason.txt"),
            QUESTION=question,
            EXTRACTION=render_extraction(extraction),
        )
        answer = ReasonedAnswer.model_validate(_parse_json(self.client.complete(prompt)))
        allowed = tuple(figure.citation for figure in extraction.figures)
        if not allowed:
            raise ValueError("pass 2 cannot produce a cited answer without extracted figures")
        try:
            citations = tuple(ground_citation(citation, allowed) for citation in answer.citations)
        except ValueError as error:
            raise ValueError(
                "pass 2 returned a citation not present in pass-1 extraction"
            ) from error
        return answer.model_copy(update={"citations": citations})
