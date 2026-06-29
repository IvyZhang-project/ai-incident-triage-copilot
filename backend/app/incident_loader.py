import csv
import json
from pathlib import Path
from typing import Any

from app.models import IncidentBundleResponse


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

