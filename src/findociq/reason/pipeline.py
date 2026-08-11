"""Explicit single-pass/two-pass reasoning orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from findociq.reason.generation import GenerationClient
from findociq.reason.pass1_extract import Pass1Extractor
from findociq.reason.pass2_reason import Pass2Reasoner
from findociq.reason.schema import ReasoningRun
from findociq.reason.single_pass import SinglePassReasoner
from findociq.retrieve.schema import RetrievalHit


@dataclass(frozen=True, slots=True)
class ReasoningPipelineConfig:
    name: str
    passes: Literal[1, 2]

    def __post_init__(self) -> None:
        if not self.name or self.passes not in {1, 2}:
            raise ValueError("reasoning config needs a name and passes of 1 or 2")

    @classmethod
    def from_yaml(cls, path: str | Path) -> ReasoningPipelineConfig:
        source = Path(path)
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"name", "passes"}:
            raise ValueError(f"pipeline config must contain exactly name and passes: {source}")
        return cls(**payload)


class ReasoningPipeline:
    def __init__(self, config: ReasoningPipelineConfig, client: GenerationClient) -> None:
        self.config = config
        self._single = SinglePassReasoner(client)
        self._pass1 = Pass1Extractor(client)
        self._pass2 = Pass2Reasoner(client)

    def run(self, question: str, hits: tuple[RetrievalHit, ...]) -> ReasoningRun:
        if self.config.passes == 1:
            answer = self._single.reason(question, hits)
            return ReasoningRun(mode=self.config.name, question=question, answer=answer)
        extraction = self._pass1.extract(question, hits)
        answer = self._pass2.reason(question, extraction)
        return ReasoningRun(
            mode=self.config.name,
            question=question,
            answer=answer,
            extraction=extraction,
        )
