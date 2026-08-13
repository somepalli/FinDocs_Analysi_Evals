"""Gemma-backed single-pass and two-pass financial reasoning."""

from findociq.reason.generation import (
    GenerationClient,
    GenerationConfig,
    OllamaGemmaClient,
    VllmGemmaClient,
    build_generation_client,
)
from findociq.reason.pipeline import ReasoningPipeline, ReasoningPipelineConfig
from findociq.reason.schema import (
    ExtractedFigure,
    Pass1Extraction,
    ReasonedAnswer,
    ReasoningRun,
    SourceCitation,
)

__all__ = [
    "ExtractedFigure",
    "GenerationClient",
    "GenerationConfig",
    "OllamaGemmaClient",
    "Pass1Extraction",
    "ReasonedAnswer",
    "ReasoningPipeline",
    "ReasoningPipelineConfig",
    "ReasoningRun",
    "SourceCitation",
    "VllmGemmaClient",
    "build_generation_client",
]
