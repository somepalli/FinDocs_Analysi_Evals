"""Single-pass baseline used for Phase 4 comparison."""

from __future__ import annotations

from findociq.reason.generation import GenerationClient
from findociq.reason.pass1_extract import _parse_json
from findociq.reason.prompting import load_prompt, render_evidence, substitute
from findociq.reason.schema import ReasonedAnswer, citation_from_provenance, ground_citation
from findociq.retrieve.schema import RetrievalHit


class SinglePassReasoner:
    def __init__(self, client: GenerationClient) -> None:
        self.client = client

    def reason(self, question: str, hits: tuple[RetrievalHit, ...]) -> ReasonedAnswer:
        if not question.strip():
            raise ValueError("question must not be blank")
        if not hits:
            raise ValueError("single-pass reasoning requires retrieved evidence")
        answer = ReasonedAnswer.model_validate(
            _parse_json(
                self.client.complete(
                    substitute(
                        load_prompt("single_pass_reason.txt"),
                        QUESTION=question,
                        EVIDENCE=render_evidence(hits),
                    )
                )
            )
        )
        allowed = tuple(
            citation_from_provenance(provenance)
            for hit in hits
            for provenance in hit.chunk.provenance
        )
        try:
            citations = tuple(ground_citation(citation, allowed) for citation in answer.citations)
        except ValueError as error:
            raise ValueError(
                "single-pass returned a citation not present in retrieved evidence"
            ) from error
        return answer.model_copy(update={"citations": citations})
