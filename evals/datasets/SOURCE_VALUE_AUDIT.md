# Source value audit

Verified on 2026-08-13 by rendering and visually inspecting each complete
source PDF page at 200 DPI. This check reads the original ICRA rationale pages,
not the Docling/PyMuPDF chunk text.

| Value | Source evidence | Page | Result |
|---|---|---:|---|
| Shree Pushkar FY2024 operating income: Rs. 726.2 crore | `icra-shree-pushkar-chemicals-2025.pdf` | 5 | Confirmed |
| Shree Pushkar FY2025 operating income: Rs. 806.3 crore | `icra-shree-pushkar-chemicals-2025.pdf` | 5 | Confirmed |
| Shree Pushkar FY2024 PAT: Rs. 37.1 crore | `icra-shree-pushkar-chemicals-2025.pdf` | 5 | Confirmed |
| Shree Pushkar FY2025 PAT: Rs. 58.6 crore | `icra-shree-pushkar-chemicals-2025.pdf` | 5 | Confirmed |
| Shree Pushkar FY2025 OPBDIT/OI: 10.4% | `icra-shree-pushkar-chemicals-2025.pdf` | 5 | Confirmed |
| FY2025 operating margin: 13.1% | `icra-desai-brothers-2025.pdf` and `icra-kids-clinic-india-2025.pdf` | 1 in each | Confirmed independently in both documents |

## Resolved benchmark placeholders

| Question | Source evidence | Page | Verified gold |
|---|---|---:|---|
| Kids Clinic FY2024 consolidated operating income | `icra-kids-clinic-india-2025.pdf` | 3 | Rs. 1,187.7 crore |
| Kinara FY2024 to FY2025 total managed assets | `icra-kinara-capital-2025.pdf` | 3 | Rs. 4,306 crore to Rs. 3,701 crore (declined) |
| Kinara FY2025 Gross Stage 3 ratio | `icra-kinara-capital-2025.pdf` | 3 | 7.4% |
| Shree Pushkar FY2025 interest coverage | `icra-shree-pushkar-chemicals-2025.pdf` | 1 | 36.7 times |
| Talcher FY2025 gearing | `icra-talcher-fertilizers-2025.pdf` | 4 | `NOT_IN_DOCUMENT` |
| Kinara 2025 liquidity concern | `icra-kinara-capital-2025.pdf` | 1 | Severe deterioration in liquidity profile |

The Kinara AUM draft was relabeled to the table's exact comparable measure,
`Total managed assets`. The Kinara GNPA draft was likewise relabeled to
`Gross Stage 3`, which is the metric the source reports. Talcher is a negative
case: the rationale explicitly says that key financial indicators were not
included because the company was still a project company.

The Shree Pushkar values appear in the consolidated key-financial-indicators
table. The 13.1% value is not dependent on table extraction: the Desai Brothers
rationale states that operating margins moderated to 13.1% from 18.1%, while
the Kids Clinic rationale states that operating margins moderated to 13.1%
from 14.7%.

Source document hashes from `configs/corpus/phase1.audit.json`:

- Shree Pushkar: `78fb20b29ec7dafc240eb1491af6beeb5f97c419de7f8a55f7dd0f0ab631e8c2`
- Desai Brothers: `062c1c21bfcf3882cec5a9805bec4310a36062cca454681219195efeaff3271e`
- Kids Clinic: `0f6d0f8bd72d42d86dd5142ce766c1caafd9b0ef9b817e2a22cca0e1f546ede3`
- Kinara Capital: `9570509e2c055919be172d24152283a13e6598abcbd559efc9c6de3c78ce1b19`
- Talcher Fertilizers: `d7869492522a402a0ecb33e4d0791c1b33d1c3f2d80c3e05980041f9d74fd0cc`
