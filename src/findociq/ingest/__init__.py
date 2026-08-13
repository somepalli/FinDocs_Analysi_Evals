"""Document ingestion, routing, parsing, and chunking."""

from findociq.ingest.chunker import ChunkerConfig, LayoutAwareChunker
from findociq.ingest.config import IngestionConfig
from findociq.ingest.docling_parser import DocumentParser, ParserConfig
from findociq.ingest.router import PageRouter, RouterConfig
from findociq.ingest.vlm_fallback import (
    OpenAICompatibleGemmaVisionExtractor,
    VisionConfig,
)

__all__ = [
    "ChunkerConfig",
    "DocumentParser",
    "IngestionConfig",
    "LayoutAwareChunker",
    "PageRouter",
    "ParserConfig",
    "RouterConfig",
    "OpenAICompatibleGemmaVisionExtractor",
    "VisionConfig",
]
