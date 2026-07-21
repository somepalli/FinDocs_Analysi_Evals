# FinDocIQ retrieval sweep

Dataset SHA-256: `2a557a4fa9ad3b18cedb46ef1c0fd0177c80374f06c57f26792fe7367030c5d6`

## Retrieval quality

| Strategy | Backend | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | fixture | 2 | 0.500 | 1.000 | 1.000 | 0.750 | 0.815 |
| hybrid | fixture | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | fixture | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Answer quality

| Strategy | Answers | Exact | Numeric exact | Text exact | Citation P | Citation R | Citation F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | 2 | 0.500 | 0.500 | - | 1.000 | 1.000 | 1.000 |
| hybrid | 2 | 1.000 | 1.000 | - | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | 2 | 1.000 | 1.000 | - | 1.000 | 1.000 | 1.000 |
