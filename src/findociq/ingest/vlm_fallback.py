"""Explicit interface for Gemma 3 vision extraction.

No remote proprietary API is supported here. A production implementation must
target a configured local vLLM or Ollama endpoint and return typed blocks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from findociq.ingest.schema import DocumentBlock


class VisionExtractionRequired(RuntimeError):
    """Raised when a page needs vision but no open-weights extractor is set."""


class VisionPageExtractor(ABC):
    @abstractmethod
    def extract_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
        document_id: str,
    ) -> tuple[DocumentBlock, ...]:
        """Extract ordered, grounded blocks from one rendered page."""


class UnconfiguredGemmaVisionExtractor(VisionPageExtractor):
    def extract_page(
        self,
        *,
        pdf_path: str,
        page_number: int,
        document_id: str,
    ) -> tuple[DocumentBlock, ...]:
        del document_id
        raise VisionExtractionRequired(
            f"page {page_number} of {pdf_path} requires Gemma 3 vision extraction; "
            "configure a local open-weights vision backend"
        )
