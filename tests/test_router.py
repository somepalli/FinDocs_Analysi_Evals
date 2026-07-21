from pathlib import Path

from findociq.ingest.router import PageRouter
from findociq.ingest.schema import PageRoute

FIXTURES = Path(__file__).parent / "fixtures"


def test_routes_digital_page() -> None:
    decision = PageRouter().route(FIXTURES / "digital.pdf")
    assert len(decision) == 1
    assert decision[0].route is PageRoute.DIGITAL
    assert decision[0].extracted_characters >= 40


def test_routes_scanned_page() -> None:
    decision = PageRouter().route(FIXTURES / "scanned.pdf")
    assert decision[0].route is PageRoute.SCANNED
    assert decision[0].image_coverage >= 0.70
