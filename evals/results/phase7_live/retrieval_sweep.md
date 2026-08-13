# FinDocIQ retrieval sweep

Dataset SHA-256: `f1356732204197249c9ded434e93eb74b05ba23a9723e5f24ea7feb573d36882`

## Retrieval quality

| Strategy | Backend | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | live | 31 | 0.290 | 0.548 | 0.661 | 0.455 | 0.489 |
| hybrid | live | 31 | 0.210 | 0.613 | 0.726 | 0.397 | 0.466 |
| hybrid_rerank | live | 31 | 0.403 | 0.806 | 0.871 | 0.609 | 0.671 |
