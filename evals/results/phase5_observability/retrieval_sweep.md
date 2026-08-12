# FinDocIQ retrieval sweep

Dataset SHA-256: `56b8cc52001dbf3f9b000bd995ac81e670eb14b8c43ff0af306735044deb98fa`

## Retrieval quality

| Strategy | Backend | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | live | 5 | 0.600 | 0.800 | 1.000 | 0.695 | 0.767 |
| hybrid | live | 5 | 0.600 | 0.800 | 1.000 | 0.692 | 0.763 |
| hybrid_rerank | live | 5 | 0.800 | 1.000 | 1.000 | 0.867 | 0.900 |

## Reasoning comparison

| Mode | Backend | Model | Retrieval | Answers | Exact | Numeric exact | Citation F1 |
|---|---|---|---|---:|---:|---:|---:|
| single_pass | live | gemma3:4b | hybrid_rerank | 5 | 1.000 | 1.000 | 0.800 |
| two_pass | live | gemma3:4b | hybrid_rerank | 5 | 0.400 | 0.400 | 0.200 |
