# AI Incident Triage Copilot

AI Incident Triage Copilot is a portfolio project that demonstrates how to build an AI-assisted operational debugging system for cloud-native backend services.

The system ingests CloudWatch-style logs, metrics, deployment events, runbooks, and historical incident reports. It retrieves relevant operational evidence and generates citation-backed incident summaries, root-cause hypotheses, mitigation steps, confidence levels, and debugging traces.

## Why This Project Exists

This project focuses on the engineering layers that make an AI system more production-like:

- Clear data boundaries
- Metadata-aware retrieval
- Hybrid search
- Citation-backed answers
- Confidence scoring
- Fallback behavior
- Trace logging
- Evaluation cases

## Data Policy

This project uses synthetic CloudWatch-style logs and simulated operational data.

No proprietary, confidential, or real production logs are used.

Synthetic data allows the project to demonstrate incident triage workflows while respecting data privacy and company confidentiality.

## MVP Goal

Given:

- A service name
- An incident time window
- Logs
- Metrics
- Deployment events
- Runbook content

The system should produce:

- Incident summary
- Timeline
- Suspected root cause
- Supporting evidence
- Confidence level
- Suggested mitigation steps
- Follow-up questions when evidence is insufficient

## Project Structure

```text
ai-incident-triage-copilot/
  backend/              FastAPI backend
  frontend/             Future Next.js frontend
  data/                 Synthetic incident datasets
  docs/                 Design docs and learning notes
  infra/                Future deployment files
```


This is an AI incident triage system where critical answers are grounded in operational evidence. I designed metadata-aware retrieval, citation-backed generation, fallback behavior for low-confidence cases, trace logging for debugging, and an evaluation set to distinguish retrieval failures from generation failures.

