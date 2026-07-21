from pathlib import Path

import pytest
from pydantic import ValidationError

from findociq.ingest.schema import BoundingBox, stable_document_id


def test_bbox_rejects_reversed_coordinates() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(x0=10, y0=10, x1=5, y1=20)


def test_document_id_depends_on_bytes_not_path(tmp_path: Path) -> None:
    first = tmp_path / "one.bin"
    second = tmp_path / "two.bin"
    first.write_bytes(b"same filing")
    second.write_bytes(b"same filing")
    assert stable_document_id(first) == stable_document_id(second)
