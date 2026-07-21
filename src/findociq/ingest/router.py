"""Route each PDF page to digital, scanned, or hybrid extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from pydantic import BaseModel, ConfigDict, Field

from findociq.ingest.schema import PageRoute


@dataclass(frozen=True, slots=True)
class RouterConfig:
    min_digital_characters: int = 40
    scanned_image_coverage: float = 0.70
    hybrid_image_coverage: float = 0.20

    def __post_init__(self) -> None:
        if self.min_digital_characters < 0:
            raise ValueError("min_digital_characters must be non-negative")
        for name in ("scanned_image_coverage", "hybrid_image_coverage"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


class PageRoutingDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    route: PageRoute
    extracted_characters: int = Field(ge=0)
    image_coverage: float = Field(ge=0, le=1)


class PageRouter:
    def __init__(self, config: RouterConfig | None = None) -> None:
        self.config = config or RouterConfig()

    def route(self, pdf_path: str | Path) -> tuple[PageRoutingDecision, ...]:
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(path)

        decisions: list[PageRoutingDecision] = []
        with fitz.open(path) as document:
            if not document.is_pdf:
                raise ValueError(f"not a PDF: {path}")
            for index, page in enumerate(document):
                text = page.get_text("text").strip()
                coverage = self._image_coverage(page)
                decisions.append(
                    PageRoutingDecision(
                        page_number=index + 1,
                        route=self._classify(len(text), coverage),
                        extracted_characters=len(text),
                        image_coverage=coverage,
                    )
                )
        return tuple(decisions)

    def _classify(self, characters: int, image_coverage: float) -> PageRoute:
        has_text = characters >= self.config.min_digital_characters
        if not has_text and image_coverage >= self.config.scanned_image_coverage:
            return PageRoute.SCANNED
        if has_text and image_coverage >= self.config.hybrid_image_coverage:
            return PageRoute.HYBRID
        return PageRoute.DIGITAL

    @staticmethod
    def _image_coverage(page: fitz.Page) -> float:
        page_area = page.rect.get_area()
        if page_area <= 0:
            return 0.0
        rectangles: list[fitz.Rect] = []
        for image in page.get_images(full=True):
            for rectangle in page.get_image_rects(image[0]):
                clipped = rectangle & page.rect
                if not clipped.is_empty:
                    rectangles.append(clipped)
        # Summing may over-count overlapping images, so clamp. Exact polygon
        # union is unnecessary for a routing heuristic.
        return min(1.0, sum(rect.get_area() for rect in rectangles) / page_area)
