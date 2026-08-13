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
| 6. Cross-lingual | Live-smoke validated | Paired English-Hindi results by language |

Every reported `1.000` below comes from an early `n=5` question/fact cohort;
the evaluation is expanding to `n=80`. These runs validate the pipeline and
measurement path, not production quality.

### Published validation environment

All Phase 4-6 live-smoke results in this README were produced on a Windows
workstation using CPU execution. They are correctness and instrumentation
checks, not GPU throughput or latency benchmarks.

| Component | Environment used for published results |
|---|---|
| Generation | Ollama `gemma3:4b` on CPU |
| Embeddings | BGE-M3 on CPU |
| Reranking | bge-reranker-v2-m3 on CPU, including cold model startup |
| Vector store | Qdrant in local Docker |
| GPU/vLLM | Not exercised in the published runs |

## Production stack

| Component | Default | Fallback / tiers |
|---|---|---|
| Generation | Gemma 3 12B AWQ int4 | Pinned 4B, 12B, and 27B YAML tiers |
| Serving | vLLM OpenAI-compatible endpoint | Ollama `gemma3:4b` |
| Vision | Gemma 3 multimodal through vLLM | Fail closed when unconfigured |
| Embeddings | BGE-M3 dense + sparse | One pinned model revision |
| Reranking | bge-reranker-v2-m3, top-50 to top-8 | None |
| Vector store | Local Qdrant | None required |
| Parsing | PyMuPDF digital fast path; Docling for complex pages | Gemma vision |
| Tracing | Self-hosted Langfuse OTLP + local JSONL | JSONL only |
| API | Thin FastAPI boundary | CLI entry points |
| Packages | uv + `pyproject.toml` + `uv.lock` | No `requirements.txt` |

## Phase 1 quick start

```powershell
uv sync --extra dev
uv run pytest
uv run findociq-ingest tests/fixtures/digital.pdf --output chunks.jsonl
uv run python scripts/spot_check_chunk.py tests/fixtures/digital.pdf chunks.jsonl `
  --chunk-id <id> --output spot-check.png
```

The default parser uses the PyMuPDF coordinate-preserving fast path for digital
pages and tries pinned Docling for scanned or hybrid documents. If Docling
cannot produce grounded blocks, or PyMuPDF table extraction fails, the page is
rendered for the configured local Gemma 3 multimodal endpoint. It is never
silently treated as a reliable text-only dump. The pinned Docling 2.62 adapter
has been exercised against the scanned fixture, including conversion of
Docling's bottom-left boxes into PDF point coordinates.

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
uv run python -m evals.run --sweep `
  --answer-predictions evals/datasets/smoke_answers.json
```

It writes separate retrieval and answer tables to `evals/results/`. Add
`--live` to sweep local Qdrant/BGE results instead of the explicitly labeled
fixture records. Retrieval metrics are never blended with answer or citation
metrics.

## Phase 4 reasoning

Reasoning is explicitly single-pass or two-pass. Pass 1 extracts figures with
page/bbox provenance; pass 2 receives only that structured extraction, never
the raw retrieval chunks. Both paths require at least one grounded citation.
The local OpenAI-compatible Gemma client defaults to
`google/gemma-3-12b-it`. vLLM serves that canonical name from the pinned
`gaunernst/gemma-3-12b-it-int4-awq` artifact. The 4B laptop and 27B ceiling
tiers are in `configs/model_tiers/`; all three use pinned AWQ int4 artifacts,
temperature 0, fixed seeds, and are consumed by `findociq-serve`.

```powershell
docker compose --profile gpu up -d qdrant vllm
uv sync --extra retrieval --extra dev --extra api --extra observability
uv run findociq-reason "What was revenue in FY25?" `
  --retrieval-hits retrieval_hits.json `
  --pipeline-config configs/pipeline/two_pass.yaml
```

To launch a different tier in a native Linux vLLM environment:

```powershell
uv run findociq-serve --tier configs/model_tiers/laptop.yaml
uv run findociq-serve --tier configs/model_tiers/ceiling.yaml
```

`VllmGemmaClient` is a concrete backend-selected client used by the CLI, API,
and live eval composition roots. Its OpenAI-compatible request contract and
the pinned vLLM launch command are tested, but full 12B GPU inference has not
yet been live-run. The published live-smoke results used the CPU validation
environment documented above and the explicitly configured Ollama 4B fallback.

Ollama remains an explicit laptop fallback:

```powershell
ollama pull gemma3:4b
uv run findociq-reason "What was revenue in FY25?" `
  --retrieval-hits retrieval_hits.json `
  --generation-config configs/reasoning/gemma_ollama.yaml
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

| Pipeline | Numeric exact (n=5) | Citation F1 (n=5) |
|---|---:|---:|
| Single pass | 1.000 (n=5; expanding to 80) | 0.800 |
| Two pass | 0.400 | 0.200 |

