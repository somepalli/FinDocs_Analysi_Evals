# Phase 1 corpus audit

Phase 1's real-document gate passed on the checksum-locked
`phase1-official-indian-filings` corpus.

## Reproducibility

- Source manifest: `configs/corpus/phase1.json`
- Checksum lock: `configs/corpus/phase1.lock.json`
- Machine-readable audit: `configs/corpus/phase1.audit.json`
- Corpus lock SHA-256:
  `916277415e9e176b3cf7b3902355ecc8eaa5d59f4e4a48c2c472e5f13169d1a5`
- Ingestion config SHA-256:
  `aa5e64257ecd3bae0f8633a726db39689024ace2af0f7cf3933572391eafe30b`

Run the audit from a rebuilt corpus with:

```powershell
python scripts/fetch_corpus.py
$env:PYTHONPATH = "src"
python scripts/audit_corpus.py
```

## Result

| Metric | Value |
|---|---:|
| Official PDFs downloaded and checksum-verified | 18 |
| Fully ingested documents | 15 |
| Pages audited | 868 |
| Chunks emitted | 1,236 |
| Atomic table chunks | 188 |
| Documents requiring Gemma vision | 3 |

All 15 ICRA rating rationales were text-native and fully ingested through the
PyMuPDF fast path. Each emitted chunk contains document, one-based page, and
PDF-coordinate bounding-box provenance.

The three annual reports were deliberately not counted as ingested because at
least one page in each requires vision. SBI Card had 8 hybrid and 7 scanned
pages; JM Financial had 2 hybrid pages; Likhitha Infrastructure had 1 hybrid
page. The remaining pages were digital, but partial ingestion would violate the
project's no-silent-loss rule.

## Document details

| Document | Pages | Blocks | Chunks | Tables |
|---|---:|---:|---:|---:|
| Talcher Fertilizers | 7 | 79 | 79 | 11 |
| Sunbeam Generators | 8 | 81 | 81 | 15 |
| Shree Pushkar Chemicals | 8 | 92 | 93 | 14 |
| Kids Clinic India | 8 | 81 | 81 | 14 |
| Mawana Sugars | 7 | 80 | 80 | 14 |
| Kinara Capital | 8 | 139 | 139 | 7 |
| NED Energy | 6 | 58 | 58 | 13 |
| Desai Brothers | 7 | 77 | 77 | 12 |
| ICRA rationale 136204 | 7 | 81 | 81 | 14 |
| ICRA rationale 136513 | 8 | 87 | 87 | 15 |
| ICRA rationale 136241 | 7 | 76 | 76 | 12 |
| Techno Electric & Engineering | 9 | 91 | 91 | 16 |
| ICRA rationale 136718 | 10 | 88 | 88 | 17 |
| ICRA rationale 136091 | 5 | 53 | 53 | 9 |
| SKH M India | 7 | 72 | 72 | 5 |

## Visual provenance review

The first table chunk from five filings was rendered at 144 DPI with every
provenance rectangle drawn in red. All five checks aligned with the source
caption and complete table bounds:

- Talcher Fertilizers
- Mawana Sugars
- Kinara Capital
- Techno Electric & Engineering
- SKH M India

The generated review images live under `.artifacts/phase1_spot_checks/` and are
intentionally ignored by Git. They can be regenerated from the checksum-locked
PDFs and JSONL chunks with `scripts/spot_check_chunk.py`.
