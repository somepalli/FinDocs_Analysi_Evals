# FinDocIQ

Open-weights financial-document intelligence for Indian annual reports and
credit-rating rationales. The project is deliberately built in measured
phases; retrieval and answer quality will be reported separately when the eval
harness lands.

## Current status

| Phase | Status | Gate |
|---|---|---|
| 1. Ingestion | Complete | 15 filings, 1,236 chunks, 5 visual bbox checks |
| 2. Retrieval | Implemented | Dense, hybrid RRF, and hybrid RRF + BGE rerank |
| 3. Evaluation | Implemented | Separate retrieval and answer score tables |
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

## Phase 2 retrieval

Start local Qdrant with `docker compose up -d qdrant`, then install the pinned
retrieval extras and index the JSONL chunks produced by ingestion:

```powershell
uv sync --extra retrieval
uv run findociq-retrieval index chunks.jsonl
uv run findociq-retrieval query "What changed in revenue?" --strategy naive
uv run findociq-retrieval query "What changed in revenue?" --strategy hybrid
uv run findociq-retrieval query "What changed in revenue?" --strategy hybrid_rerank
```

The strategies are assembled from `configs/retrieval/`. `naive` uses dense
BGE-M3 search, `hybrid` uses Qdrant's dense+sparse reciprocal-rank fusion, and
`hybrid_rerank` retrieves 50 candidates before scoring the final 8 with
`BAAI/bge-reranker-v2-m3`. Retrieval hits retain the original chunk and its
page-level provenance; answer generation is deliberately not part of this
phase.

## Phase 3 evaluation

The evaluation contract lives in [evals/EVAL_SCHEMA.md](evals/EVAL_SCHEMA.md).
Run the deterministic smoke sweep with:

```powershell
$env:PYTHONPATH = "src;."
python -m evals.run --sweep --answer-predictions evals/datasets/smoke_answers.json
```

It writes separate retrieval and answer tables to `evals/results/`. Add
`--live` to sweep local Qdrant/BGE results instead of the explicitly labeled
fixture records. Retrieval metrics are never blended with answer or citation
metrics.

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
- The reproducible Phase 1 corpus uses 18 official-source PDFs. Fifteen ICRA
  rationales were fully ingested; three annual reports correctly stop at the
  local Gemma vision boundary. See `docs/phase1_corpus_audit.md`.
- Vision extraction is an explicit interface in this phase. Production Gemma
  serving and its pinned revision belong to the later reasoning/serving work.

## Known Phase 2 limitations

- Retrieval unit tests inject deterministic model/store doubles; running the
  real BGE-M3 and bge-reranker weights requires the pinned `retrieval` extra and
  a local Qdrant service.
- No retrieval benchmark is claimed yet. The separate retrieval scorers and
  reproducible sweep belong to Phase 3.
