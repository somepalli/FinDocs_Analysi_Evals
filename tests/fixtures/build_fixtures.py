"""Build tiny deterministic PDF fixtures used by Phase 1 regression tests."""

from __future__ import annotations

from pathlib import Path

import fitz

HERE = Path(__file__).parent
PAGE = fitz.Rect(0, 0, 595, 842)


def digital() -> None:
    document = fitz.open()
    page = document.new_page(width=PAGE.width, height=PAGE.height)
    page.insert_text((54, 70), "ACME INDUSTRIES LIMITED", fontsize=16)
    page.insert_textbox(
        fitz.Rect(54, 100, 540, 170),
        "The company delivered resilient performance during the financial year. "
        "Revenue and EBITDA are summarized below for analyst review.",
        fontsize=11,
    )
    page.insert_text((54, 205), "Table 1: Key financial indicators (INR crore)", fontsize=10)
    x_positions = [54, 220, 360, 500]
    y_positions = [225, 255, 285, 315]
    for x in x_positions:
        page.draw_line((x, y_positions[0]), (x, y_positions[-1]), width=0.7)
    for y in y_positions:
        page.draw_line((x_positions[0], y), (x_positions[-1], y), width=0.7)
    cells = [
        ("Metric", "FY25", "FY24"),
        ("Revenue", "1,240", "1,010"),
        ("EBITDA", "186", "142"),
    ]
    for row, values in enumerate(cells):
        for column, value in enumerate(values):
            page.insert_text((x_positions[column] + 6, 245 + row * 30), value, fontsize=10)
    document.set_metadata({"title": "Digital filing fixture"})
    document.save(HERE / "digital.pdf", garbage=4, deflate=True)


def scanned() -> None:
    source = fitz.open()
    source_page = source.new_page(width=PAGE.width, height=PAGE.height)
    source_page.insert_text((70, 100), "SCANNED CREDIT RATING RATIONALE", fontsize=18)
    source_page.insert_textbox(
        fitz.Rect(70, 140, 520, 260),
        "This page is intentionally rasterized so the router sends it to the "
        "Gemma vision extraction path.",
        fontsize=14,
    )
    pixmap = source_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    document = fitz.open()
    page = document.new_page(width=PAGE.width, height=PAGE.height)
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(HERE / "scanned.pdf", garbage=4, deflate=True)


def page_spanning_table() -> None:
    document = fitz.open()
    for page_number in range(2):
        page = document.new_page(width=PAGE.width, height=PAGE.height)
        page.insert_text((54, 65), "NOTES TO CONSOLIDATED FINANCIAL STATEMENTS", fontsize=13)
        if page_number == 0:
            page.insert_textbox(
                fitz.Rect(54, 90, 540, 140),
                "The following maturity profile continues on the next page.",
                fontsize=10,
            )
            page.insert_text((54, 160), "Table 8: Borrowing maturity profile", fontsize=10)
            top, bottom = 180, 810
        else:
            page.insert_text((54, 100), "Table 8 (continued)", fontsize=10)
            top, bottom = 120, 420
        columns = [54, 300, 500]
        rows = list(range(top, bottom + 1, 30))
        for x in columns:
            page.draw_line((x, rows[0]), (x, rows[-1]), width=0.5)
        for y in rows:
            page.draw_line((columns[0], y), (columns[-1], y), width=0.5)
        for row, y in enumerate(rows[:-1]):
            page.insert_text((60, y + 20), f"Maturity bucket {row + 1}", fontsize=8)
            page.insert_text((310, y + 20), str(100 + row * 7), fontsize=8)
    document.save(HERE / "page_spanning_table.pdf", garbage=4, deflate=True)


if __name__ == "__main__":
    digital()
    scanned()
    page_spanning_table()
