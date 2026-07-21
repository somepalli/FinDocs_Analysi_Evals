# FinDocIQ

Open-weights financial-document intelligence for Indian annual reports and
credit-rating rationales. The project is deliberately built in measured
phases; retrieval and answer quality will be reported separately when the eval
harness lands.

## Current status

| Phase | Status | Gate |
|---|---|---|
| 1. Ingestion | In progress | Code/tests pass; 15-20 filing corpus review pending |
| 2. Retrieval | Not started | Three strategies behind one CLI flag |
| 3. Evaluation | Not started | Separate retrieval and answer score tables |
| 4. Two-pass reasoning | Not started | Single-pass versus two-pass results |
| 5. Observability | Not started | Per-query latency and hit-rate |
| 6. Cross-lingual | Not started | Results split by query language |

No benchmark claim is made before a reproducible corpus-backed eval exists.

## Phase 1 quick start

```powershell
uv sync --extra dev
uv run pytest
uv run findociq-ingest tests/fixtures/digital.pdf --output chunks.jsonl
uv run python scripts/spot_check_chunk.py tests/fixtures/digital.pdf chunks.jsonl `
  --chunk-id <id> --output spot-check.png
```

The default parser prefers Docling when the optional `docling` extra is
installed and uses the PyMuPDF fast path for digital pages. Scanned or hybrid
pages require a configured Gemma 3 vision endpoint; they are never silently
treated as reliable text extraction.

## Provenance contract

Every chunk contains one or more provenance objects with a document ID,
one-based page number, and a PDF-coordinate bounding box `(x0, y0, x1, y1)`.
Coordinates use the source page's point-space and include the page dimensions,
so a reviewer can render and visually verify the evidence.

Tables are emitted as one `TableChunk`; the chunker does not apply text size
limits to table content. Adjacent caption text and the preceding paragraph are
attached to the table chunk.

## Known Phase 1 limitations

- The PyMuPDF fast path identifies tables through its rule-based table finder;
  borderless and visually complex tables may require Docling or vision.
- The checked fixtures are small deterministic documents for regression tests,
  not the 15-20 filing exit corpus. `scripts/fetch_corpus.py` will be added only
  when redistribution-safe source URLs are selected.
- Vision extraction is an explicit interface in this phase. Production Gemma
  serving and its pinned revision belong to the later reasoning/serving work.
