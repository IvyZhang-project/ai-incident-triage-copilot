# Step-by-Step Roadmap

This roadmap explains how AI Incident Triage Copilot evolves from a local evidence-loading API into a production-inspired AI incident analysis system with AWS-aware data ingestion, deterministic signal detection, retrieval, grounded LLM analysis, traces, and evaluation.

The project intentionally starts with synthetic data and deterministic backend logic before adding retrieval and LLM generation. This keeps the system testable, debuggable, and grounded in operational evidence while preserving a path toward CloudWatch-style integrations.

## Phase 1: Backend Skeleton and Data Boundaries

Goal:

Create a small backend service and define what data the system is allowed to use.

Build:

- FastAPI backend
- `/health` endpoint
- first synthetic incident dataset
- data boundary documentation

Key design decisions:

- Use synthetic CloudWatch-style data instead of proprietary production logs.
- Keep hidden eval labels separate from model-visible evidence.
- Treat local data as test fixtures, not as a claim about production storage.

Why this matters:

AI incident triage must respect data privacy and confidentiality. The system should never require real logs from a previous employer.

## Phase 2: Incident Evidence Loading

Goal:

Load model-visible incident evidence through a structured API.

Build:

- `GET /incidents/{incident_id}`
- `GET /incidents/{incident_id}/summary`
- shared incident loader
- initial loader abstraction for local fixture data

Evidence types:

- application logs
- metrics
- deployment events
- runbooks

Summary fields:

- log count
- metric count
- deployment count
- runbook availability
- error log count
- affected services
- max observed latency
- generic error patterns

Key design decisions:

- Keep API endpoints thin.
- Put reusable loading logic in shared helpers.
- Introduce data-source boundaries early so local fixtures can later be replaced by AWS-shaped loaders.
- Keep summary fields generic enough to work across incident types.
- Avoid scenario-specific fields such as `has_database_timeout` in generic response models.

Why this matters:

The first production-minded step is not AI generation. It is proving that the backend can load the right evidence and avoid exposing hidden answer keys.

## Phase 3: Rule-Based Triage Baseline

Goal:

Build deterministic signal detection before using an LLM.

Build:

- `GET /incidents/{incident_id}/baseline-triage`
- signal detection helpers

Signals:

- latency increase
- error-rate increase
- repeated error patterns
- deployment-before-spike correlation
- likely affected service
- missing evidence
- conflicting evidence

Key design decisions:

- Use deterministic code for exact facts.
- Do not use an LLM for service, region, time-window, or threshold checks.
- Treat the baseline as a comparison point for future AI output.

Why this matters:

Operational facts such as error rate, p95 latency, and deployment timing should be calculated reliably. The LLM should explain and synthesize evidence, not replace basic signal detection.

## Phase 4: Multiple Incidents and Mixed-Log Filtering

Goal:

Move from neat incident folders toward a more production-like data shape where logs are mixed and data sources are replaceable.

Build:

- multiple synthetic incident scenarios
- mixed local application log store
- mixed local metric store
- mixed local deployment store
- `POST /incident-query`
- `LocalIncidentLoader`
- `CloudWatchLikeIncidentLoader`
- placeholder `FutureCloudWatchLogsInsightsLoader`

Example query:

```json
{
  "service": "checkout-api",
  "region": "us-west-2",
  "start_time": "2026-06-15T09:30:00Z",
  "end_time": "2026-06-15T09:45:00Z"
}
```

Expected behavior:

- filter mixed logs by service, region, and time window
- filter metrics by service, region, metric, and time window
- filter deployments by service, region, and time window
- return the same `IncidentBundle` shape used by local incident folders

Key design decisions:

- Local folders are benchmark fixtures.
- Mixed local stores simulate the production reality that logs are not pre-grouped by incident.
- Filtering by exact structured fields should be deterministic.
- Loader implementations should return the same `IncidentBundle` schema.
- A CloudWatch-shaped loader can mimic CloudWatch Logs Insights results without requiring AWS credentials.
- Real CloudWatch integration remains optional until the core triage pipeline is strong.

Why this matters:

In production, an on-call engineer usually starts from an alert, service, region, and time window. The system should gather and filter evidence into an incident bundle before retrieval or AI reasoning. The loader abstraction keeps the triage pipeline independent from whether evidence comes from local fixtures, uploaded files, CloudWatch-shaped data, or real CloudWatch Logs Insights later.

## Phase 5: Retrieval and Citations

Goal:

Retrieve relevant operational evidence before asking an LLM to analyze it.

Build:

