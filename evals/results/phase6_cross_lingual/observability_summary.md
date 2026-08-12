# FinDocIQ operational observability

Operational metrics are reported separately from retrieval and answer quality.

- Runs: 60
- Spans: 188
- Failed runs: 8
- Span errors: 16
- Query-cache hit rate: 0.250
- Non-empty retrieval rate: 1.000

| Stage | Spans | Errors | p50 ms | p95 ms |
|---|---:|---:|---:|---:|
| citation_validation | 14 | 0 | 0.018 | 0.314 |
| generation.pass1 | 10 | 0 | 5550.468 | 14753.341 |
| generation.pass2 | 2 | 0 | 3911.278 | 4571.364 |
| generation.single_pass | 10 | 0 | 3890.708 | 13321.402 |
| reasoning.pass1 | 10 | 8 | 5555.120 | 14755.451 |
| reasoning.pass2 | 2 | 0 | 3913.632 | 4575.946 |
| reasoning.single_pass | 10 | 0 | 3892.938 | 13324.710 |
| reasoning.total | 20 | 8 | 4325.796 | 14691.917 |
| retrieval.embedding | 30 | 0 | 289.804 | 565.744 |
| retrieval.rerank | 10 | 0 | 89347.510 | 105695.623 |
| retrieval.search | 30 | 0 | 20.681 | 44.118 |
| retrieval.total | 40 | 0 | 359.423 | 93725.587 |
