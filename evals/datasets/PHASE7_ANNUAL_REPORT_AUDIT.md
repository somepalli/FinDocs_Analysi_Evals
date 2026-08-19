# Phase 7 annual-report dataset audit

Verified on 2026-08-13 against rendered pages from the hash-locked official
FY2025 annual reports. The local digital fast-path ingestion contains 20,757
rows and 20,754 unique chunk IDs; CI uses the six reviewed answer-bearing
anchors in `phase7_annual_reports_chunk_manifest.json`.

| Dataset | Questions | Reviewed source pages | Principal evidence |
|---|---:|---|---|
| SBI Card | 4 | 171, 301 | Total income, revenue from operations, PAT, income growth |
| JM Financial | 4 | 7, 62 | Consolidated PAT, Home Loans revenue/PAT, net debt-equity |
| Likhitha Infrastructure | 5 | 75, 106 | Standalone revenue/PAT/EPS and consolidated total income |
| Cross-document | 1 | SBI 301; JM 7 | FY2025 PAT comparison |

All 14 rows have concrete chunk IDs and exact `(document, page, bbox)`
citations. No `VERIFY` placeholders remain.

Two draft negative questions were not promoted:

- SBI Card's report explicitly discloses an interim dividend of Rs. 2.50 per
  share, so `NOT_IN_DOCUMENT` would be false.
- Likhitha's order-book absence cannot be established from a partial visual
  ingestion, so the benchmark does not score it as absent.

The configured Gemma vision endpoint was unavailable because port 8900 was
owned by an unrelated local service. These datasets therefore make claims only
about verified searchable pages; they do not mark the three reports as fully
vision-remediated.