- evidence chunking
- metadata-aware keyword retrieval
- `POST /retrieve`
- citation IDs for returned chunks

Chunk metadata:

- source type
- source ID
- incident ID
- service
- region
- timestamp
- severity

Key design decisions:

- Start with keyword retrieval before vector retrieval.
- Make every retrieved chunk traceable to its source.
- Prefer reliable citations over impressive but unsupported answers.

Why this matters:

Retrieval quality is often the bottleneck in AI systems. If the right evidence is not retrieved, the model cannot reliably produce a grounded answer.

## Phase 6: AI Analysis With Grounding

Goal:

Generate incident analysis only after evidence retrieval exists.

Build:

- `POST /triage/analyze`
- prompt construction from retrieved evidence
- citation-backed incident summary
- root-cause hypothesis
- mitigation suggestions
- confidence level

Output should include:

- summary
- timeline
- suspected root cause
- supporting citations
- confidence
- recommended next steps

Key design decisions:

- The model only sees model-visible evidence.
- The model should cite evidence for important claims.
- The model should not claim certainty when evidence is weak.

Why this matters:

The value of the LLM is synthesis and explanation, not unrestricted guessing. Grounded generation reduces hallucination risk and makes answers easier to debug.

## Phase 7: Fallback and Failure Handling

Goal:

Make the system behave safely when evidence is incomplete, conflicting, or weak.

Build:

- low-confidence behavior
- missing-data follow-up questions
- conflict detection
- fallback response format

Failure cases:

- no relevant logs found
- missing deployment data
- metrics unavailable
- conflicting evidence
- retrieved evidence does not support a root-cause claim

Key design decisions:

- A useful AI system should know when not to answer.
- Low confidence should trigger conservative output or follow-up questions.
- Failure handling is part of system quality, not an afterthought.

Why this matters:

Real incidents are messy. A production-inspired AI system must handle uncertainty instead of always producing a confident answer.

## Phase 8: Trace Logging and Debuggability

Goal:

Make the AI workflow inspectable and operationally debuggable.

Build:

- trace records for each analysis request
- retrieved chunk logging
- prompt logging
- model output logging
- latency tracking
- token and cost estimate tracking
- fallback reason tracking
- `GET /traces/{trace_id}`
- optional trace/debug admin view

Trace fields:

- user query
- incident ID
- retrieved chunk IDs
- prompt version
- prompt
- model response
- confidence
- latency
- token estimate
- estimated cost
- fallback reason

Key design decisions:

- Do not treat the LLM as a black box.
- Record enough information to debug wrong answers.
- Keep traces separate from user-facing summaries.

Why this matters:

When an AI answer is wrong, engineers need to know whether the failure came from loading, filtering, retrieval, prompting, model output, or product boundaries.

## Phase 9: Evaluation

Goal:

Measure whether the system improves over time.

Build:

- hidden eval labels
- 20-30 eval cases
- `POST /eval/run`
- simple eval report
- retrieval accuracy measurement
- citation correctness measurement
- fallback rate measurement
- root-cause hypothesis match measurement

Failure categories:

- retrieval failure
- grounding failure
- citation failure
- fallback failure
- format failure
- root-cause mismatch

Key design decisions:

- Eval labels are answer keys and should not be model-visible.
- Synthetic incidents provide controlled ground truth.
- Passing synthetic evals does not prove production readiness, but it does validate the evaluation loop.

Why this matters:

AI quality should not be judged only by whether a few demo answers sound good. A small golden set makes improvements more measurable and repeatable.

## Phase 10: AWS-Aware Deployment and Portfolio Packaging

Goal:

Package the project so another engineer or interviewer can understand it, run it, and see how it maps to a cloud-native architecture.

Build:

- polished README
- architecture diagram
- local setup guide
- API examples
- eval methodology
- deployment notes
- FastAPI container
- optional AWS App Runner, ECS Fargate, or Lambda container deployment
- CloudWatch logging notes
- resume bullets
- demo script

Key design decisions:

- Be explicit that the project uses synthetic data.
- Explain how local, CloudWatch-shaped, and future CloudWatch loaders fit behind the same incident bundle schema.
- Emphasize backend design, AWS-aware architecture, evidence grounding, traceability, eval, and deployment tradeoffs.
- Keep frontend polish optional; the strongest signal is backend + retrieval + eval + observability.

Why this matters:

The final project should not look like a generic RAG chatbot. It should show production-minded backend, AWS, and AI engineering judgment: data-source boundaries, deterministic filtering, evidence retrieval, citations, traces, eval, and a credible deployment story.
