# FinDocIQ operational observability

Operational metrics are reported separately from retrieval and answer quality.

- Runs: 30
- Spans: 98
- Failed runs: 3
- Span errors: 6
- Query-cache hit rate: 0.250
- Non-empty retrieval rate: 1.000

| Stage | Spans | Errors | p50 ms | p95 ms |
|---|---:|---:|---:|---:|
| citation_validation | 9 | 0 | 0.027 | 3.636 |
| generation.pass1 | 5 | 0 | 4155.185 | 13742.276 |
| generation.pass2 | 2 | 0 | 3464.124 | 3819.588 |
| generation.single_pass | 5 | 0 | 3684.505 | 30505.729 |
| reasoning.pass1 | 5 | 3 | 4159.325 | 13745.016 |
| reasoning.pass2 | 2 | 0 | 3480.077 | 3833.104 |
| reasoning.single_pass | 5 | 0 | 3687.155 | 30526.656 |
| reasoning.total | 10 | 3 | 3836.405 | 30527.285 |
| retrieval.embedding | 15 | 0 | 288.807 | 131224.116 |
| retrieval.rerank | 5 | 0 | 105495.611 | 110190.040 |
| retrieval.search | 15 | 0 | 26.947 | 7094.367 |
| retrieval.total | 20 | 0 | 307.158 | 110430.775 |
