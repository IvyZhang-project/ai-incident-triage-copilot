# Portfolio Notes

## Resume Bullets

- Built an AI incident-triage copilot with FastAPI and an AWS-oriented loader
  architecture to filter CloudWatch-shaped logs, metrics, deployments, and
  runbooks into scoped incident evidence packages.
- Implemented deterministic evidence-quality guardrails, metadata-aware
  retrieval, citation-backed OpenAI analysis, confidence caps, and fallback
  behavior for missing, weak, or conflicting evidence.
- Added structured traces for retrieval IDs, prompt versions, latency, token and
  cost estimates, and LLM failure categories to support production debugging.
- Created a six-case synthetic golden set plus 19 offline unit and API integration
  tests to separate retrieval, citation, grounding, answer, and fallback failures.

Use two or three bullets depending on available resume space. Do not claim real
CloudWatch ingestion or production AWS deployment unless those extensions are
actually completed.

## Two-Minute Project Explanation

I built an AI incident-triage copilot for cloud-native backend incidents. The
system starts with an incident scope such as service, region, and time window.
It deterministically filters mixed operational data into an `IncidentBundle`
containing logs, metrics, deployment events, and runbook context.

The backend then performs two separate jobs. First, deterministic analysis
assesses evidence quality using coverage, signal strength, consistency,
specificity, time alignment, and data gaps. Second, retrieval converts the
evidence into citation-ready chunks and ranks the most useful logs, metric
spikes, deployments, and runbook sections.

Only the retrieved evidence is sent to OpenAI. The backend validates the JSON
schema, allowlists citation IDs, caps confidence according to evidence quality,
and returns a deterministic fallback when generation is unavailable or
unsupported. Each run produces a trace containing the prompt, retrieved chunk
IDs, latency, token and cost estimates, fallback reason, and failure category.

I evaluated retrieval separately from generation because a wrong answer may be
caused by missing evidence or by the model misusing correct evidence. The
project includes synthetic happy-path, missing-data, conflicting-evidence, and
no-clear-cause cases, persistent reports, and offline automated tests.

## Key Tradeoffs

### Why deterministic filtering before the LLM?

Service, region, time, and access boundaries must be reproducible, testable, and
cost-efficient. The LLM helps interpret scoped evidence; it does not enforce
exact data boundaries.

### Why an `IncidentBundle` abstraction?

Curated fixtures, mixed local data, and a future CloudWatch adapter can return
the same schema. Retrieval and analysis remain independent of the source.

### Why assess evidence quality instead of hardcoding root causes?

Production root causes are open-ended. General evidence properties provide a
safer confidence boundary than a brittle list of expected incidents.

### Why keep a deterministic fallback?

The service should remain useful when OpenAI is unavailable, returns malformed
output, cites unsupported evidence, or receives an incident with weak data.

### Why keep humans in the loop?

The system proposes a leading hypothesis and missing evidence. An on-call
engineer confirms causality before consequential remediation.

## Honest Limitations

- Synthetic data does not reproduce the scale and noise of real telemetry.
- The CloudWatch-shaped adapter is local; real IAM and query integration are not
  implemented.
- Retrieval is heuristic and keyword-based rather than semantic or hybrid.
- Traces are in memory and are not suitable for multiple replicas.
- Six golden cases and one LLM run per case are useful regression signals, not a
  comprehensive production benchmark.
- The system narrows investigations but does not prove root cause autonomously.

## Short Interview Closing

The main lesson was that useful AI engineering is not just the model call. Most
of the reliability comes from data boundaries, retrieval, deterministic
guardrails, observability, fallback, and evaluation around the model.
