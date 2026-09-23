# Evaluation Report

## Run Configuration

- Mode: Retrieval only
- Top-K: 10
- Cases: 6

## Aggregate Metrics

| Metric | Result |
| --- | ---: |
| Retrieval accuracy | 100.0% |
| Citation correctness | Not run |
| Answer match rate | Not run |
| Fallback rate | Not run |

## Case Results

| Incident | Retrieval | Citations valid | Fallback | Status |
| --- | ---: | --- | --- | --- |
| `checkout_latency_spike` | 100.0% | Not run | Not run | Pass |
| `payment_provider_timeout` | 100.0% | Not run | Not run | Pass |
| `missing_runbook_generic_latency` | 100.0% | Not run | Not run | Pass |
| `conflicting_evidence_case` | 100.0% | Not run | Not run | Pass |
| `missing_metrics_case` | 100.0% | Not run | Not run | Pass |
| `no_clear_root_cause` | 100.0% | Not run | Not run | Pass |

## Failure Details

No evaluation failures were detected in this run.

## Interpretation

Retrieval-only mode evaluates whether the ranking layer returns the expected evidence without calling an LLM. Full-analysis mode also evaluates citation validity, expected answer concepts, forbidden claims, and fallback behavior.

This golden set uses synthetic incidents with known expectations. It measures regression behavior for these cases; it does not prove correctness for every unknown production incident.

Full-analysis metrics describe one model run per case. Because LLM output is nondeterministic, repeated-run pass rates are a future stability improvement.
