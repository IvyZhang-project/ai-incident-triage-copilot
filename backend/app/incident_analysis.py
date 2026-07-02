from app.models import (
    BaselineSignals,
    BaselineTriageResponse,
    IncidentBundleResponse,
    IncidentSummaryResponse,
)
from app.signal_detection import (
    build_baseline_signals,
    detect_error_patterns,
    get_affected_services,
)


def build_incident_summary(
    incident: IncidentBundleResponse,
) -> IncidentSummaryResponse:
    error_logs = [log for log in incident.logs if log.level == "ERROR"]

    return IncidentSummaryResponse(
        incident_id=incident.incident_id,
        log_count=len(incident.logs),
        metric_count=len(incident.metrics),
        deployment_count=len(incident.deployments),
        has_runbook=bool(incident.runbook.strip()),
        error_log_count=len(error_logs),
        affected_services=get_affected_services(incident.logs),
        max_observed_latency_ms=max(log.latency_ms for log in incident.logs),
        error_patterns=detect_error_patterns(incident.logs),
    )


def identify_missing_evidence(signals: BaselineSignals) -> list[str]:
    missing_evidence = []
    has_database_pattern = (
        "database_connection_timeout" in signals.error_patterns
        or "connection_pool_exhaustion" in signals.error_patterns
    )
    has_downstream_timeout = "downstream_timeout" in signals.error_patterns

    if not signals.latency_spike_detected:
        missing_evidence.append("latency_spike")

    if not signals.error_rate_spike_detected:
        missing_evidence.append("error_rate_spike")

    if not signals.error_patterns:
        missing_evidence.append("error_patterns")

    if has_database_pattern and not signals.deployment_correlation_detected:
        missing_evidence.append("deployment_correlation")

    if has_downstream_timeout:
        missing_evidence.append("external_provider_status")

    return missing_evidence


def determine_evidence_strength(missing_evidence: list[str]) -> str:
    if not missing_evidence:
        return "high"

    if len(missing_evidence) <= 2:
        return "medium"

    return "low"


def build_rule_based_hypothesis(signals: BaselineSignals) -> str:
    has_database_pattern = (
        "database_connection_timeout" in signals.error_patterns
        or "connection_pool_exhaustion" in signals.error_patterns
    )
    has_downstream_timeout = "downstream_timeout" in signals.error_patterns

    if (
        signals.latency_spike_detected
        and signals.error_rate_spike_detected
        and has_database_pattern
        and signals.deployment_correlation_detected
    ):
        return (
            "Deployment-related database connection issue is a candidate cause "
            "based on metric spikes, deployment timing, and database connection "
            "error patterns."
        )

    if (
        signals.latency_spike_detected
        and signals.error_rate_spike_detected
        and has_downstream_timeout
        and not signals.deployment_correlation_detected
    ):
        return (
            "External provider degradation is a candidate cause based on metric "
            "spikes, downstream timeout errors, and lack of correlated "
            "deployment evidence."
        )

    return (
        "The available evidence is insufficient for a strong rule-based root "
        "cause hypothesis. Additional logs, metrics, or deployment context may "
        "be needed."
    )


def build_baseline_triage(
    incident: IncidentBundleResponse,
) -> BaselineTriageResponse:
    signals = build_baseline_signals(incident)
    missing_evidence = identify_missing_evidence(signals)

    return BaselineTriageResponse(
        incident_id=incident.incident_id,
        affected_services=get_affected_services(incident.logs),
        signals=signals,
        rule_based_hypothesis=build_rule_based_hypothesis(signals),
        evidence_strength=determine_evidence_strength(missing_evidence),
        missing_evidence=missing_evidence,
    )
