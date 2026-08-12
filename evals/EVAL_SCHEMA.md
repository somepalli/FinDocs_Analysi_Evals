# FinDocIQ evaluation schema

Evaluation inputs are JSON Lines files. One line is one analyst question and
must contain:

```json
{
  "question_id": "q-001",
  "question": "What was revenue in FY25?",
  "language": "en",
  "relevant_chunk_ids": ["chunk-id-containing-the-answer"],
  "expected_answer": {
    "answer_type": "numeric",
    "value": "1240",
    "tolerance": 0.0
  },
  "expected_citations": [
    {"document_id": "filing-id", "page_number": 12}
  ]
}
```

Required fields are `question_id`, `question`, and `relevant_chunk_ids`.
`language` defaults to `en`; `expected_answer` and `expected_citations` are
optional for retrieval-only cases. `answer_type` is `numeric` or `text`.
Numeric values are compared after removing currency/grouping punctuation and
with the declared absolute tolerance. Text values are compared after
case-folding and whitespace/punctuation normalization.

Retrieval records are JSON objects keyed by strategy name and question ID:

```json
{
  "naive": {
    "q-001": [
      {"chunk_id": "chunk-id-containing-the-answer", "rank": 1, "score": 0.91}
    ]
  }
}
```

Answer prediction records use the same strategy/question nesting:

```json
{
  "naive": {
    "q-001": {
      "answer": "INR 1,240 crore",
      "citations": [
        {"document_id": "filing-id", "page_number": 12}
      ]
    }
  }
}
```

## Scoring contract

Retrieval and answer quality are never blended. Retrieval output reports
`recall@1`, `recall@5`, `recall@8`, MRR, and nDCG@8. Answer output reports
numeric/text exact-match accuracy and citation precision, recall, and F1.
Cases without an expected answer are excluded from answer denominators.

For cross-lingual datasets, `pair_id` identifies translations of the same
question and `language` identifies the query language. Running with
`--validate-cross-lingual-pairs` requires exactly one English (`en`) and one
Hindi (`hi`) case per pair, with identical relevant chunks, expected answer,
and citation targets. Validation occurs before model loading.

Every result records the dataset SHA-256 and a config hash. Live runs use the
pinned model revisions in `configs/index/default.yaml`; smoke records are
explicitly labeled as fixture-backed and are not benchmark claims.

`--live --live-reasoning` retrieves each corpus-backed case with the selected
strategy and executes both reasoning modes against the pinned local Gemma
runtime. Each reasoning config hash covers the reasoning pipeline, generation
runtime, retrieval strategy, and index configuration. The generated
`reasoning_predictions.json` preserves the complete page/bbox citations used
for scoring.

Retrieval and reasoning results include typed `*_by_language` collections.
Markdown output renders English and Hindi rows plus Hindi-minus-English gaps.
Overall, per-language, retrieval, answer, and citation metrics remain distinct;
the cross-lingual report does not blend these score families.

## Operational observability

Passing `--observability-config configs/observability/local.yaml` enables the
local JSONL recorder. Each immutable span contains a deterministic `run_id`,
operation, query SHA-256, optional question/config/dataset identifiers, stage,
status, duration, structural attributes, and exception type. It does not
contain raw questions, prompts, responses, answers, or document text.

`observability_summary.json` and its Markdown rendering report run/span error
counts, query-cache hit rate, non-empty retrieval rate, and per-stage p50/p95
latency. These operational measurements are deliberately not fields in
`RetrievalMetrics` or `AnswerMetrics`; retrieval and answer quality remain
separately scored.