Hybrid reranking improved retrieval Recall@1 from `0.600` to `0.800` and
reached Recall@5 of `1.000` (`n=5`; expanding to `n=80`). Three two-pass cases
in this historical run are scored as failures because Gemma omitted required
pass-1 fields. Debugging showed these were schema-extraction failures, not an
established model-quality ceiling: one response omitted the echoed question
and two omitted citations. The current parser restores the caller's question
and repairs a missing citation only when the figure value matches exactly one
retrieved provenance; ambiguous or ungrounded output still fails closed. The
table remains the original run and has not been rescored after that fix.

## Phase 5 observability

Observability is typed and fans every immutable structural span to local JSONL
and, when enabled, the self-hosted Langfuse OTLP endpoint. Embedding, search,
reranking, text generation, vision generation, reasoning passes, API requests,
and citation validation are spanned. Raw questions, prompts, answers, images,
and document text are never written; traces carry hashes, model revisions,
counts, durations, and exception types.

FinDocIQ reuses an existing self-hosted Langfuse instance instead of starting
a second stack. Supply that project's keys to the process and keep its base URL
in `configs/observability/langfuse.yaml`:

```powershell
$env:LANGFUSE_PUBLIC_KEY = "<project-public-key>"
$env:LANGFUSE_SECRET_KEY = "<project-secret-key>"
uv sync --extra observability
```

The exporter was integration-tested against the existing local Langfuse
v3.174.1 deployment on port 3000: a structural span was ingested and read back
with one observation and no trace input or output content.

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

The current `n=5` question smoke run (expanding to `n=80`) produced 98 spans
across 30 operational runs, with a `0.250` query-cache hit rate and `1.000`
non-empty retrieval rate (`n=5` questions, expanding to `n=80`; 20 retrieval
calls). Three failed runs correspond
to the historical two-pass schema validation failures described above.
`retrieval.rerank` p50 was 105.5 seconds because the pinned reranker ran cold on
CPU; this is a local smoke-run diagnostic, not GPU or production latency.
Retrieval and answer scores were unchanged from Phase 4.

## Phase 6 cross-lingual evaluation

The Phase 6 dataset contains five matched financial facts, each asked once in
English and once in Hindi. Every pair shares the same relevant chunk IDs,
numeric answer, and exact `(document, page, bbox)` citation targets. Pair
validation runs before model loading, preventing corpus or label differences
from being mistaken for language effects. Official company names remain in
English inside Hindi questions to avoid entity-translation ambiguity.

```powershell
uv run python -m evals.run --sweep --live --live-reasoning `
  --dataset evals/datasets/phase6_cross_lingual.jsonl `
  --results-dir evals/results/phase6_cross_lingual `
  --observability-config configs/observability/phase6.yaml `
  --validate-cross-lingual-pairs
```

The pinned paired smoke run used `n=5` facts per language and is expanding to
`n=80` total questions. It produced:

| Pipeline | Metric | English (n=5) | Hindi (n=5) | Hindi - English |
|---|---|---:|---:|---:|
| Hybrid rerank | Recall@1 | 0.800 | 0.800 | +0.000 |
| Hybrid rerank | Recall@5 | 1.000 (n=5; expanding to 80) | 1.000 (n=5; expanding to 80) | +0.000 |
| Single pass | Numeric exact | 1.000 (n=5; expanding to 80) | 1.000 (n=5; expanding to 80) | +0.000 |
| Single pass | Citation F1 | 0.800 | 0.800 | +0.000 |
| Two pass | Numeric exact | 0.400 | 0.000 | -0.400 |
| Two pass | Citation F1 | 0.200 | 0.000 | -0.200 |

Naive and hybrid retrieval showed language gaps, while the pinned multilingual
reranker recovered parity at Recall@1 and Recall@5. All five Hindi two-pass
queries failed pass-1 structured-output validation; the errors are retained in
`reasoning_predictions.json` and are not repaired by tuning on this dataset.
The paired set validates the cross-lingual measurement path but is too small to
support a production benchmark claim.

## FastAPI service

The HTTP layer only validates requests and delegates to `FinDocIQService`;
retrieval and reasoning logic stays in `src/findociq/`. The query response
schema requires at least one `(document, page, bbox)` citation.

```powershell
uv sync --extra api --extra retrieval --extra observability
uv run findociq-api --config configs/api/default.yaml
Invoke-RestMethod http://127.0.0.1:8080/healthz
```

`POST /v1/query` accepts `question`, optional `question_id`, and optional
`mode` (`single_pass` or `two_pass`). The configured two-pass mode is used when
the request omits it.

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
- The reproducible Phase 1 corpus uses 18 official-source PDFs. Its historical
  checked-in audit predates the now-configured Gemma multimodal endpoint; rerun
  the corpus audit before claiming those three annual reports as remediated.
  See `docs/phase1_corpus_audit.md`.

## Known Phase 2 limitations

- Retrieval unit tests inject deterministic model/store doubles; running the
  real BGE-M3 and bge-reranker weights requires the pinned `retrieval` extra and
  a local Qdrant service.
- No retrieval benchmark is claimed yet. The separate retrieval scorers and
  reproducible sweep belong to Phase 3.
