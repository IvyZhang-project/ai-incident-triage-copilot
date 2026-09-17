from app.models import (
    BaselineSignals,
    BaselineTriageResponse,
    EvidenceCoverage,
    EvidenceQuality,
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
    max_observed_latency_ms = (
        max(log.latency_ms for log in incident.logs)
        if incident.logs
        else 0
    )

    return IncidentSummaryResponse(
        incident_id=incident.incident_id,
        log_count=len(incident.logs),
        metric_count=len(incident.metrics),
        deployment_count=len(incident.deployments),
        has_runbook=bool(incident.runbook.strip()),
        error_log_count=len(error_logs),
        affected_services=get_affected_services(incident.logs),
        max_observed_latency_ms=max_observed_latency_ms,
        error_patterns=detect_error_patterns(incident.logs),
    )


QUALITY_RANK = {
    "weak": 1,
    "medium": 2,
    "strong": 3,
}


def build_evidence_coverage(
    incident: IncidentBundleResponse,
) -> EvidenceCoverage:
    return EvidenceCoverage(
        has_logs=bool(incident.logs),
        has_metrics=bool(incident.metrics),
        has_deployments=bool(incident.deployments),
        has_runbook=bool(incident.runbook.strip()),
    )


def identify_data_gaps(
    coverage: EvidenceCoverage,
) -> list[str]:
    data_gaps = []

    if not coverage.has_logs:
        data_gaps.append("logs")

    if not coverage.has_metrics:
        data_gaps.append("metrics")

    if not coverage.has_runbook:
        data_gaps.append("runbook")

    return data_gaps


def determine_signal_strength(signals: BaselineSignals) -> str:
    anomaly_count = sum(
        [
            signals.latency_spike_detected,
            signals.error_rate_spike_detected,
            bool(signals.error_patterns),
        ]
    )

    if anomaly_count >= 2:
        return "strong"

    if anomaly_count == 1:
        return "medium"

    return "weak"


def determine_specificity(signals: BaselineSignals) -> str:
    if signals.error_patterns:
        return "strong"

    return "weak"


def determine_time_alignment(signals: BaselineSignals) -> str:
    aligned_signal_count = sum(
        [
            signals.latency_spike_detected,
            signals.error_rate_spike_detected,
            signals.deployment_correlation_detected,
        ]
    )

    if aligned_signal_count >= 2:
        return "strong"

    if aligned_signal_count == 1:
        return "medium"

    return "weak"


def determine_consistency(signals: BaselineSignals) -> str:
    has_database_pattern = any(
        pattern in signals.error_patterns
        for pattern in [
            "database_connection_timeout",
            "connection_pool_exhaustion",
        ]
    )
    has_downstream_pattern = "downstream_timeout" in signals.error_patterns

    if has_database_pattern and has_downstream_pattern:
        return "weak"

    if (
        signals.latency_spike_detected
        and signals.error_rate_spike_detected
        and signals.error_patterns
    ):
        return "strong"

    if signals.error_patterns and (
        signals.latency_spike_detected or signals.error_rate_spike_detected
    ):
        return "medium"

    if signals.latency_spike_detected and signals.error_rate_spike_detected:
        return "medium"

    return "weak"


def determine_evidence_quality_level(
    coverage: EvidenceCoverage,
    signal_strength: str,
    consistency: str,
    specificity: str,
    time_alignment: str,
    data_gaps: list[str],
) -> str:
    score = 0

    if coverage.has_logs:
        score += 1
    if coverage.has_metrics:
        score += 1
    if coverage.has_runbook:
        score += 1

    score += QUALITY_RANK[signal_strength]
    score += QUALITY_RANK[consistency]
    score += QUALITY_RANK[specificity]
    score += QUALITY_RANK[time_alignment]
    score -= len(data_gaps)

    if score >= 10:
        if consistency == "weak":
            return "medium"

        if data_gaps and specificity == "weak":
            return "medium"

        return "strong"

    if score >= 6:
        return "medium"

    return "weak"


def build_evidence_quality(
    incident: IncidentBundleResponse,
    signals: BaselineSignals,
) -> EvidenceQuality:
    coverage = build_evidence_coverage(incident)
    data_gaps = identify_data_gaps(coverage)
    signal_strength = determine_signal_strength(signals)
    consistency = determine_consistency(signals)
    specificity = determine_specificity(signals)
    time_alignment = determine_time_alignment(signals)

    return EvidenceQuality(
        level=determine_evidence_quality_level(
            coverage=coverage,
            signal_strength=signal_strength,
            consistency=consistency,
            specificity=specificity,
            time_alignment=time_alignment,
            data_gaps=data_gaps,
        ),
        coverage=coverage,
        signal_strength=signal_strength,
        consistency=consistency,
        specificity=specificity,
        time_alignment=time_alignment,
        data_gaps=data_gaps,
    )


def determine_investigation_risk(evidence_quality: EvidenceQuality) -> str:
    if evidence_quality.level == "strong":
        return "low"

    if evidence_quality.level == "medium":
        return "medium"

    return "high"


def build_rule_based_summary(signals: BaselineSignals) -> str:
    observations = []

    if signals.latency_spike_detected:
        observations.append("latency anomaly detected")

    if signals.error_rate_spike_detected:
        observations.append("error-rate anomaly detected")

    if signals.error_patterns:
        observations.append(
            "specific error patterns detected: "
            + ", ".join(signals.error_patterns)
        )

    if signals.deployment_correlation_detected:
        observations.append("deployment or config event aligned with anomaly window")

    if not observations:
        return (
            "No strong deterministic signals were detected. The evidence package "
            "may still be useful, but the investigation should remain broad."
        )

    return (
        "Deterministic evidence assessment found "
        + "; ".join(observations)
        + ". This summarizes evidence quality and investigation risk, not a "
        "final root-cause claim."
    )


def build_baseline_triage(
    incident: IncidentBundleResponse,
) -> BaselineTriageResponse:
    signals = build_baseline_signals(incident)
    evidence_quality = build_evidence_quality(incident, signals)

    return BaselineTriageResponse(
        incident_id=incident.incident_id,
        affected_services=get_affected_services(incident.logs),
        signals=signals,
        evidence_quality=evidence_quality,
        investigation_risk=determine_investigation_risk(evidence_quality),
        rule_based_summary=build_rule_based_summary(signals),
    )
