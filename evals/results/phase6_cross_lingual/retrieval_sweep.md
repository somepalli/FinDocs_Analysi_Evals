# FinDocIQ retrieval sweep

Dataset SHA-256: `64d501bca57b672f086328fcb3bb4012478195bb264c9fd032160300694f48b8`

## Retrieval quality

| Strategy | Backend | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | live | 10 | 0.500 | 0.900 | 1.000 | 0.643 | 0.728 |
| hybrid | live | 10 | 0.500 | 0.600 | 0.800 | 0.560 | 0.615 |
| hybrid_rerank | live | 10 | 0.800 | 1.000 | 1.000 | 0.883 | 0.913 |

## Reasoning comparison

| Mode | Backend | Model | Retrieval | Answers | Exact | Numeric exact | Citation F1 |
|---|---|---|---|---:|---:|---:|---:|
| single_pass | live | gemma3:4b | hybrid_rerank | 10 | 1.000 | 1.000 | 0.800 |
| two_pass | live | gemma3:4b | hybrid_rerank | 10 | 0.200 | 0.200 | 0.100 |

## Retrieval quality by query language

| Strategy | Language | Queries | Recall@1 | Recall@5 | Recall@8 | MRR | nDCG@8 |
|---|---|---:|---:|---:|---:|---:|---:|
| naive | en | 5 | 0.600 | 0.800 | 1.000 | 0.695 | 0.767 |
| naive | hi | 5 | 0.400 | 1.000 | 1.000 | 0.590 | 0.690 |
| hybrid | en | 5 | 0.600 | 0.800 | 1.000 | 0.692 | 0.763 |
| hybrid | hi | 5 | 0.400 | 0.400 | 0.600 | 0.429 | 0.467 |
| hybrid_rerank | en | 5 | 0.800 | 1.000 | 1.000 | 0.867 | 0.900 |
| hybrid_rerank | hi | 5 | 0.800 | 1.000 | 1.000 | 0.900 | 0.926 |

### Hindi minus English retrieval gap

| Strategy | Recall@1 gap | Recall@5 gap | MRR gap | nDCG@8 gap |
|---|---:|---:|---:|---:|
| naive | -0.200 | +0.200 | -0.105 | -0.077 |
| hybrid | -0.200 | -0.400 | -0.263 | -0.296 |
| hybrid_rerank | +0.000 | +0.000 | +0.033 | +0.026 |

## Reasoning quality by query language

| Mode | Language | Answers | Exact | Numeric exact | Citation F1 |
|---|---|---:|---:|---:|---:|
| single_pass | en | 5 | 1.000 | 1.000 | 0.800 |
| single_pass | hi | 5 | 1.000 | 1.000 | 0.800 |
| two_pass | en | 5 | 0.400 | 0.400 | 0.200 |
| two_pass | hi | 5 | 0.000 | 0.000 | 0.000 |

### Hindi minus English reasoning gap

| Mode | Numeric exact gap | Citation F1 gap |
|---|---:|---:|
| single_pass | +0.000 | +0.000 |
| two_pass | -0.400 | -0.200 |
