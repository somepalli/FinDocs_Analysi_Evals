from pathlib import Path

import pytest

from findociq.ingest.chunker import LayoutAwareChunker
from findociq.ingest.docling_parser import DocumentParser, ParserConfig
from findociq.ingest.schema import BlockType
from findociq.ingest.vlm_fallback import VisionExtractionRequired

FIXTURES = Path(__file__).parent / "fixtures"


def test_fast_path_preserves_page_and_bbox_provenance() -> None:
    parsed = DocumentParser(ParserConfig(prefer_docling=False)).parse(FIXTURES / "digital.pdf")
    assert parsed.parser_name.startswith("pymupdf")
    assert parsed.pages[0].blocks
    assert any(block.block_type is BlockType.TABLE for block in parsed.blocks)
    for block in parsed.blocks:
        source = block.provenance
        assert source.document_id == parsed.document_id
        assert source.page_number == 1
        assert 0 <= source.bbox.x0 <= source.bbox.x1 <= source.page_width
        assert 0 <= source.bbox.y0 <= source.bbox.y1 <= source.page_height


def test_scanned_page_never_silently_uses_text_dump() -> None:
    with pytest.raises(VisionExtractionRequired):
        DocumentParser(ParserConfig(prefer_docling=False)).parse(FIXTURES / "scanned.pdf")


def test_page_spanning_table_becomes_one_atomic_chunk() -> None:
    parsed = DocumentParser(ParserConfig(prefer_docling=False)).parse(
        FIXTURES / "page_spanning_table.pdf"
    )
    chunks = LayoutAwareChunker().chunk(parsed)
    tables = [chunk for chunk in chunks if chunk.kind == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["atomic"] is True
    assert tables[0].metadata["page_spanning"] is True
    assert {item.page_number for item in tables[0].provenance} == {1, 2}
