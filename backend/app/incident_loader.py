import csv
import json
from abc import ABC, abstractmethod
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


class IncidentLoader(ABC):
    @abstractmethod
    def load(self) -> IncidentBundleResponse:
        pass


class LocalIncidentLoader(IncidentLoader):
    def __init__(
        self,
        incident_id: str,
        base_dir: Path = SAMPLE_INCIDENTS_DIR,
    ) -> None:
        self.incident_id = incident_id
        self.base_dir = base_dir

    def load(self) -> IncidentBundleResponse:
        incident_dir = self.base_dir / self.incident_id

        return IncidentBundleResponse(
            incident_id=self.incident_id,
            logs=load_jsonl(incident_dir / "logs.jsonl"),
            metrics=load_csv(incident_dir / "metrics.csv"),
            deployments=load_json(incident_dir / "deployments.json"),
            runbook=load_text(incident_dir / "runbook.md"),
        )


class CloudWatchLikeIncidentLoader(IncidentLoader):
    def __init__(
        self,
        query: IncidentQueryRequest,
        base_dir: Path = MIXED_SOURCES_DIR,
    ) -> None:
        self.query = query
        self.base_dir = base_dir

    def load(self) -> IncidentBundleResponse:
        logs = [
            log
            for log in load_jsonl(self.base_dir / "application_logs.jsonl")
            if self._is_in_query_window(log)
        ]
        metrics = [
            metric
            for metric in load_csv(self.base_dir / "metrics.csv")
            if self._is_in_query_window(metric)
        ]
        deployments = [
            deployment
            for deployment in load_json(self.base_dir / "deployments.json")
            if self._is_in_query_window(deployment)
        ]

        return IncidentBundleResponse(
            incident_id=self._build_query_incident_id(),
            logs=logs,
            metrics=metrics,
            deployments=deployments,
            runbook=self._load_runbook(),
        )

    def _is_in_query_window(self, record: dict[str, Any]) -> bool:
        return (
            record["service"] == self.query.service
            and record["region"] == self.query.region
            and self.query.start_time <= record["timestamp"] <= self.query.end_time
        )

    def _build_query_incident_id(self) -> str:
        start = (
            self.query.start_time
            .replace("-", "")
            .replace(":", "")
            .replace("Z", "")
        )
        return f"query-{self.query.service}-{self.query.region}-{start}"

    def _load_runbook(self) -> str:
        runbook_path = self.base_dir / "runbooks" / f"{self.query.service}.md"

        if not runbook_path.exists():
            return ""

        return load_text(runbook_path)


class FutureCloudWatchLogsInsightsLoader(IncidentLoader):
    def __init__(self, query: IncidentQueryRequest) -> None:
        self.query = query

    def load(self) -> IncidentBundleResponse:
        raise NotImplementedError(
            "Real CloudWatch Logs Insights integration is post-MVP stretch work."
        )


def load_incident_bundle(incident_id: str) -> IncidentBundleResponse:
    return LocalIncidentLoader(incident_id).load()


def load_incident_bundle_from_query(
    query: IncidentQueryRequest,
) -> IncidentBundleResponse:
    return CloudWatchLikeIncidentLoader(query).load()
