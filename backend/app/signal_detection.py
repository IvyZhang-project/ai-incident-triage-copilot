from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from app.models import (
    BaselineSignals,
    IncidentBundleResponse,
    LogEntry,
    MetricPoint,
)


ERROR_PATTERN_RULES = {
    "database_connection_timeout": ["database connection timeout"],
    "connection_pool_exhaustion": [
        "no available connections",
        "pool had no available connections",
    ],
    "downstream_timeout": [
        "downstream timeout",
        "provider timeout",
    ],
}


LATENCY_SPIKE_RATIO_THRESHOLD = 3.0
ERROR_RATE_SPIKE_RATIO_THRESHOLD = 5.0
DEPLOYMENT_CORRELATION_WINDOW_MINUTES = 15


def get_affected_services(logs: list[LogEntry]) -> list[str]:
    return sorted({log.service for log in logs})


def detect_error_patterns(logs: list[LogEntry]) -> list[str]:
    messages = " ".join(log.message.lower() for log in logs)
    patterns = []

    for pattern_name, keywords in ERROR_PATTERN_RULES.items():
        if any(keyword in messages for keyword in keywords):
            patterns.append(pattern_name)

    return patterns


def get_metric_points(
    metrics: list[MetricPoint],
    metric_name: str,
) -> list[MetricPoint]:
    return sorted(
        [metric for metric in metrics if metric.metric == metric_name],
        key=lambda metric: metric.timestamp,
    )


def calculate_increase_ratio_from_baseline(
    baseline_values: list[float],
    observed_values: list[float],
) -> float:
    if not baseline_values or not observed_values:
        return 0.0

    baseline = median(baseline_values)
    peak = max(observed_values)

    if baseline == 0:
        return 0.0

    return round(peak / baseline, 2)


def split_metric_values_at_first_spike(
    metrics: list[MetricPoint],
    metric_name: str,
    ratio_threshold: float,
) -> tuple[list[float], list[float], str | None]:
    metric_points = get_metric_points(metrics, metric_name)

    for index in range(1, len(metric_points)):
        baseline_values = [
            float(metric.value)
            for metric in metric_points[:index]
        ]
        current_value = float(metric_points[index].value)
        baseline = median(baseline_values)

        if baseline > 0 and current_value / baseline >= ratio_threshold:
            observed_values = [
                float(metric.value)
                for metric in metric_points[index:]
            ]
            return baseline_values, observed_values, metric_points[index].timestamp

    all_values = [float(metric.value) for metric in metric_points]
    return all_values, [], None


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def has_deployment_correlation(
    incident: IncidentBundleResponse,
    first_spike_timestamp: str | None,
    window_minutes: int = DEPLOYMENT_CORRELATION_WINDOW_MINUTES,
) -> bool:
    if first_spike_timestamp is None:
        return False

    first_spike_time = parse_timestamp(first_spike_timestamp)
    window_start = first_spike_time - timedelta(minutes=window_minutes)

    return any(
        window_start <= parse_timestamp(deployment.timestamp) <= first_spike_time
        for deployment in incident.deployments
    )


def build_baseline_signals(
    incident: IncidentBundleResponse,
) -> BaselineSignals:
    (
        latency_baseline_values,
        latency_observed_values,
        latency_first_spike_timestamp,
    ) = split_metric_values_at_first_spike(
        incident.metrics,
        "p95_latency_ms",
        LATENCY_SPIKE_RATIO_THRESHOLD,
    )
    (
        error_rate_baseline_values,
        error_rate_observed_values,
        _,
    ) = split_metric_values_at_first_spike(
        incident.metrics,
        "error_rate",
        ERROR_RATE_SPIKE_RATIO_THRESHOLD,
    )

    latency_increase_ratio = calculate_increase_ratio_from_baseline(
        latency_baseline_values,
        latency_observed_values,
    )
    error_rate_increase_ratio = calculate_increase_ratio_from_baseline(
        error_rate_baseline_values,
        error_rate_observed_values,
    )
    deployment_event_count = len(incident.deployments)

    return BaselineSignals(
        latency_increase_ratio=latency_increase_ratio,
        latency_spike_detected=(
            latency_increase_ratio >= LATENCY_SPIKE_RATIO_THRESHOLD
        ),
        error_rate_increase_ratio=error_rate_increase_ratio,
        error_rate_spike_detected=(
            error_rate_increase_ratio >= ERROR_RATE_SPIKE_RATIO_THRESHOLD
        ),
        error_patterns=detect_error_patterns(incident.logs),
        deployment_event_count=deployment_event_count,
        deployment_correlation_detected=has_deployment_correlation(
            incident,
            latency_first_spike_timestamp,
        ),
    )
