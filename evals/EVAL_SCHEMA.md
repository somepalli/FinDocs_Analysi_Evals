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

Every result records the dataset SHA-256 and a config hash. Live runs use the
pinned model revisions in `configs/index/default.yaml`; smoke records are
explicitly labeled as fixture-backed and are not benchmark claims.

`--live --live-reasoning` retrieves each corpus-backed case with the selected
strategy and executes both reasoning modes against the pinned local Gemma
runtime. Each reasoning config hash covers the reasoning pipeline, generation
runtime, retrieval strategy, and index configuration. The generated
`reasoning_predictions.json` preserves the complete page/bbox citations used
for scoring.
