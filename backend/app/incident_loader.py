import csv
import json
from pathlib import Path
from typing import Any

from app.models import IncidentBundleResponse, IncidentQueryRequest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INCIDENTS_DIR = PROJECT_ROOT / "data" / "sample_incidents"
MIXED_SOURCES_DIR = PROJECT_ROOT / "data" / "mixed_sources"


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


def is_in_query_window(
    record: dict[str, Any],
    query: IncidentQueryRequest,
) -> bool:
    return (
        record["service"] == query.service
        and record["region"] == query.region
        and query.start_time <= record["timestamp"] <= query.end_time
    )


def build_query_incident_id(query: IncidentQueryRequest) -> str:
    start = (
        query.start_time
        .replace("-", "")
        .replace(":", "")
        .replace("Z", "")
    )
    return f"query-{query.service}-{query.region}-{start}"


def load_mixed_runbook(service: str) -> str:
    runbook_path = MIXED_SOURCES_DIR / "runbooks" / f"{service}.md"

    if not runbook_path.exists():
        return ""

    return load_text(runbook_path)


def load_incident_bundle_from_query(
    query: IncidentQueryRequest,
) -> IncidentBundleResponse:
    logs = [
        log
        for log in load_jsonl(MIXED_SOURCES_DIR / "application_logs.jsonl")
        if is_in_query_window(log, query)
    ]
    metrics = [
        metric
        for metric in load_csv(MIXED_SOURCES_DIR / "metrics.csv")
        if is_in_query_window(metric, query)
    ]
    deployments = [
        deployment
        for deployment in load_json(MIXED_SOURCES_DIR / "deployments.json")
        if is_in_query_window(deployment, query)
    ]

    return IncidentBundleResponse(
        incident_id=build_query_incident_id(query),
        logs=logs,
        metrics=metrics,
        deployments=deployments,
        runbook=load_mixed_runbook(query.service),
    )
