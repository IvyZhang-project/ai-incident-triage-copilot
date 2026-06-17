import csv
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class LogEntry(BaseModel):
    timestamp: str
    service: str
    region: str
    level: str
    request_id: str
    message: str
    latency_ms: int
    deployment_id: str


class MetricPoint(BaseModel):
    timestamp: str
    service: str
    region: str
    metric: str
    value: str


class DeploymentEvent(BaseModel):
    timestamp: str
    service: str
    region: str
    deployment_id: str
    version: str
    change_summary: str
    changed_files: list[str]


class IncidentBundleResponse(BaseModel):
    incident_id: str
    logs: list[LogEntry]
    metrics: list[MetricPoint]
    deployments: list[DeploymentEvent]
    runbook: str


class IncidentSummaryResponse(BaseModel):
    incident_id: str
    log_count: int
    metric_count: int
    deployment_count: int
    has_runbook: bool
    error_log_count: int
    affected_services: list[str]
    max_observed_latency_ms: int
    error_patterns: list[str]


ERROR_PATTERN_RULES = {
    "database_connection_timeout": ["database connection timeout"],
    "connection_pool_exhaustion": [
        "no available connections",
        "pool had no available connections"
    ],
    "downstream_timeout": [
        "downstream timeout",
        "provider timeout"
    ],
}


app = FastAPI(
    title="AI Incident Triage Copilot API",
    description="Backend API for evidence-backed AI incident triage.",
    version="0.1.0",
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INCIDENTS_DIR = PROJECT_ROOT / "data" / "sample_incidents"


def load_json(path: Path) -> Any:
    with path.open() as file:
        return json.load(file)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as file:
        return [json.loads(line) for line in file if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as file:
        return list(csv.DictReader(file))


def load_text(path: Path) -> str:
    with path.open() as file:
        return file.read()


def load_incident_bundle(incident_id: str) -> IncidentBundleResponse:
    incident_dir = SAMPLE_INCIDENTS_DIR / incident_id

    return IncidentBundleResponse(
        incident_id=incident_id,
        logs=load_jsonl(incident_dir / "logs.jsonl"),
        metrics=load_csv(incident_dir / "metrics.csv"),
        deployments=load_json(incident_dir / "deployments.json"),
        runbook=load_text(incident_dir / "runbook.md"),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="ai-incident-triage-copilot",
        version="0.1.0",
    )


@app.get(
    "/incidents/checkout_latency_spike",
    response_model=IncidentBundleResponse,
)
def get_checkout_latency_spike() -> IncidentBundleResponse:
    return load_incident_bundle("checkout_latency_spike")


def detect_error_patterns(logs: list[LogEntry]) -> list[str]:
    messages = " ".join(log.message.lower() for log in logs)
    patterns = []

    for pattern_name, keywords in ERROR_PATTERN_RULES.items():
        if any(keyword in messages for keyword in keywords):
            patterns.append(pattern_name)

    return patterns


@app.get(
    "/incidents/checkout_latency_spike/summary",
    response_model=IncidentSummaryResponse,
)
def get_checkout_latency_spike_summary() -> IncidentSummaryResponse:
    incident = load_incident_bundle("checkout_latency_spike")
    error_logs = [log for log in incident.logs if log.level == "ERROR"]

    return IncidentSummaryResponse(
        incident_id=incident.incident_id,
        log_count=len(incident.logs),
        metric_count=len(incident.metrics),
        deployment_count=len(incident.deployments),
        has_runbook=bool(incident.runbook.strip()),
        error_log_count=len(error_logs),
        affected_services=sorted({log.service for log in incident.logs}),
        max_observed_latency_ms=max(log.latency_ms for log in incident.logs),
        error_patterns=detect_error_patterns(incident.logs),
    )
