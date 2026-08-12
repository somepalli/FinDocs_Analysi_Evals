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
| 4. Two-pass reasoning | Live-smoke validated | Single-pass versus two-pass results |
| 5. Observability | Live-smoke validated | Content-safe latency, cache and failure spans |
| 6. Cross-lingual | Not started | Results split by query language |

The five-question corpus-backed smoke run is a pipeline validation, not a
production benchmark claim.

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

## Phase 4 reasoning

Reasoning is explicitly single-pass or two-pass. Pass 1 extracts figures with
page/bbox provenance; pass 2 receives only that structured extraction, never
the raw retrieval chunks. Both paths require at least one grounded citation.
The local OpenAI-compatible Gemma client is configured in
`configs/reasoning/gemma_local.yaml` and uses temperature 0 with a fixed seed.
The checked-in laptop configuration uses Ollama's open-weight `gemma3:4b` and
verifies its full local content digest before the first model call.

```powershell
ollama pull gemma3:4b
uv sync --extra retrieval --extra dev
uv run findociq-reason "What was revenue in FY25?" `
  --retrieval-hits retrieval_hits.json `
  --pipeline-config configs/pipeline/two_pass.yaml
```

The fixture evaluation compares both modes with `--reasoning-predictions`.
For a live corpus-backed run, start Qdrant, index the audited corpus once, and
run retrieval plus both reasoning modes:

```powershell
docker compose up -d qdrant
uv run findociq-retrieval index corpus/phase1_chunks
uv run python -m evals.run --sweep --live --live-reasoning `
  --dataset evals/datasets/phase4_corpus.jsonl `
  --results-dir evals/results/phase4_live
```

The reasoning table remains separate from retrieval quality. Live prediction
records retain `(document, page, bbox)` citations and are written beside the
summary results.

### Current live smoke result

The pinned five-question English run in `evals/results/phase4_live/` produced:

| Pipeline | Numeric exact | Citation F1 |
|---|---:|---:|
| Single pass | 1.000 | 0.800 |
| Two pass | 0.400 | 0.200 |

Hybrid reranking improved retrieval Recall@1 from `0.600` to `0.800` and
reached Recall@5 of `1.000`. Three two-pass cases are deliberately scored as
failures because Gemma omitted required pass-1 fields; the associated errors
are preserved in `reasoning_predictions.json` instead of being hidden or
silently repaired.

## Phase 5 observability

Observability is local, typed, and disabled unless an observability YAML file
is supplied. A trace records content-safe structural metadata for embedding,
search, reranking, generation, reasoning passes, and citation validation. Raw
questions, prompts, answers, and document text are never written; traces carry
query hashes, configuration hashes, model revisions, counts, durations, and
exception types.

Enable tracing for the corpus-backed evaluation with:

```powershell
uv run python -m evals.run --sweep --live --live-reasoning `
  --dataset evals/datasets/phase4_corpus.jsonl `
  --results-dir evals/results/phase5_observability `
  --observability-config configs/observability/local.yaml
```

The run writes `traces.jsonl`, `observability_summary.json`, and
`observability_summary.md`. Operational cache/non-empty rates and p50/p95
latencies remain separate from Recall@k, answer accuracy, and citation scores.
The no-op recorder is the default, and tests verify that enabling tracing does
not change retrieval rankings or returned provenance.

The current five-question smoke run produced 98 spans across 30 operational
runs, with a `0.250` query-cache hit rate and `1.000` non-empty retrieval rate.
Three failed runs correspond to the already-known two-pass schema validation
failures. Retrieval and answer scores were unchanged from Phase 4. These local
latencies and rates validate instrumentation behavior; they are not production
performance benchmarks.

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
