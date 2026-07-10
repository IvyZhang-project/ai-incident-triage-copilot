import re
from statistics import median

from app.models import EvidenceChunk, IncidentBundleResponse, MetricPoint


DEFAULT_INVESTIGATION_TOP_K = 10
METRIC_SPIKE_RATIO_THRESHOLD = 3.0
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "did",
    "do",
    "does",
    "for",
    "is",
    "it",
    "me",
    "of",
    "show",
    "the",
    "there",
    "this",
    "to",
    "was",
    "what",
}


def build_log_chunks(incident: IncidentBundleResponse) -> list[EvidenceChunk]:
    chunks = []

    for index, log in enumerate(incident.logs, start=1):
        chunks.append(
            EvidenceChunk(
                citation_id=f"log-{index:03}",
                incident_id=incident.incident_id,
                source_type="log",
                text=(
                    f"{log.timestamp} {log.level} {log.service} "
                    f"{log.region}: {log.message}"
                ),
                service=log.service,
                region=log.region,
                timestamp=log.timestamp,
                severity=log.level,
            )
        )

    return chunks


def build_metric_chunks(incident: IncidentBundleResponse) -> list[EvidenceChunk]:
    chunks = []

    for index, metric in enumerate(incident.metrics, start=1):
        chunks.append(
            EvidenceChunk(
                citation_id=f"metric-{index:03}",
                incident_id=incident.incident_id,
                source_type="metric",
                text=(
                    f"{metric.timestamp} {metric.service} {metric.region}: "
                    f"{metric.metric}={metric.value}"
                ),
                service=metric.service,
                region=metric.region,
                timestamp=metric.timestamp,
            )
        )

    return chunks


def build_deployment_chunks(
    incident: IncidentBundleResponse,
) -> list[EvidenceChunk]:
    chunks = []

    for index, deployment in enumerate(incident.deployments, start=1):
        changed_files = ", ".join(deployment.changed_files)

        chunks.append(
            EvidenceChunk(
                citation_id=f"deployment-{index:03}",
                incident_id=incident.incident_id,
                source_type="deployment",
                text=(
                    f"{deployment.timestamp} {deployment.service} "
                    f"{deployment.region}: {deployment.change_summary}. "
                    f"Changed files: {changed_files}"
                ),
                service=deployment.service,
                region=deployment.region,
                timestamp=deployment.timestamp,
            )
        )

    return chunks


def build_runbook_chunks(incident: IncidentBundleResponse) -> list[EvidenceChunk]:
    chunks = []

    sections = [
        section.strip()
        for section in incident.runbook.split("\n## ")
        if section.strip()
    ]

    for index, section in enumerate(sections, start=1):
        chunks.append(
            EvidenceChunk(
                citation_id=f"runbook-{index:03}",
                incident_id=incident.incident_id,
                source_type="runbook",
                text=section,
            )
        )

    return chunks


def build_evidence_chunks(
    incident: IncidentBundleResponse,
) -> list[EvidenceChunk]:
    chunks = []

    chunks.extend(build_log_chunks(incident))
    chunks.extend(build_metric_chunks(incident))
    chunks.extend(build_deployment_chunks(incident))
    chunks.extend(build_runbook_chunks(incident))

    return chunks


def get_metric_spike_scores(
    metrics: list[MetricPoint],
    ratio_threshold: float = METRIC_SPIKE_RATIO_THRESHOLD,
) -> dict[str, float]:
    scores = {}
    metric_groups: dict[str, list[tuple[int, MetricPoint]]] = {}

    for index, metric in enumerate(metrics, start=1):
        metric_groups.setdefault(metric.metric, []).append((index, metric))

    for metric_points in metric_groups.values():
        sorted_points = sorted(
            metric_points,
            key=lambda item: item[1].timestamp,
        )

        previous_values: list[float] = []
        for original_index, metric in sorted_points:
            current_value = float(metric.value)

            if previous_values:
                baseline = median(previous_values)
                if baseline > 0:
                    ratio = current_value / baseline
                    if ratio >= ratio_threshold:
                        scores[f"metric-{original_index:03}"] = ratio

            previous_values.append(current_value)

    return scores


def score_investigation_chunk(
    chunk: EvidenceChunk,
    metric_spike_scores: dict[str, float],
) -> float:
    if chunk.source_type == "log" and chunk.severity == "ERROR":
        return 100

    if chunk.citation_id in metric_spike_scores:
        return 90 + min(metric_spike_scores[chunk.citation_id], 9)

    if chunk.source_type == "deployment":
        return 80

    if chunk.source_type == "log" and chunk.severity == "WARN":
        return 70

    if chunk.source_type == "runbook":
        return 50

    if chunk.source_type == "log" and chunk.severity == "INFO":
        return 10

    return 0


def retrieve_investigation_evidence(
    incident: IncidentBundleResponse,
    top_k: int = DEFAULT_INVESTIGATION_TOP_K,
) -> list[EvidenceChunk]:
    chunks = build_evidence_chunks(incident)
    metric_spike_scores = get_metric_spike_scores(incident.metrics)

    ranked_chunks = sorted(
        chunks,
        key=lambda chunk: (
            score_investigation_chunk(chunk, metric_spike_scores),
            chunk.timestamp or "",
            chunk.citation_id,
        ),
        reverse=True,
    )

    return ranked_chunks[:top_k]


def tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9_]+", query.lower())
    return [token for token in tokens if token not in STOP_WORDS]


def score_query_chunk(
    chunk: EvidenceChunk,
    query_terms: list[str],
) -> int:
    searchable_text = " ".join(
        value
        for value in [
            chunk.source_type,
            chunk.service,
            chunk.region,
            chunk.severity,
            chunk.text,
        ]
        if value
    ).lower()

    return sum(1 for term in query_terms if term in searchable_text)


def retrieve_chunks(
    incident: IncidentBundleResponse,
    query: str,
    top_k: int,
) -> list[EvidenceChunk]:
    chunks = build_evidence_chunks(incident)
    query_terms = tokenize_query(query)

    ranked_chunks = sorted(
        chunks,
        key=lambda chunk: (
            score_query_chunk(chunk, query_terms),
            chunk.timestamp or "",
            chunk.citation_id,
        ),
        reverse=True,
    )

    return [
        chunk
        for chunk in ranked_chunks
        if score_query_chunk(chunk, query_terms) > 0
    ][:top_k]
